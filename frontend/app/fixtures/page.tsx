'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { Demo, Evidence, Fact } from '../../lib/contracts';

export default function Workspace() {
  const [data, setData] = useState<Demo | null>(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(0);
  const [highlight, setHighlight] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/v1/demo`, { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error('API unavailable'); return r.json(); })
      .then((d: Demo) => { if (d.mode !== 'demo' || !d.conversations?.length) throw new Error('Invalid demo'); setData(d); })
      .catch(e => { if (e.name !== 'AbortError') setError('Cannot load the demo. Start the backend on port 8000, then retry.'); });
    return () => controller.abort();
  }, [attempt]);
  function evidence(e: Evidence) {
    return <span className="evidence">{e.message_ids.map(id => <a key={id} href={`#${id}`} onClick={() => setHighlight(id)} aria-label={`View source message ${id}`}>{id} ↗</a>)}</span>;
  }
  function fact(label: string, f: Fact) { return <div className="fact" key={label}><dt>{label}</dt><dd>{f.value}{evidence(f.evidence)}</dd></div>; }
  const c = data?.conversations[selected];
  return <div className="shell">
    <header className="topbar"><Link className="brand" href="/">▣ <span>OrderGuard</span></Link><span className="studio">THE LITTLE CRUMB / WORKSPACE</span><span className="demo">Demo data · synthetic conversations</span></header>
    <div className="intro"><div><p className="eyebrow">YOUR BAKERY, IN ORDER</p><h1>A little clarity. A lot less rework.</h1><p>Keep what was requested separate from what you promised.</p></div><div className="offline">Seeded snapshot<br/><span>Meta & Instagram not connected</span></div></div>
    {!c ? <div className="load" role={error ? 'alert' : 'status'}>{error || 'Loading bakery workspace…'}{error && <button onClick={() => { setError(''); setAttempt(attempt + 1); }}>Retry connection</button>}</div> : <main className="workspace">
      <aside className="inbox"><div className="pane-title"><h2>Conversations</h2><span>{data!.conversations.length}</span></div><p className="muted small">Fictional customer inbox</p><nav aria-label="Conversations">{data!.conversations.map((item, i) => <button className={`conversation ${selected === i ? 'active' : ''}`} key={item.id} aria-pressed={selected === i} onClick={() => { setSelected(i); setHighlight(''); }}><span className="avatar">{item.customer_name.split(' ').map(n => n[0]).join('')}</span><span><strong>{item.customer_name}</strong><small>{item.orders.length ? 'Birthday cake · review needed' : 'Cupcake inquiry'}</small><span className={`tag ${item.alerts.length ? 'warm' : ''}`}>{item.alerts.length ? `${item.alerts.length} review alerts` : 'No order yet'}</span></span></button>)}</nav><div className="inbox-note">✦ <strong>Every detail has a source.</strong><p>Select a message reference on the right to find it in the conversation.</p></div></aside>
      <section className="transcript" aria-label="Customer transcript"><div className="chat-head"><div><h2>{c.customer_name}</h2><p className="muted small">{c.channel}</p></div><span className="tag">Read only</span></div><div className="messages"><div className="day">4 NOVEMBER 2026 · TIMES IN IST</div>{c.messages.map(m => <article tabIndex={-1} id={m.id} key={m.id} className={`message ${m.sender} ${highlight === m.id ? 'highlight' : ''}`}><div className="message-meta"><strong>{m.sender === 'baker' ? 'The Little Crumb' : c.customer_name}</strong><time dateTime={m.sent_at}>{new Date(m.sent_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })}</time></div><p>{m.text}</p><span className="message-id">{m.id}</span></article>)}</div><footer className="chat-footer">Synthetic transcript · sending messages is not enabled</footer></section>
      <aside className="orders"><div className="pane-title"><h2>Order desk</h2><span>STATIC</span></div>{!c.orders.length ? <div className="empty"><h3>Just a conversation, for now.</h3><p>No order or commitment has been recorded.</p></div> : c.orders.map(o => <div key={o.id}><div className="order-heading"><strong>{o.id}</strong><span className="tag">In production · seeded</span></div><section className="alert-list" aria-label="Review alerts">{c.alerts.map(a => <article className={`alert ${a.priority}`} key={a.id}><p className="eyebrow">{a.priority === 'critical' ? '⚑ HIGH PRIORITY' : 'REVIEW NEEDED'}</p><h3>{a.title}</h3><p>{a.detail}</p>{evidence(a.evidence)}</article>)}</section><h3 className="section-title">Requested specification</h3><p className="muted small">Latest customer request · not a promise</p><dl>{Object.entries(o.requested).map(([key, f]) => fact(key, f))}</dl><details open><summary>Accepted plan</summary><dl>{Object.entries(o.accepted).map(([key, f]) => fact(key, f))}</dl></details><details><summary>Production snapshot · unchanged</summary><dl>{Object.entries(o.production).map(([key, f]) => fact(key, f))}</dl></details><h3 className="section-title">Commercial details</h3><dl>{fact('Earlier quote', o.quote)}{fact('Payment', o.payment)}{fact('Fulfillment', o.fulfillment)}</dl><p className="mock-note">Manually authored fixture, not AI output. Approval actions arrive in a later milestone.</p></div>)}</aside>
    </main>}
    <footer className="page-footer">ORDERGUARD / M0 PROTOTYPE <span>Turn messy customer conversations into reliable orders.</span></footer>
  </div>;
}
