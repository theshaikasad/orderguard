import type { Business, Offer, Value } from '../lib/agent';

export const readable = (value: string) => value.replaceAll('_', ' ').replace(/^./, c => c.toUpperCase());
export const fieldNames: Record<string, string> = { product: 'Cake', size: 'Size', quantity: 'Quantity', date: 'Date', customizations: 'Customizations', addons: 'Add-ons', fulfillment: 'Collection', inscription: 'Cake message', delivery_address: 'Delivery address' };

// Shared with the original seller dashboard: all values come from backend state.
export function OrderFacts({ values, business }: { values: Record<string, Value>; business: Business | null }) {
  return <dl>{Object.entries(values).map(([key, v]) => <div className="fact" key={key}><dt>{fieldNames[key] || readable(key)}</dt><dd>{key === 'product' ? business?.products[v.value]?.name || readable(v.value) : key === 'size' ? `${v.value} ${business?.products[values.product?.value]?.unit || ''}` : key === 'inscription' || key === 'delivery_address' ? v.value : v.value.split(',').map(readable).join(', ') || 'None'}</dd></div>)}</dl>;
}

export function OfferDetails({ offer, business }: { offer: Offer; business: Business | null }) {
  return <div><div className="quote-total">₹{offer.total.toLocaleString('en-IN')}</div><p className="small muted">Items &amp; extras ₹{offer.subtotal.toLocaleString('en-IN')} · Delivery ₹{offer.total - offer.subtotal}</p><p className="small muted">Deposit ₹{offer.deposit.toLocaleString('en-IN')} · Payment not verified</p><OrderFacts values={offer.spec} business={offer.configuration_snapshot || business}/></div>;
}
