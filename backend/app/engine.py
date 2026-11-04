"""Transactional orchestrator. Only validated interpretation enters commercial rules."""
import math
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from .agent_models import Business, State, Incoming, Turn, SourcedValue, Offer, Commitment, Event
from .provider import ModelError
from .replies import plan_reply, compose_reply, cheaper_options

CATALOGUE_PATH = Path(__file__).resolve().parents[2] / 'fixtures' / 'business.json'
REQUIRED = ('product', 'size', 'quantity', 'date', 'fulfillment')


def catalogue():
    return Business.model_validate_json(CATALOGUE_PATH.read_text()).model_dump()


def supported_selection(spec, config):
    """Reject unsupported known fields even while other details are missing."""
    values = {key: value.value for key, value in spec.items()}
    if values.get('product') and values['product'] not in config['products']:
        return False
    if values.get('product') and values.get('size') and values['size'] not in config['products'][values['product']]['sizes']:
        return False
    if values.get('fulfillment') and values['fulfillment'] not in config['fulfillment']:
        return False
    for group in ('customizations', 'addons'):
        keys = [key.strip() for key in values.get(group, '').split(',') if key.strip()]
        if len(keys) != len(set(keys)) or any(key not in config[group] for key in keys):
            return False
    return True


def price(spec, config):
    """Fixed catalogue amounts in integer rupees; extras charged per cake."""
    values = {k: v.value for k, v in spec.items()}
    product = config['products'].get(values['product'])
    if not product or values['size'] not in product['sizes']:
        raise ValueError('That product or size is outside our catalogue; the owner will need to check.')
    try:
        qty = int(values['quantity'])
    except ValueError:
        raise ValueError('Quantity must be a whole number.') from None
    if not 1 <= qty <= config['policy']['daily_capacity']:
        raise ValueError('Requested quantity exceeds the configured daily capacity.')
    base = product['sizes'][values['size']]
    refs = [f"products.{values['product']}.sizes.{values['size']}", 'policy.pricing', 'policy.deposit_percent']
    for group in ('customizations', 'addons'):
        ids = [s.strip() for s in values.get(group, '').split(',') if s.strip()]
        if len(ids) != len(set(ids)) or any(i not in config[group] for i in ids):
            raise ValueError(f'Unsupported {group}; the owner needs to check this request.')
        for ident in ids:
            base += config[group][ident]
            refs.append(f'{group}.{ident}')
    fulfillment = values['fulfillment']
    if fulfillment not in config['fulfillment']:
        raise ValueError('That fulfillment zone or method needs owner review.')
    refs.append(f'fulfillment.{fulfillment}')
    subtotal = base * qty
    total = subtotal + config['fulfillment'][fulfillment]
    return subtotal, total, math.ceil(total * config['policy']['deposit_percent'] / 100), refs



def gate_reply(text):
    # Defense in depth; composition also validates complete approved paragraphs.
    if re.search(r'allergen[- ]free|allergy[- ]safe|payment (?:is )?verified|guaranteed delivery|cross.contact safe', text, re.I):
        raise ModelError('Unsafe response rejected. No changes saved.')
    return text


def event(s, kind, mid, detail, refs=None, terms=None, requested_spec=None):
    s.events.append(Event(id=f'e{len(s.events)+1}', kind=kind, message_id=mid,
                          evidence=refs or [mid], detail=detail, terms=terms.model_copy(deep=True) if terms else None,
                          requested_spec={k: v.model_copy(deep=True) for k, v in requested_spec.items()} if requested_spec is not None else None))


def review(s, reason):
    s.review_required = True
    s.decision = 'needs_owner'
    s.alerts.append(reason)
    return None


def validate_evidence(s, config):
    mids = {t.id for t in s.turns}
    def policy_ref(ref):
        # Historical M1.1 evidence remains auditable, never active pricing authority.
        if ref in {'policy.max_discount_percent', 'policy.minimum_order_rupees'}:
            return True
        if ref.startswith('products.'):
            # Size keys may contain a decimal point.
            for pid, p in config['products'].items():
                if ref in {f'products.{pid}.sizes.{size}' for size in p['sizes']}:
                    return True
            return False
        parts = ref.split('.')
        return len(parts) == 2 and parts[0] in config and isinstance(config[parts[0]], dict) and parts[1] in config[parts[0]]
    def walk(obj):
        if isinstance(obj, dict):
            if 'evidence' in obj:
                if any(r not in mids and not policy_ref(r) for r in obj['evidence']):
                    raise ModelError('Invalid evidence; no changes saved.')
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    walk(s.model_dump())


def process(store, provider, cid, incoming: Incoming, now=None):
    with store.transaction():
        return _process(store, provider, cid, incoming, now)


def _process(store, provider, cid, incoming: Incoming, now=None):
    s = store.get(cid)
    existing = next((t for t in s.turns if t.id == incoming.message_id), None)
    if existing:
        if existing.sender != 'customer' or existing.text != incoming.text:
            raise HTTPException(409, 'Message ID already used with different content.')
        return s
    now = now or datetime.now(ZoneInfo('Asia/Kolkata'))
    if incoming.timestamp > now + timedelta(minutes=5):
        raise HTTPException(422, 'Timestamp is in the future.')
    customer_turns = [t for t in s.turns if t.sender == 'customer']
    if customer_turns and incoming.timestamp <= max(t.timestamp for t in customer_turns):
        raise HTTPException(409, 'Out-of-order message rejected; current state is unchanged. Send a new message ID with a current timestamp.')
    config = store.catalogue()
    interpretation = provider.interpret({'server_now': now.isoformat(), 'business': config,
        'state': s.model_dump(mode='json'), 'new_message': incoming.model_dump(mode='json')})
    # Validate extraction evidence before any persisted mutation.
    for p in interpretation.patches:
        if p.message_id != incoming.message_id or p.quote not in incoming.text:
            raise ModelError('Model evidence did not match the incoming message. No changes saved.')
        if p.field == 'inscription' and p.value not in p.quote:
            raise ModelError('Inscription was not preserved verbatim. No changes saved.')
    if len({p.field for p in interpretation.patches}) != len(interpretation.patches):
        raise ModelError('Model returned conflicting fields. No changes saved.')
    mid = incoming.message_id
    source = provider.source
    s.source = source
    s.turns.append(Turn(id=mid, sender='customer', timestamp=incoming.timestamp, text=incoming.text, source=source))
    s.decision, s.alerts = 'automatic', []
    event(s, 'incoming', mid, incoming.text)
    intents = interpretation.intents
    text = incoming.text.lower()
    discount_requested = 'discount_request' in intents or bool(re.search(r'discount|cheaper|\d+\s*%|\bprice.{0,15}(?:lower|reduce)|\b(?:deal|negotiate|bargain)\b', text))
    claimed = 'payment_claim' in intents or bool(re.search(r'\b(i paid|i have paid|payment sent|paid already)\b', text))
    if claimed:
        s.payment = 'claimed'
        event(s, 'payment_claimed', mid, 'Payment claimed; never verified', [mid, 'policy.deposit_percent'])
    sensitive = 'allergy' in intents or bool(re.search(r'allerg|cross.contact|nut.free|gluten.free', text))
    injection = bool(re.search(r'ignore.{0,35}(polic|instruct|rule)|system prompt|override.{0,20}(polic|rule)', text))
    patches = {p.field: SourcedValue(value=p.value, evidence=[mid]) for p in interpretation.patches}
    if injection:
        patches = {}
    changes = {k: v for k, v in patches.items() if k not in s.requested_spec or s.requested_spec[k].value != v.value}
    s.requested_spec.update(patches)
    if changes:
        event(s, 'requested_spec_changed', mid, 'Customer request interpreted by model; not a commitment', requested_spec=s.requested_spec)
    if changes and s.offered_terms:
        event(s, 'offer_invalidated', mid, s.offered_terms.id, terms=s.offered_terms)
        s.offered_terms = None
        s.awaiting_acceptance_for = None
        if not s.accepted_commitment:
            s.status = 'draft'
    s.missing_fields = [f for f in REQUIRED if not s.requested_spec.get(f) or not s.requested_spec[f].value]
    action = 'help'
    routine_ack = bool(re.fullmatch(r'\s*(?:yes|okay|ok|sure)[.!]?\s*', incoming.text, re.I))
    local_ack = (routine_ack and not changes and s.offered_terms and not s.review_required
            and not s.accepted_commitment and not sensitive and not claimed
            and interpretation.association in ('current', 'unknown'))
    # Still run all pricing, capacity and review gates before clarifying.
    if interpretation.association != 'current' and not local_ack:
        review(s, 'Please identify the order. Multiple/new independent orders need owner review.')
        action = 'association'
    elif injection:
        action = 'help'
    elif sensitive or 'dispute' in intents:
        review(s, 'Dietary suitability or a dispute needs a human check. Shared kitchen; suitability is not confirmed.')
        action = 'safety' if sensitive else 'blocked'
    elif (s.accepted_commitment or s.production_snapshot) and (changes or 'cancel' in intents):
        review(s, 'Changes or cancellation after confirmation need owner approval.')
        action = 'review_change'
    elif s.review_required:
        review(s, 'An earlier request is still awaiting owner review.')
        action = 'review_pending'
    elif 'fulfillment_check' in intents:
        review(s, 'Exact pickup or delivery times need owner confirmation.')
        action = 'fulfillment'
    elif s.status == 'cancelled':
        action = 'cancelled'
    elif 'cancel' in intents:
        s.status, s.offered_terms = 'cancelled', None
        event(s, 'cancelled', mid, 'Unaccepted draft cancelled')
        action = 'cancelled'
    elif claimed:
        action = 'payment'
        s.decision = 'needs_owner'
        s.alerts = ['Payment verification required before fulfillment.']
    elif s.accepted_commitment:
        action = 'unchanged'
    elif not supported_selection(s.requested_spec, config):
        s.offered_terms = None
        s.status = 'draft'
        review(s, 'Requested product, size, extras or delivery zone is outside the catalogue.')
        action = 'blocked'
    elif s.missing_fields:
        s.status = 'draft' if s.requested_spec else 'inquiry'
        action = 'clarify'
    else:
        try:
            requested_date = date.fromisoformat(s.requested_spec['date'].value)
            if requested_date < now.date() + timedelta(days=config['policy']['lead_days']) or requested_date.isoformat() in config['policy']['closed_dates']:
                raise ValueError('That date needs an availability check.')
            occupied = sum(int(other.accepted_commitment.terms.spec['quantity'].value)
                for other in store.all() if other.id != cid and other.accepted_commitment
                and other.accepted_commitment.terms.spec['date'].value == requested_date.isoformat())
            if occupied + int(s.requested_spec['quantity'].value) > config['policy']['daily_capacity']:
                raise ValueError('The local capacity ledger is full on that date.')
            subtotal, total, deposit, refs = price(s.requested_spec, config)
            refs += ['policy.lead_days', 'policy.daily_capacity', 'policy.availability', 'policy.hours', 'policy.dietary']
            offer = s.offered_terms
            # Recheck every commercial term and requested field, including old discounted records.
            if offer and (offer.discount_percent != 0 or offer.subtotal != subtotal
                          or offer.total != total or offer.deposit != deposit
                          or {k: v.value for k, v in offer.spec.items()} != {k: v.value for k, v in s.requested_spec.items()}):
                event(s, 'offer_invalidated', mid, offer.id, terms=offer)
                s.offered_terms = None
                s.awaiting_acceptance_for = None
            explicit = re.fullmatch(r'\s*i accept offer ([a-zA-Z0-9_-]+)[.!]?\s*', incoming.text, re.I)
            natural = re.fullmatch(r"\s*(?:i accept|i confirm|yes[, ]+go ahead|go ahead|please go ahead|yes[, ]+please go ahead|let[’']s go ahead)[.!]?\s*", incoming.text, re.I)
            offer = s.offered_terms
            exact_reference = explicit and offer and explicit.group(1).lower() == offer.id.lower()
            contextual_reference = natural and offer and s.awaiting_acceptance_for == offer.id
            valid_accept = ('accept' in intents and not discount_requested and not changes
                            and (exact_reference or contextual_reference))
            if valid_accept:
                s.accepted_commitment = Commitment(terms=offer.model_copy(deep=True), evidence=[mid, offer.message_id])
                s.status = 'accepted'
                event(s, 'accepted', mid, offer.id, [mid, offer.message_id])
                action = 'accepted'
            else:
                if s.offered_terms is None:
                    oid = f'offer-{len(s.events)+1}'
                    s.offered_terms = Offer(id=oid, spec={k: v.model_copy(deep=True) for k, v in s.requested_spec.items()},
                        subtotal=subtotal, total=total, deposit=deposit,
                        evidence=list(dict.fromkeys([r for v in s.requested_spec.values() for r in v.evidence] + refs)),
                        message_id=f'reply-{mid}')
                    event(s, 'offered', mid, oid, s.offered_terms.evidence, terms=s.offered_terms)
                s.status = 'offered'
                action = 'ambiguous' if ('accept' in intents or routine_ack) and not changes and offer else 'quote'
        except (ValueError, KeyError):
            s.offered_terms = None
            if not s.accepted_commitment:
                s.status = 'draft'
            review(s, 'Requested product, options, quantity, date or capacity needs owner review.')
            action = 'blocked'
    groups = plan_reply(s, config, action, discount_requested,
                        dietary_note='customizations' in changes and 'eggless' in changes['customizations'].value.split(','))
    # Natural acceptance binds to a specific current quote and its last unambiguous question.
    invites_acceptance = action in ('quote', 'ambiguous') and not (
        action == 'quote' and discount_requested and cheaper_options(s.offered_terms, config))
    s.awaiting_acceptance_for = s.offered_terms.id if invites_acceptance else None
    reply, reply_source = compose_reply(provider, groups, {
        'tone': config['tone'], 'permitted_action': action,
        'recent_conversation': [{'speaker': t.sender, 'text': t.text} for t in s.turns[-5:]],
    })
    if s.decision == 'needs_owner':
        event(s, 'owner_review', mid, '; '.join(s.alerts))
    s.assistant_reply = gate_reply(reply)
    s.turns.append(Turn(id=f'reply-{mid}', sender='baker', timestamp=datetime.now(ZoneInfo('Asia/Kolkata')),
                        text=s.assistant_reply, source=source, reply_source=reply_source))
    event(s, 'reply', mid, f'Customer reply: {reply_source}', [f'reply-{mid}'])
    validate_evidence(s, config)
    store.save(s)
    return s
