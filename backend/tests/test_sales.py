"""M1.2 sales decisions, closed-world replies and failure behavior."""
import json
import pytest
import httpx
from app.engine import catalogue
from app.provider import MetaProvider, ModelError
from app.replies import plan_reply, compose_reply
from test_agent import MockProvider, turn, quoted, accepted, store, DATE


def test_basic_inquiry_is_friendly_and_lists_only_catalogue(store):
    s = turn(store, 1, text='What cakes do you make?')
    assert 'chocolate cake' in s.assistant_reply.lower()
    assert 'red velvet cake' in s.assistant_reply.lower()
    assert 'vanilla' not in s.assistant_reply.lower()
    assert s.offered_terms is None and s.accepted_commitment is None
    assert s.turns[-1].reply_source == 'mock'


def test_itemized_quantity_extras_and_delivery(store):
    p = MockProvider({'product': 'chocolate', 'size': '1.5', 'quantity': '2', 'date': DATE,
                      'fulfillment': 'delivery_indiranagar', 'customizations': 'eggless,floral_decoration',
                      'addons': 'candles'})
    s = turn(store, 1, p)
    assert s.offered_terms.total == 3700
    for detail in ['₹2700', '₹300', '₹500', '₹100', 'Total: ₹3700', 'Deposit: ₹1850']:
        assert detail in s.assistant_reply
    assert 'offer-' not in s.assistant_reply and 'discount' not in s.assistant_reply


@pytest.mark.parametrize('text', ['yes, go ahead', 'I confirm', 'Please go ahead!', 'I accept'])
def test_natural_acceptance_exactly_current_quote(store, text):
    offer = quoted(store).offered_terms
    s = turn(store, 2, MockProvider(intents=['accept']), text)
    assert s.accepted_commitment.terms == offer
    assert s.status == 'accepted' and s.production_snapshot is None and s.payment == 'unknown'
    assert 'production hasn’t been scheduled' in s.assistant_reply
    assert 'offer-' not in s.assistant_reply


@pytest.mark.parametrize('text', ['yes', 'okay', 'I confirm if you can do tomorrow',
                                  'Yes, make it 2 kg', 'I confirm the earlier quote'])
def test_ambiguous_or_conditional_acceptance_cannot_commit(store, text):
    quoted(store)
    s = turn(store, 2, MockProvider(intents=['accept']), text)
    assert s.accepted_commitment is None and s.status == 'offered'


def test_simultaneous_revision_and_acceptance_cannot_commit(store):
    old = quoted(store).offered_terms
    s = turn(store, 2, MockProvider({'size': '2'}, ['accept', 'revise']), 'Yes, go ahead with 2 kg')
    assert s.accepted_commitment is None
    assert s.offered_terms.id != old.id and s.offered_terms.total == 1800
    assert s.offered_terms.spec['size'].value == '2'
    s = turn(store, 3, MockProvider(intents=['accept']), 'I confirm')
    assert s.accepted_commitment.terms.total == 1800


def test_discount_alternatives_do_not_create_ambiguous_commitment(store):
    quoted(store)
    turn(store, 2, MockProvider({'size': '2'}), 'Make it 2 kg')
    s = turn(store, 3, MockProvider(intents=['discount_request']), 'Any discount?')
    assert '1 kg size' in s.assistant_reply and s.awaiting_acceptance_for is None
    assert s.offered_terms.total == 1800
    s = turn(store, 4, MockProvider(intents=['accept']), 'yes, go ahead')
    assert s.accepted_commitment is None
    s = turn(store, 5, MockProvider(intents=['accept']), 'I confirm')
    assert s.accepted_commitment.terms.total == 1800


def test_discount_alternatives_never_remove_dietary_requirement(store):
    quoted(store)
    turn(store, 2, MockProvider({'customizations': 'eggless,floral_decoration'}))
    s = turn(store, 3, MockProvider(intents=['discount_request']), 'Can it be cheaper?')
    assert 'removing floral decoration' in s.assistant_reply
    assert 'removing eggless' not in s.assistant_reply and s.offered_terms.total == 1300


def test_no_repeated_answered_questions(store):
    turn(store, 1, MockProvider({'product': 'chocolate', 'quantity': '1'}))
    s = turn(store, 2, MockProvider({'size': '1'}))
    assert 'What date is it for?' in s.assistant_reply
    assert 'What size' not in s.assistant_reply and 'How many' not in s.assistant_reply
    assert 'Which cake' not in s.assistant_reply


def test_unsupported_customization_requires_owner(store):
    quoted(store)
    s = turn(store, 2, MockProvider({'customizations': 'gold_leaf'}), 'Add gold leaf')
    assert s.decision == 'needs_owner' and s.offered_terms is None
    assert s.accepted_commitment is None and 'owner' in s.assistant_reply


def test_legacy_discounted_offer_must_be_requoted(store):
    s = quoted(store)
    old_id = s.offered_terms.id
    s.offered_terms.discount_percent, s.offered_terms.total = 10, 810
    s.offered_terms.evidence += ['policy.max_discount_percent', 'policy.minimum_order_rupees']
    store.save(s)
    s = turn(store, 2, MockProvider(intents=['accept']), 'I confirm')
    assert s.accepted_commitment is None
    assert s.offered_terms.total == 900 and s.offered_terms.id != old_id
    s = turn(store, 3, MockProvider(intents=['accept']), f'I accept offer {old_id}')
    assert s.accepted_commitment is None


def test_accepted_historical_terms_remain_unchanged(store):
    s = accepted(store)
    s.accepted_commitment.terms.discount_percent = 10
    s.accepted_commitment.terms.total = 810
    store.save(s)
    s = turn(store, 3, text='Hello again')
    assert s.accepted_commitment.terms.total == 810


def test_catalogue_price_change_requires_new_quote(store, monkeypatch):
    quoted(store)
    import app.engine as engine
    config = catalogue()
    config['products']['chocolate']['sizes']['1'] = 950
    monkeypatch.setattr(store, 'catalogue', lambda: config)
    s = turn(store, 2, MockProvider(intents=['accept']), 'I confirm')
    assert s.accepted_commitment is None and s.offered_terms.total == 950


def test_reply_failure_falls_back_but_persists_valid_decision(store):
    class Fails(MockProvider):
        def generate_reply(self, context):
            raise ModelError('Unavailable')
    quoted(store)
    s = turn(store, 2, Fails(intents=['accept']), 'I confirm')
    assert s.status == 'accepted' and s.accepted_commitment.terms.total == 900
    assert s.turns[-1].reply_source == 'fallback' and store.get('demo') == s
    assert turn(store, 2, Fails(), 'I confirm') == s


@pytest.mark.parametrize('bad', [
    ['Your cake costs ₹1 and delivery is guaranteed.'],
    ['Your payment is verified and production is booked.'],
    ['Offer offer-17 confirmed.'],
    ['We also offer vanilla cakes at 900 rupees.'],
    ['Pay tomorrow and I promise a refund.'],
    ['The price is nine hundred rupees and I will deliver by noon.'],
    [], None, 'arbitrary prose',
])
def test_unapproved_reply_falls_back(store, bad):
    class Bad(MockProvider):
        def generate_reply(self, context):
            return bad
    s = turn(store, 1, Bad({'product': 'chocolate', 'size': '1', 'quantity': '1', 'date': DATE, 'fulfillment': 'pickup'}))
    assert s.turns[-1].reply_source == 'fallback'
    assert 'Total: ₹900' in s.assistant_reply
    assert 'offer-' not in s.assistant_reply and s.accepted_commitment is None


def test_correct_numbers_in_wrong_context_are_rejected(store):
    s = quoted(store)
    groups = plan_reply(s, catalogue(), 'quote')
    class Wrong(MockProvider):
        def generate_reply(self, context):
            return [g[0].replace('Total: ₹900', 'Total: ₹450').replace('Deposit: ₹450', 'Deposit: ₹900') for g in groups]
    _, source = compose_reply(Wrong(), groups, {})
    assert source == 'fallback'


def test_omitted_safety_caveat_is_rejected(store):
    s = accepted(store)
    groups = plan_reply(s, catalogue(), 'accepted')
    class Omits(MockProvider):
        def generate_reply(self, context):
            return [groups[0][0]]
    _, source = compose_reply(Omits(), groups, {})
    assert source == 'fallback'


def test_provider_reply_wire_and_sanitized_failure(monkeypatch):
    monkeypatch.setenv('MODEL_API_KEY', 'test-not-a-key')
    actual_client = httpx.Client
    captured = []
    def handle(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'paragraphs': ['Happy to help!']})}}]})
    monkeypatch.setattr(httpx, 'Client', lambda **kw: actual_client(transport=httpx.MockTransport(handle), **kw))
    p = MetaProvider()
    assert p.generate_reply({'approved_paragraphs': [['Happy to help!']]}) == ['Happy to help!']
    assert captured[0]['model'] == 'muse-spark-1.3'
    assert captured[0]['response_format']['json_schema']['name'] == 'CustomerReply'
    def fail(request):
        raise httpx.ReadTimeout('upstream sensitive details')
    monkeypatch.setattr(httpx, 'Client', lambda **kw: actual_client(transport=httpx.MockTransport(fail), **kw))
    with pytest.raises(ModelError) as exc:
        p.generate_reply({'approved_paragraphs': [['Happy to help!']]})
    assert 'sensitive' not in str(exc.value)


def test_partial_unsupported_customization_is_not_ignored(store):
    s = turn(store, 1, MockProvider({'product': 'chocolate', 'customizations': 'gold_leaf'}), 'A chocolate cake with gold leaf')
    assert s.decision == 'needs_owner' and s.offered_terms is None
    assert 'owner' in s.assistant_reply and 'What size' not in s.assistant_reply


def test_exact_slot_needs_owner_even_with_valid_quote(store):
    quoted(store)
    s = turn(store, 2, MockProvider(intents=['accept', 'fulfillment_check']), 'I confirm for pickup at noon')
    assert s.accepted_commitment is None and s.decision == 'needs_owner'
    assert 'exact slot' in s.assistant_reply


def test_uncertain_yes_clarifies_without_owner_or_commitment(store):
    quoted(store)
    s = turn(store, 2, MockProvider(association='unknown'), 'Yes')
    assert s.decision == 'automatic' and not s.review_required
    assert not s.accepted_commitment and s.offered_terms.total == 900
    assert 'Total: ₹900' in s.assistant_reply
    s = turn(store, 3, MockProvider(intents=['accept']), 'I confirm')
    assert s.accepted_commitment.terms.total == 900


@pytest.mark.parametrize('claim', ['Delivery is guaranteed.', 'Payment is verified.',
                                  'We offer vanilla cake.', 'Your total is ₹1.',
                                  'Your cake will be ready at noon.'])
def test_appending_claim_to_otherwise_valid_reply_is_rejected(store, claim):
    class AddsClaim(MockProvider):
        def generate_reply(self, context):
            paragraphs = super().generate_reply(context)
            paragraphs[0] += ' ' + claim
            return paragraphs
    s = turn(store, 1, AddsClaim({'product': 'chocolate', 'size': '1', 'quantity': '1', 'date': DATE, 'fulfillment': 'pickup'}))
    assert s.turns[-1].reply_source == 'fallback'
    assert claim not in s.assistant_reply
    assert s.offered_terms.total == 900 and not s.accepted_commitment


def test_reply_context_contains_no_order_ids_or_mutation_authority(store):
    quoted(store)
    class Inspect(MockProvider):
        def generate_reply(self, context):
            assert set(context) == {'approved_paragraphs', 'tone', 'permitted_action', 'recent_conversation'}
            assert 'requested_spec' not in context and 'accepted_commitment' not in context
            assert 'offer-' not in json.dumps(context)
            return super().generate_reply(context)
    s = turn(store, 2, Inspect(), 'Can you repeat the quote?')
    assert s.offered_terms.total == 900 and not s.accepted_commitment


def test_fulfillment_question_uses_only_configured_options(store, monkeypatch):
    import app.engine as engine
    config = catalogue()
    config['fulfillment'] = {'pickup': 0}
    monkeypatch.setattr(store, 'catalogue', lambda: config)
    s = turn(store, 1, MockProvider({'product': 'chocolate', 'size': '1', 'quantity': '1', 'date': DATE}))
    assert 'pickup' in s.assistant_reply and 'delivery' not in s.assistant_reply.lower()


def test_agreement_to_remove_optional_extra_requotes_before_acceptance(store):
    quoted(store)
    turn(store, 2, MockProvider({'customizations': 'eggless,floral_decoration'}))
    turn(store, 3, MockProvider(intents=['discount_request']), 'Any discount?')
    s = turn(store, 4, MockProvider({'customizations': 'eggless'}, ['revise', 'accept']), 'Yes, go ahead')
    assert s.offered_terms.total == 1050 and s.accepted_commitment is None
    assert s.offered_terms.spec['customizations'].value == 'eggless'
    s = turn(store, 5, MockProvider(intents=['accept']), 'I confirm')
    assert s.accepted_commitment.terms.total == 1050


def test_opt_in_low_reasoning_is_explicit_and_validated(monkeypatch):
    monkeypatch.setenv('MODEL_API_KEY','test-not-a-key')
    monkeypatch.setenv('MUSE_REPLY_REASONING_EFFORT','low')
    actual_client=httpx.Client
    captured=[]
    def handle(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"paragraphs":["Hello"]}'}}]})
    monkeypatch.setattr(httpx,'Client',lambda **kw:actual_client(transport=httpx.MockTransport(handle),**kw))
    provider=MetaProvider()
    assert provider.generate_reply({'approved_paragraphs':[['Hello']]})==['Hello']
    assert captured[0]['reasoning_effort']=='low' and provider.metrics[0]['reasoning_effort']=='low'
    monkeypatch.setenv('MUSE_REPLY_REASONING_EFFORT','none')
    with pytest.raises(ModelError):provider.generate_reply({'approved_paragraphs':[['Hello']]})
