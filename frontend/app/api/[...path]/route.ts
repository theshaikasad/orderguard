import { NextRequest } from 'next/server';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const endpoint = path.join('/');
  const allowed = /^(?:business\/config|v1\/demo|demo\/reset|conversations\/[a-zA-Z0-9_-]{1,60}(?:\/(?:messages|owner-action))?)$/;
  if (!allowed.test(endpoint)) return Response.json({ detail: 'Unknown API route.' }, { status: 404 });
  const base = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  try {
    const upstream = await fetch(`${base}/api/${endpoint}`, {
      method: request.method,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: request.method === 'POST' ? await request.text() : undefined,
      cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(120_000),
    });
    return new Response(upstream.body, { status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('content-type') || 'application/json' } });
  } catch {
    return Response.json({ detail: 'The bakery service is temporarily unavailable. Retry this message.' }, { status: 503 });
  }
}
export const GET = forward;
export const POST = forward;
