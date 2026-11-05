'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '../lib/workspace';
export default function Navigation() {
  const [shops,setShops] = useState<{id:string;name:string}[]>([]);
  const [selected,setSelected] = useState('little-crumb-v1');
  const [error,setError] = useState('');
  useEffect(()=>{ api<{id:string;name:string}[]>('businesses').then(rows=>{setShops(rows);setSelected(localStorage.getItem('orderguard-business') || 'little-crumb-v1');}).catch(e=>setError(String(e))); },[]);
  function choose(id:string) { localStorage.setItem('orderguard-business',id); window.location.reload(); }
  async function create() { try { const b = await api<{id:string}>('businesses',{}); localStorage.setItem('orderguard-business',b.id); window.location.assign(new URL('/settings',window.location.origin).toString()); } catch(e) {setError(String(e));} }
  return <nav className="navigation" aria-label="Workspace"><Link className="brand" href="/overview">▣ OrderGuard</Link><div className="nav-links"><Link href="/overview">Overview</Link><Link href="/">Conversations</Link><Link href="/settings">Business settings</Link><Link href="/lab">Scenario Lab</Link><Link href="/channels">Instagram</Link></div><label className="shop-select">Demo business switcher <select aria-label="Selected business" value={selected} onChange={e=>choose(e.target.value)}>{shops.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label><button className="control" onClick={create}>＋ New business</button>{error&&<span role="alert">{error}</span>}</nav>;
}
