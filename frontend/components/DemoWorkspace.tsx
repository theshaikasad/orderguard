'use client';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import type { AgentState, Business } from '../lib/agent';
import { fieldNames, OrderFacts, OfferDetails, readable } from './OrderDetails';
import './demo.css';

type Session = { business_id: string; conversation_id: string; business: Business };
type Pending = { message_id: string; text: string; timestamp: string };
const SESSION_KEY = 'orderguard-recording-session-v1';
const pendingKey = (s: Session) => `orderguard-recording-pending-${s.business_id}`;
function storedSession(): Session | null {
  try {
    const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
    return s && /^demo-[a-f0-9]{32}$/.test(s.business_id) && s.conversation_id === 'recording' && s.business?.name ? s : null;
  } catch { return null; }
}
function storedPending(s: Session): Pending | null {
  try { return JSON.parse(localStorage.getItem(pendingKey(s)) || 'null'); } catch { return null; }
}
async function request<T>(path: string, session?: Session | null, body?: unknown): Promise<T> {
  const response = await fetch(`/api/${path}`, { method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(session ? { 'X-Orderguard-Business': session.business_id } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(240_000) });
  if (!response.ok) throw new Error('Please try again.');
  return response.json();
}
function BakeryAvatar({ small = false }: { small?: boolean }) {
  return <span className={`bakery-avatar ${small ? 'small-avatar' : ''}`} aria-hidden="true"><svg width="34" height="34" viewBox="0 0 40 40" fill="none"><path d="M8 28h24v6H8zM10 20h20v8H10z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/><path d="M10 22c3 5 5-3 8 0s5 3 7 0 3 1 5 0M20 20v-7M7 34h26" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/><path d="M20 5s5 6 0 7c-5-1 0-7 0-7Z" fill="currentColor"/></svg></span>;
}
function SendIcon() { return <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m5 12 14-7-5 14-3-6-6-1Zm6 1 8-8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>; }
const time = (timestamp: string) => new Date(timestamp).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
const statusNames: Record<string, string> = { inquiry: 'New conversation', draft: 'Gathering details', offered: 'Quote ready', accepted: 'Order accepted', in_production: 'In production', cancelled: 'Cancelled' };

export default function DemoWorkspace({ view }: { view: 'customer' | 'seller' }) {
  const seller = view === 'seller';
  const [session, setSession] = useState<Session | null>(null);
  const [state, setState] = useState<AgentState | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const [connectionError, setConnectionError] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const transcript = useRef<HTMLDivElement>(null);
  const actionLock = useRef(false);
  const currentSession = useRef<Session | null>(null);
  const atBottom = useRef(true);

  useEffect(() => {
    let active = true;
    const sync = () => {
      const next = storedSession();
      if (next?.business_id !== currentSession.current?.business_id) {
        currentSession.current = next; setSession(next); setState(null); setError(''); setText('');
      }
      setPending(next ? storedPending(next) : null);
    };
    queueMicrotask(() => {
      if (!active) return;
      sync();
      const recovered = storedSession();
      if (view === 'customer' && recovered && storedPending(recovered)) {
        setError('An earlier message is awaiting confirmation. You can retry safely; it will only be processed once.');
      }
    });
    window.addEventListener('storage', sync);
    return () => { active = false; window.removeEventListener('storage', sync); };
  }, [view]);

  useEffect(() => {
    if (!session) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await request<AgentState>(`conversations/${session!.conversation_id}`, session);
        if (active) {
          // A GET begun before a POST must never replace newer committed state.
          setState(previous => !previous || next.turns.length >= previous.turns.length ? next : previous);
          setConnectionError(false);
          const p = storedPending(session!);
          if (p && next.turns.some(t => t.id === p.message_id)) {
            localStorage.removeItem(pendingKey(session!)); setPending(null);
          }
        }
      } catch { if (active) setConnectionError(true); }
      if (active) timer = setTimeout(poll, 1000);
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [session]);

  useEffect(() => {
    if (!pending) return;
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - Date.parse(pending.timestamp)) / 1000)));
    tick(); const timer = setInterval(tick, 1000); return () => clearInterval(timer);
  }, [pending]);

  useEffect(() => {
    if (transcript.current && atBottom.current) transcript.current.scrollTo({ top: transcript.current.scrollHeight, behavior: 'smooth' });
  }, [state?.turns.length, pending, error]);

  async function fresh() {
    if (actionLock.current || pending) return;
    actionLock.current = true; setStarting(true); setError('');
    try {
      const next = await request<Session>('demo/sessions', null, {});
      localStorage.setItem(SESSION_KEY, JSON.stringify(next));
      currentSession.current = next; setSession(next); setState(null); setText(''); setPending(null); atBottom.current = true;
    } catch { setError('We couldn’t start a fresh demo. Check that the bakery is published and the service is running, then try again.'); }
    finally { actionLock.current = false; setStarting(false); }
  }

  async function send() {
    if (!session || actionLock.current || (!pending && !text.trim())) return;
    const body = pending || { message_id: crypto.randomUUID(), text: text.trim(), timestamp: new Date().toISOString() };
    actionLock.current = true; setSending(true); setError(''); setPending(body); setText(''); atBottom.current = true;
    localStorage.setItem(pendingKey(session), JSON.stringify(body));
    try {
      const next = await request<AgentState>(`conversations/${session.conversation_id}/messages`, session, body);
      if (currentSession.current?.business_id === session.business_id) {
        setState(next); setPending(null); localStorage.removeItem(pendingKey(session));
      }
    } catch { setError('Your message hasn’t been confirmed yet. Retry safely; it will only be processed once.'); }
    finally { actionLock.current = false; setSending(false); }
  }

  const waiting = !!pending && !error;
  const showPending = pending && !state?.turns.some(t => t.id === pending.message_id);
  const business = session?.business || null;
  const title = business?.name || 'The Little Crumb';
  const lastReply = state?.turns.filter(t => t.sender === 'baker').at(-1);
  const quote = state?.offered_terms;
  const accepted = state?.accepted_commitment;

  const chat = <section className="demo-chat" aria-label={seller ? 'Live customer conversation' : 'Customer chat'}>
    <header className="demo-chat-head"><BakeryAvatar/><div><h1>{seller ? 'Ananya Rao' : title}</h1><p>{seller ? 'Fictional customer · Bakery inquiry' : 'A little joy, freshly baked.'}</p></div><span className="chat-label">{seller ? 'Customer conversation' : 'BAKERY & CAKES'}</span></header>
    <div className="demo-messages" ref={transcript} onScroll={() => { const el = transcript.current; if (el) atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100; }} role="log" aria-label="Messages" aria-live="polite" aria-relevant="additions text">
      <div className="demo-date">{state?.turns[0] ? new Date(state.turns[0].timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }) : 'A fresh conversation'}</div>
      {!state?.turns.length && !pending && <div className="demo-welcome"><BakeryAvatar/><span className="demo-kicker">MADE FOR YOUR LITTLE CELEBRATIONS</span><h2>Something sweet<br/>starts with a hello.</h2><p>{seller ? 'Customer messages and order details will appear here as the conversation unfolds.' : 'Ask about a cake, make it your own, and plan a little celebration.'}</p>{!session && <button className="demo-button" disabled={starting} onClick={fresh}>{starting ? 'Opening your conversation…' : 'Start a fresh demo'}</button>}</div>}
      {state?.turns.filter(t => t.sender !== 'owner').map(t => <article id={`demo-${t.id}`} key={t.id} className={`demo-bubble ${t.sender === 'customer' ? 'from-customer' : 'from-bakery'}`}><p>{t.text}</p><footer><time dateTime={t.timestamp}>{time(t.timestamp)}</time>{t.sender === 'customer' && <span aria-label="Saved">✓</span>}</footer></article>)}
      {showPending && <article className="demo-bubble from-customer is-pending"><p>{pending.text}</p><footer>{error ? 'Awaiting retry' : 'Sending…'}</footer></article>}
      {waiting && <div className="demo-waiting" role="status"><div className="typing-dots" aria-hidden="true"><i/><i/><i/></div><span>{seller ? 'Muse is preparing the bakery’s reply' : 'The bakery’s assistant is working on your message'}<small>Live AI · {elapsed}s elapsed</small></span></div>}
    </div>
    {seller ? <div className="demo-chat-note"><span className="live-dot"/>Conversation and order details update automatically.</div> : <form className="demo-composer" onSubmit={e => { e.preventDefault(); void send(); }}>
      {error && <p className="demo-error" role="alert">{error}</p>}
      <div className="demo-input-wrap"><textarea aria-label="Message the bakery" placeholder="Message the bakery…" value={text} maxLength={4000} rows={2} disabled={!session || !!pending} onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }}/><button type="submit" className="demo-send" aria-label={pending && error ? 'Retry message' : 'Send message'} disabled={!session || sending || (waiting) || (!pending && !text.trim())}>{pending && error ? 'Retry' : <SendIcon/>}</button></div>
      <p className="demo-composer-note">{waiting ? 'A thoughtful reply takes a moment. You can keep this window open.' : 'Enter to send · Shift + Enter for a new line'}</p>
    </form>}
  </section>;

  return <div className={`demo-page ${seller ? 'seller-demo' : 'customer-demo'}`}>
    <nav className="demo-nav" aria-label="Demo navigation"><Link href="/" className="demo-brand"><span className="brand-mark">o<span>g</span></span>OrderGuard<span className="demo-nav-divider"/>{seller ? 'Seller workspace' : 'Customer experience'}</Link><div className="demo-nav-actions"><span className="demo-live"><span className="live-dot"/>Simulated customer · Live AI</span><Link href={seller ? '/demo/customer' : '/demo/seller'} target="_blank" rel="noopener">{seller ? 'Open customer view ↗' : 'Open seller view ↗'}</Link><button onClick={fresh} disabled={starting || !!pending}>{starting ? 'Starting…' : 'Fresh demo'}</button></div></nav>
    {connectionError && <div className="demo-connection" role="status">Reconnecting to the bakery… Your saved conversation is safe.</div>}
    {error && seller && <p className="demo-error" role="alert">{error}</p>}
    {seller ? <main className="demo-seller-main"><header className="demo-heading"><div><p className="demo-kicker">THE LITTLE DETAILS, TAKEN CARE OF</p><h1>Your conversations. In order.</h1><p>Muse handles the conversation. You stay in control of the commitments.</p></div><span className="demo-business"><BakeryAvatar small/>{title}</span></header><div className="demo-seller-grid"><aside className="demo-inbox"><p className="demo-kicker">INBOX</p><h2>Conversations</h2><div className="demo-inbox-item"><span className="customer-avatar">AR</span><div><strong>Ananya Rao</strong><p>{state?.turns.filter(t => t.sender === 'customer').at(-1)?.text || 'A new celebration'}</p><span>Synthetic customer</span></div></div><div className="demo-inbox-bottom"><span className="live-dot"/>Live, with guardrails<p>Fixed prices. Sourced details.<br/>Important changes come to you.</p></div></aside>{chat}<aside className="demo-order-desk" aria-label="Order desk"><header><p className="demo-kicker">ORDER DESK</p><span className={`demo-status ${state?.decision === 'needs_owner' ? 'review' : ''}`}>{state?.decision === 'needs_owner' ? 'Owner review needed' : statusNames[state?.status || 'inquiry']}</span></header>
      {state?.alerts.map((alert, i) => <article className="demo-review-alert" key={i}><span>! &nbsp; OWNER REVIEW</span><h3>A change needs your attention</h3><p>{alert}</p>{accepted && <strong>The accepted order is preserved.</strong>}</article>)}
      {quote && <section className="demo-order-card demo-quote"><div className="demo-card-heading"><h2>Current quotation</h2><span>Fixed price</span></div><OfferDetails offer={quote} business={business}/></section>}
      <section className={`demo-order-card ${accepted ? 'demo-accepted' : ''}`}><div className="demo-card-heading"><h2>{accepted ? '✓ Accepted commitment' : 'Accepted commitment'}</h2></div>{accepted ? <><OfferDetails offer={accepted.terms} business={business}/><p className="demo-preserved">Saved at acceptance. Later requests do not change these terms.</p></> : <p className="demo-placeholder">Waiting for the customer to accept a valid quote.</p>}</section>
      <section className="demo-order-card"><div className="demo-card-heading"><h2>Customer’s request</h2>{state?.source === 'meta' && <span>From conversation</span>}</div>{state && Object.keys(state.requested_spec).length ? <OrderFacts values={state.requested_spec} business={business}/> : <p className="demo-placeholder">The details will come together here.</p>}{!!state?.missing_fields.length && <p className="demo-missing">Still needed: {state.missing_fields.map(k => fieldNames[k] || readable(k)).join(', ')}</p>}</section>

      {!quote && <p className="demo-placeholder">{accepted ? 'No new quotation is active.' : 'A quote appears once the required details are clear.'}</p>}
      {state?.production_snapshot && <section className="demo-order-card"><h2>Frozen production plan</h2><OfferDetails offer={state.production_snapshot.terms} business={business}/></section>}
      {lastReply?.reply_source === 'fallback' && <p className="demo-fallback">The latest reply used the checked fallback. Muse interpretation was retained.</p>}
      <details className="demo-audit"><summary>Evidence &amp; AI audit</summary><p>Interpretation: {state?.source === 'meta' ? 'Live Meta Muse' : 'Not run'}</p><p>Latest reply: {lastReply?.reply_source === 'meta' ? 'Live Meta Muse' : lastReply?.reply_source || 'Not run'}</p><p>Isolated synthetic capacity · Payment not verified</p>{Object.entries(state?.requested_spec || {}).map(([field, value]) => <div className="demo-evidence" key={field}><strong>{fieldNames[field] || readable(field)}</strong>{value.evidence.map(id => <a key={id} href={`#demo-${id}`}>{state?.turns.find(t => t.id === id)?.text || id}</a>)}</div>)}<details><summary>Technical record</summary><pre>{JSON.stringify({ business: session?.business_id, conversation: state?.id, metrics: state?.last_turn_metrics, events: state?.events }, null, 2)}</pre></details></details>
    </aside></div></main> : <main className="demo-customer-main"><div className="demo-customer-intro"><span className="demo-kicker">A LITTLE CELEBRATION, A SIMPLE CONVERSATION</span><h2>Made personal.<br/><em>Handled with care.</em></h2><p>A fictional bakery. A real AI conversation.<br/>Your order comes together, one message at a time.</p><div className="demo-flourish" aria-hidden="true">✳</div><span className="demo-footnote">POWERED BY ORDERGUARD</span></div>{chat}</main>}
    <footer className="demo-footer">Fictional bakery &amp; customer · No real orders, payments or Instagram messages<span>Meta Muse interprets · Catalogue rules authorize · Owners review exceptions</span></footer>
  </div>;
}
