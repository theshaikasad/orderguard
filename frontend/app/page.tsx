'use client';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import type { AgentState, Business, Commitment, Offer, Value } from '../lib/agent';
const API = process.env.NEXT_PUBLIC_API_BASE_URL || '';
async function request<T>(path: string, body?: unknown): Promise<T> {
  let r: Response;
  try { r = await fetch(`${API}${path}`, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); }
  catch { throw new Error('Backend unavailable. Start FastAPI on port 8000, then retry or reload.'); }
  const data = await r.json();
  if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Invalid request. Check the message and try again.');
  return data;
}
export default function Workspace() {
  const transcript = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<AgentState | null>(null);
  const [business, setBusiness] = useState<Business | null>(null);
  const [cid, setCid] = useState('sales-m12');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [highlight, setHighlight] = useState('');
  const [pending, setPending] = useState<{ message_id: string; text: string; timestamp: string } | null>(null);
  useEffect(() => {
    let active = true;
    Promise.all([request<AgentState>(`/api/conversations/${cid}`), request<Business>('/api/business/config')])
      .then(([s, b]) => { if (active) { setState(s); setBusiness(b); setError(''); } })
      .catch(e => { if (active) setError(e.message || 'Backend unavailable. Start the backend and reload.'); });
    return () => { active = false; };
  }, [cid]);
  useEffect(() => {
    if (transcript.current) transcript.current.scrollTop = transcript.current.scrollHeight;
  }, [state?.turns.length]);
  async function send() {
    if (busy || (!pending && !text.trim())) return;
    const body = pending || { message_id: crypto.randomUUID(), text: text.trim(), timestamp: new Date().toISOString() };
    setPending(body); setBusy(true); setError('');
    try { setState(await request<AgentState>(`/api/conversations/${cid}/messages`, body)); setPending(null); setText(''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Backend unavailable. Retry this turn.'); }
    finally { setBusy(false); }
  }
  async function reset() {
    setBusy(true); setError('');
    try { await request('/api/demo/reset', {}); setState(await request<AgentState>(`/api/conversations/${cid}`)); setPending(null); setText(''); }
    catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  async function production() {
    setBusy(true);
    try { setState(await request<AgentState>(`/api/conversations/${cid}/owner-action`, { action: 'start_production' })); }
    catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  function refs(evidence: string[]) { return <span className="evidence">{evidence.map(ref => <a key={ref} href={`#${ref.startsWith('policy.') || ref.startsWith('products.') || ref.startsWith('customizations.') || ref.startsWith('addons.') || ref.startsWith('fulfillment.') ? 'business-rules' : ref}`} onClick={() => { setHighlight(ref); const rules = document.getElementById('business-rules') as HTMLDetailsElement | null; if (ref.includes('.') && rules) rules.open = true; }}>{ref} ↗</a>)}</span>; }
  const readable = (value: string) => value.replaceAll('_', ' ').replace(/^./, c => c.toUpperCase());
  const fieldNames: Record<string, string> = { product: 'Cake', size: 'Size', quantity: 'Quantity', date: 'Date', customizations: 'Extras', addons: 'Add-ons', fulfillment: 'Pickup / delivery', inscription: 'Cake message' };
  const statusNames: Record<string, string> = { inquiry: 'New inquiry', draft: 'Details needed', offered: 'Quote sent', accepted: 'Details confirmed', in_production: 'In simulated production', cancelled: 'Cancelled' };
  function spec(values: Record<string, Value>) { return <dl>{Object.entries(values).map(([key, v]) => <div className="fact" key={key}><dt>{fieldNames[key] || readable(key)}</dt><dd>{key === 'product' ? business?.products[v.value]?.name || readable(v.value) : key === 'size' ? `${v.value} kg` : key === 'inscription' ? v.value : v.value.split(',').map(readable).join(', ') || 'None'}</dd></div>)}</dl>; }
  function offer(o: Offer) { return <div><p><strong>Total ₹{o.total}</strong></p><p className="small muted">Cakes and extras ₹{o.subtotal} · delivery ₹{o.total - o.subtotal} · deposit ₹{o.deposit}</p>{spec(o.spec)}</div>; }
  function commitment(c: Commitment | null) { return c ? offer(c.terms) : <p className="muted small">None recorded</p>; }
  const examples = ['What cakes do you make?', 'I need 1 chocolate cake, 1 kg, on 2026-11-08 for pickup.', 'Make it eggless with floral decoration.', 'Are there any discounts?', 'Yes, go ahead', 'I confirm', 'I paid.', 'The cake needs to be nut-free.'];
  return <div className="shell"><header className="topbar"><Link className="brand" href="/">▣ OrderGuard</Link><span className="studio">THE LITTLE CRUMB / SALES OPERATIONS</span><span className="demo">Synthetic customers · real Meta inference when configured</span></header>
    <div className="intro"><div><p className="eyebrow">YOUR BAKERY, IN ORDER</p><h1>From the first hello to a clear commitment.</h1><p>Friendly conversations. Clear cake orders.</p></div><div className="offline">Local simulator only<br/><span>No Instagram or payment connection</span></div></div>
    <main className="workspace"><aside className="inbox"><div className="pane-title"><h2>Conversations</h2><span>M1.2</span></div>{['sales-m12', 'second-m12'].map((id, i) => <button disabled={busy} key={id} aria-pressed={cid === id} className={`conversation ${cid === id ? 'active' : ''}`} onClick={() => { setCid(id); setState(null); setPending(null); setText(''); }}><span className="avatar">{i ? 'KS' : 'AR'}</span><span><strong>{i ? 'Kabir Shah' : 'Ananya Rao'}</strong><small>Synthetic customer simulator</small></span></button>)}<div className="inbox-note"><strong>Real understanding. Bounded authority.</strong><p>Muse understands customers and composes friendly replies. Catalogue prices stay fixed; exceptions come to you.</p><p><Link href="/fixtures">Open original M0 fixture →</Link></p><button disabled={busy} className="control" onClick={reset}>Reset all simulated conversations</button><p>Reset clears the local demo ledger and capacity reservations.</p></div></aside>
    <section className="transcript" aria-label="Customer simulator"><div className="chat-head"><div><h2>{cid === 'sales-m12' ? 'Ananya Rao' : 'Kabir Shah'}</h2><p className="muted small">Synthetic customer · replies stay in this browser workspace</p></div><span className="tag">Bakery assistant</span></div><div ref={transcript} className="messages" aria-live="polite">{!state && !error && <p role="status">Loading conversation…</p>}{state?.turns.length === 0 && <div className="empty"><h3>Let the conversation begin.</h3><p>Type as a customer below. Muse helps with your cake inquiry. If reply writing is unavailable, we use a checked, friendly response.</p></div>}{state?.turns.map(t => <article tabIndex={-1} id={t.id} key={t.id} className={`message ${t.sender} ${highlight === t.id ? 'highlight' : ''}`}><div className="message-meta"><strong>{t.sender === 'customer' ? 'Customer' : t.sender === 'owner' ? 'Local owner action' : 'The Little Crumb'}</strong></div><p>{t.text}</p><span className="message-id">{new Date(t.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST</span></article>)}{busy && <p role="status">One moment…</p>}</div><div className="composer">{error && <p className="error" role="alert">We couldn’t send this message just now. Please try again.</p>}<label htmlFor="customer-message">Customer simulator message</label><textarea id="customer-message" disabled={busy || !!pending} value={pending?.text || text} onChange={e => setText(e.target.value)} placeholder="Ask about a cake, change an option, or accept an offer…" rows={3}/><button className="control primary" disabled={busy || (!pending && !text.trim())} onClick={send}>{busy ? 'Writing a reply…' : pending ? 'Retry same message' : 'Send customer message'}</button>{pending && !busy && <button className="control" onClick={() => { setPending(null); setError(''); }}>Edit message</button>}<details><summary>Try these customer messages</summary>{examples.map(e => <button className="example" disabled={busy || !!pending} key={e} onClick={() => setText(e)}>{e}</button>)}</details></div></section>
    <aside className="orders"><div className="pane-title"><h2>Order desk</h2><span>{state ? statusNames[state.status] || readable(state.status) : 'Loading'}</span></div>{state && <><div className="order-heading"><span className="tag">{state.turns.length === 0 ? 'Awaiting first message' : state.decision === 'automatic' ? 'Handled automatically' : 'Needs your review'}</span><span className="small">Payment: {state.payment === 'claimed' ? 'Customer says paid · check needed' : 'Not verified'}</span></div>{state.alerts.map((a, i) => <article className="alert critical" key={i}><h3>Owner review</h3><p>{a}</p></article>)}{state.missing_fields.length > 0 && <p className="mock-note">Missing: {state.missing_fields.map(k => fieldNames[k] || readable(k)).join(', ')}</p>}<h3 className="section-title">Customer’s latest request</h3>{spec(state.requested_spec)}<details open><summary>Current quote</summary>{state.offered_terms ? offer(state.offered_terms) : <p className="muted small">No current quote</p>}</details><details open><summary>Confirmed details</summary>{commitment(state.accepted_commitment)}</details><details><summary>Production plan</summary>{commitment(state.production_snapshot)}</details>{state.status === 'accepted' && <button className="control" disabled={busy || state.decision === 'needs_owner'} onClick={production}>Owner: start simulated production</button>}<details><summary>Audit &amp; debug details</summary><p className="small">Interpretation: {state.source || 'Not run'}</p>{state.turns.map(t => <div className="event" key={t.id}><strong>{t.sender} · {t.id}</strong><p>Interpretation: {t.source} · reply: {t.reply_source || 'Not applicable / earlier prototype'}</p></div>)}{Object.entries(state.requested_spec).map(([key, value]) => <div className="event" key={key}><strong>{key}</strong>{refs(value.evidence)}</div>)}{state.offered_terms && <div className="event"><strong>Current quote: {state.offered_terms.id}</strong>{refs(state.offered_terms.evidence)}</div>}{state.accepted_commitment && <div className="event"><strong>Confirmed quote: {state.accepted_commitment.terms.id}</strong>{refs(state.accepted_commitment.evidence)}</div>}{state.events.map(e => <div className="event" key={e.id}><strong>{e.kind}</strong><p>{e.detail}</p>{refs(e.evidence)}</div>)}</details></>}
    <>{error && <details><summary>Connection details</summary><p className="small">{error}</p></details>}</><details id="business-rules"><summary>Business rules · seeded owner configuration</summary>{business && <><p className="small">{business.tone}</p>{Object.entries(business.products).map(([id, p]) => <div className="event" key={id}><strong>{p.name}</strong>{Object.entries(p.sizes).map(([size, amount]) => <p key={size}>{size} kg · ₹{amount}</p>)}</div>)}{(['customizations', 'addons', 'fulfillment'] as const).map(group => <div className="event" key={group}><strong>{group}</strong>{Object.entries(business[group]).map(([id, n]) => <p key={id}>{readable(id)}: ₹{n}</p>)}</div>)}{Object.entries(business.policy).map(([key, value]) => <div className="event" key={key}><strong>{key.replaceAll('_', ' ')}</strong><p>{Array.isArray(value) ? value.join(', ') || 'None' : value}</p></div>)}</>}</details></aside></main><footer className="page-footer">ORDERGUARD / M1.2 LOCAL SIMULATOR<span>Synthetic customers · fixed catalogue prices · Muse-assisted replies with a checked fallback.</span></footer></div>;
}
