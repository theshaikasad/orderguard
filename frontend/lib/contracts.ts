export type Evidence = { message_ids: string[] };
export type Fact = { value: string; evidence: Evidence };
export type Specification = Record<'size' | 'flavor' | 'date' | 'dietary' | 'inscription', Fact>;
export type Message = { id: string; sender: 'customer' | 'baker'; sent_at: string; text: string };
export type Order = { id: string; status: 'in_production'; requested: Specification; accepted: Specification; production: Specification; quote: Fact; payment: Fact; fulfillment: Fact };
export type Alert = { id: string; priority: 'critical' | 'warning'; title: string; detail: string; evidence: Evidence };
export type Conversation = { id: string; customer_name: string; channel: string; messages: Message[]; orders: Order[]; alerts: Alert[] };
export type Demo = { mode: 'demo'; conversations: Conversation[] };
