export function businessHeaders(): Record<string, string> {
  const id = typeof window !== 'undefined' ? localStorage.getItem('orderguard-business') : null;
  return id ? { 'X-Orderguard-Business': id } : {};
}
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/${path}`, { method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json', ...businessHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store' });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check the values and try again.');
  return data;
}
export type Config = {
  id: string; name: string; category: string; location: string; currency: string; language: string; tone: string;
  delivery_zones: Record<string,string[]>; commercial_reviewed: boolean; extra_units: Record<string, string>; approval_rules: string[];
  products: Record<string, {name: string; unit: string; sizes: Record<string, number>}>;
  customizations: Record<string, number>; addons: Record<string, number>; fulfillment: Record<string, number>;
  policy: { hours: string; capacity_unit: 'items'|'orders'; lead_days: number; lead_hours: number | null; daily_capacity: number; closed_dates: string[];
    deposit_percent: number; pricing: string; cancellation: string; dietary: string; escalation: string;
    automatable_actions: string[]; availability: string };
};
export type Settings = {config: Config; revision: number; questions: string[]; issues: string[]; active_version: number;
  paused: boolean; versions: {version: number; config: Config}[]; history: {speaker: string; text: string; source?: string; edits?: unknown[]}[]};
