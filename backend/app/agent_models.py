from datetime import datetime, timezone
from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Incoming(Strict):
    message_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    text: str = Field(min_length=1, max_length=4000)
    timestamp: AwareDatetime = Field(strict=False, default_factory=lambda: datetime.now(timezone.utc))


    @field_validator('message_id')
    @classmethod
    def reserved_ids(cls, value):
        if value.startswith(('reply-', 'owner-')):
            raise ValueError('Reserved message ID prefix')
        return value


class Patch(Strict):
    field: Literal['product', 'size', 'quantity', 'date', 'customizations', 'addons', 'fulfillment', 'inscription']
    value: str
    message_id: str
    quote: str = Field(min_length=1)


class Interpretation(Strict):
    intents: list[Literal['inquiry', 'revise', 'accept', 'discount_request', 'payment_claim', 'cancel', 'allergy', 'dispute', 'fulfillment_check']]
    association: Literal['current', 'new', 'unknown', 'multiple']
    patches: list[Patch]
    missing_fields: list[str]
    proposed_action: Literal['clarify', 'quote', 'accept', 'review', 'cancel']


class Turn(Strict):
    id: str
    sender: Literal['customer', 'baker', 'owner']
    timestamp: AwareDatetime
    text: str
    source: Literal['meta', 'fixture', 'mock']
    reply_source: Literal['meta', 'mock', 'fallback'] | None = None


class SourcedValue(Strict):
    value: str
    evidence: list[str]


class Offer(Strict):
    id: str
    spec: dict[str, SourcedValue]
    subtotal: int
    # Read historical SQLite snapshots without rewriting their commercial terms.
    discount_percent: int = 0
    total: int
    deposit: int
    evidence: list[str]
    message_id: str


class Commitment(Strict):
    terms: Offer
    evidence: list[str]


class Event(Strict):
    id: str
    kind: str
    message_id: str
    evidence: list[str]
    detail: str
    terms: Offer | None = None
    requested_spec: dict[str, SourcedValue] | None = None


class State(Strict):
    id: str
    source: Literal['meta', 'mock'] | None = None
    turns: list[Turn] = Field(default_factory=list)
    requested_spec: dict[str, SourcedValue] = Field(default_factory=dict)
    offered_terms: Offer | None = None
    awaiting_acceptance_for: str | None = None
    accepted_commitment: Commitment | None = None
    production_snapshot: Commitment | None = None
    status: Literal['inquiry', 'draft', 'offered', 'accepted', 'in_production', 'cancelled'] = 'inquiry'
    review_required: bool = False
    payment: Literal['unknown', 'claimed'] = 'unknown'
    missing_fields: list[str] = Field(default_factory=list)
    decision: Literal['automatic', 'needs_owner'] = 'automatic'
    alerts: list[str] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    assistant_reply: str | None = None


class ProductionRequest(Strict):
    action: Literal['start_production']


class Product(Strict):
    name: str
    sizes: dict[str, int]


class Policy(Strict):
    hours: str
    lead_days: int
    daily_capacity: int
    closed_dates: list[str]
    deposit_percent: int
    pricing: Literal['fixed']
    cancellation: str
    dietary: str
    escalation: str
    automatable_actions: list[str]
    availability: str


class Business(Strict):
    id: str
    name: str
    currency: str
    tone: str
    products: dict[str, Product]
    customizations: dict[str, int]
    addons: dict[str, int]
    fulfillment: dict[str, int]
    policy: Policy


class ResetResponse(Strict):
    status: Literal['reset']
