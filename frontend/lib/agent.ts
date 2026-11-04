export type Value = { value: string; evidence: string[] };
export type Offer = { id: string; spec: Record<string, Value>; subtotal: number; total: number; deposit: number; evidence: string[]; message_id: string };
export type Commitment = { terms: Offer; evidence: string[] };
export type AgentState = {
  id: string; source: 'meta' | 'mock' | null;
  turns: { id: string; sender: 'customer' | 'baker' | 'owner'; timestamp: string; text: string; source: string; reply_source?: 'meta' | 'mock' | 'fallback' | null }[];
  requested_spec: Record<string, Value>; offered_terms: Offer | null;
  accepted_commitment: Commitment | null; production_snapshot: Commitment | null;
  status: string; payment: string; missing_fields: string[]; decision: string;
  alerts: string[]; events: { id: string; kind: string; message_id: string; evidence: string[]; detail: string }[];
};
export type Business = { name: string; products: Record<string, { name: string; sizes: Record<string, number> }>; customizations: Record<string, number>; addons: Record<string, number>; fulfillment: Record<string, number>; policy: Record<string, string | number | string[]>; tone: string };
