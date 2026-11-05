import { NextRequest } from 'next/server';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const endpoint = path.join('/');
  const allowed = /^(?:channels\/instagram(?:\/(?:replays-reset|replays(?:\/[a-zA-Z0-9_-]+(?:\/messages)?)?|accounts\/[a-zA-Z0-9_-]+\/disconnect))?|business\/config|businesses|settings(?:\/(?:draft|chat|publish|pause))?|overview|lab(?:\/(?:runs|reset|runs\/[a-zA-Z0-9_-]+\/step))?|v1\/demo|demo\/reset|conversations\/[a-zA-Z0-9_-]{1,60}(?:\/(?:messages|owner-action))?)$/;
  if (!allowed.test(endpoint) && endpoint !== 'demo/sessions') return Response.json({ detail: 'Unknown API route.' }, { status: 404 });
  const base = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  try {
    const upstream = await fetch(`${base}/api/${endpoint}`, {
      method: request.method,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...(request.headers.get('X-Orderguard-Business') ? { 'X-Orderguard-Business': request.headers.get('X-Orderguard-Business')! } : {}) },
      body: request.method === 'POST' ? await request.text() : undefined,
      cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(240_000),
    });
    return new Response(upstream.body, { status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('content-type') || 'application/json', ...(upstream.headers.get('server-timing') ? {'Server-Timing':upstream.headers.get('server-timing')!} : {}), ...(upstream.headers.get('x-orderguard-database-statements') ? {'X-Orderguard-Database-Statements':upstream.headers.get('x-orderguard-database-statements')!} : {}) } });
  } catch {
    return Response.json({ detail: 'The agent service is temporarily unavailable. Retry this message.' }, { status: 503 });
  }
}
export const GET = forward;
export const POST = forward;
