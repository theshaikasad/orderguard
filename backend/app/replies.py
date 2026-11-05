"""Closed-world reply composition: Muse selects natural, approved paragraphs.

Each paragraph has fact-equivalent variants. Validate every paragraph and its
position, including required caveats, rather than trying to detect arbitrary
promises with a blacklist. No free-form customer text becomes reply authority.
"""
from .provider import ModelError
from decimal import Decimal


def label(value):
    if value.startswith('delivery_'):
        return 'Delivery to ' + value.removeprefix('delivery_').replace('_', ' ').title()
    return value.replace('_', ' ').capitalize()


def quote_details(offer, config):
    values = {k: v.value for k, v in offer.spec.items()}
    qty = int(values['quantity'])
    product = config['products'][values['product']]
    unit = product.get('unit', 'kg')
    variant = f"{values['size']} {unit}" if unit in {'kg','g','stems','roses','litres','meters'} else values['size']
    suffix = '' if values['size'] in product['name'].split() else f' ({variant})'
    lines = [f"{qty} × {product['name']}{suffix}: ₹{product['sizes'][values['size']] * qty}"]
    for group in ('customizations', 'addons'):
        for key in filter(None, (part.strip() for part in values.get(group, '').split(','))):
            lines.append(f'{label(key)} × {qty}: ₹{int(Decimal(config[group][key]) * qty * (Decimal(values['size']) if config.get('extra_units', {}).get(key) == 'per_size' else 1))}')
    if values.get('delivery_address'):
        lines.append(f"Delivery address: {values['delivery_address']}")
    fee = config['fulfillment'][values['fulfillment']]
    lines.append(f"{label(values['fulfillment'])}: ₹{fee}")
    lines += [f'Total: ₹{offer.total}', f'Deposit: ₹{offer.deposit}',
              f"Requested date: {values['date']}"]
    if values.get('inscription'):
        lines.append(f"Cake message: “{values['inscription']}”")
    return '\n'.join(lines)


def cheaper_options(offer, config):
    """Suggest catalogue changes, never lower an existing quote or imply capacity."""
    v = {k: x.value for k, x in offer.spec.items()}
    options = []
    sizes = config['products'][v['product']]['sizes']
    cheaper = [(size, amount) for size, amount in sizes.items()
               if size.replace('.', '', 1).isdigit() and v['size'].replace('.', '', 1).isdigit() and float(size) < float(v['size']) and amount < sizes[v['size']]]
    if cheaper:
        size, _ = min(cheaper, key=lambda entry: float(entry[0]))
        options.append(f"a {size} {config['products'][v['product']].get('unit','kg')} size")
    # Eggless may be a dietary need, so never suggest removing it to save money.
    optional = [key for group in ('customizations', 'addons')
                for key in v.get(group, '').split(',')
                if key and key != 'eggless' and key in config[group] and config[group][key] > 0]
    if optional:
        options.append('removing ' + ', '.join(label(key).lower() for key in optional))
    return ('We could look at ' + ' or '.join(options) + ' to lower the total. Would you like that?') if options else ''


def plan_reply(s, config, action, discount_requested=False, dietary_note=False):
    groups = []
    if discount_requested:
        groups.append(['Our prices are fixed, so I can’t offer a discount.',
                       'We keep our prices fixed, so there isn’t a discount available.'])
    if action == 'quote':
        groups += [['Here’s your cake quote:', 'Here’s the breakdown for your cake:', 'Lovely, here are the details:'],
                   [quote_details(s.offered_terms, config)]]
        if dietary_note:
            groups.append(['Our eggless recipe is made in a shared kitchen; please let us know about any allergies.'])
        alternative = cheaper_options(s.offered_terms, config) if discount_requested else ''
        groups.append([alternative] if alternative else [
            'Would you like to go ahead with this cake at this price?',
            'Shall we go ahead with these details and this total?'])
    elif action == 'accepted':
        total = s.accepted_commitment.terms.total
        deposit = s.accepted_commitment.terms.deposit
        groups += [[f'Thanks! I’ve confirmed your cake details at ₹{total}.',
                    f'Lovely, your cake details are confirmed at ₹{total}.'],
                   [f'The deposit is ₹{deposit}. Payment hasn’t been verified, and production hasn’t been scheduled.']]
    elif action == 'unchanged':
        groups += [['Your confirmed cake details are unchanged.', 'We’re keeping your confirmed cake details as they are.'],
                   ['The owner can help with payment verification and the next steps.']]
    elif action == 'clarify':
        if 'product' in s.missing_fields:
            names = ' and '.join(p['name'].lower() for p in config['products'].values())
            groups.append([f'Hi! We make {names}.', f'Happy to help! We have {names}.'])
        questions = {
            'product': 'Which cake would you like?',
            'size': 'What size would you like?',
            'quantity': 'How many cakes would you like?',
            'date': 'What date is it for?',
            'delivery_address': 'What is the delivery address, including the service area?',
            'fulfillment': 'Would you prefer ' + ' or '.join(label(key).lower() for key in config['fulfillment']) + '?',
        }
        groups.append([' '.join(questions[key] for key in s.missing_fields[:2])])
    elif action == 'ambiguous':
        groups += [[quote_details(s.offered_terms, config)],
                   ['Just to check, would you like to go ahead with these cake details and total?',
                    'Shall I confirm the cake exactly as described in the latest quote?']]
    elif action == 'payment':
        groups += [['Thanks for letting us know! The owner will need to check the payment before we can arrange fulfillment.']]
    elif action == 'cancelled':
        groups += [['Your cake request is cancelled. Please start a new conversation if you’d like to order again.']]
    elif action == 'safety':
        groups += [['Thanks for telling us. I’ll ask the owner to check this dietary requirement. Our kitchen is shared, so suitability isn’t confirmed.']]
    elif action == 'review_change':
        groups += [['I’ll ask the owner to check that change. Your previously confirmed cake details will stay as they are for now.']]
    elif action == 'review_pending':
        groups += [['The owner still needs to check your earlier request. I’ll keep the confirmed details unchanged for now.']]
    elif action == 'association':
        groups += [['Could you clarify which cake order this is for? I’ll ask the owner to help keep the orders separate.']]
    elif action == 'blocked':
        names = ', '.join(p['name'] for p in config['products'].values())
        groups.append([f'Our listed options are {names}. I can help with those at their fixed prices.'])
        groups += [['I’ll need the owner to check that option or date before quoting. I haven’t confirmed the change.']]
    elif action == 'fulfillment':
        groups += [['I’ll ask the owner to check that pickup or delivery time. I can’t confirm an exact slot yet.']]
    else:
        groups += [['I can help with our cakes at their listed prices. What would you like to know?']]
    if config.get('category', '').lower() not in ('', 'bakery'):
        groups = [[text.replace('cakes', 'items').replace('Cakes', 'Items').replace('cake', 'item').replace('Cake', 'Item').replace('kitchen', 'workspace') for text in group] for group in groups]
    if 'formal' in config.get('tone', '').lower():
        groups = [[text.replace('Hi!', 'Hello.').replace('Lovely,', 'Thank you,').replace('Happy to help!', 'I can assist.').replace('Thanks', 'Thank you') for text in group] for group in groups]
    return groups


def compose_reply(provider, groups, context):
    """Reply failure never rolls back a valid interpreted turn or invents a result."""
    fallback = '\n\n'.join(group[0] for group in groups)
    try:
        paragraphs = provider.generate_reply({'approved_paragraphs': groups, **context})
        if not isinstance(paragraphs, list) or len(paragraphs) != len(groups):
            raise ModelError('Invalid reply shape')
        if any(not isinstance(text, str) or text not in variants
               for text, variants in zip(paragraphs, groups)):
            raise ModelError('Reply introduced unapproved wording or facts')
        return '\n\n'.join(paragraphs), provider.source
    except ModelError:
        return fallback, 'fallback'
