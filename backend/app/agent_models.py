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
    field: Literal['product', 'size', 'quantity', 'date', 'customizations', 'addons', 'fulfillment', 'delivery_address', 'inscription']
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
    configuration_version: int | None = None
    configuration_snapshot: dict | None = None
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
    last_turn_metrics: dict = Field(default_factory=dict)
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
    name: str = Field(min_length=1, max_length=200)
    unit: str = "kg"
    sizes: dict[str, int]

    @field_validator("sizes")
    @classmethod
    def valid_prices(cls, value):
        if any(not key or amount < 0 or amount > 10000000 for key, amount in value.items()):
            raise ValueError("Prices must be nonnegative integer INR amounts")
        return value


class Policy(Strict):
    hours: str
    capacity_unit: Literal["items", "orders"] = "items"
    lead_hours: int | None = Field(default=None, ge=0, le=8760)
    lead_days: int = Field(ge=0, le=365)
    daily_capacity: int = Field(ge=0, le=10000)
    closed_dates: list[str]

    @field_validator('closed_dates')
    @classmethod
    def valid_dates(cls, values):
        from datetime import date
        for value in values:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError('Use YYYY-MM-DD dates')
        return values
    deposit_percent: int = Field(ge=0, le=100)
    pricing: Literal['fixed']
    cancellation: str
    dietary: str
    escalation: str
    automatable_actions: list[str]
    availability: str


class Business(Strict):
    id: str
    name: str
    category: str = ""
    location: str = ""
    language: Literal["English"] = "English"
    commercial_reviewed: bool = False
    require_delivery_details: bool = False
    delivery_zones: dict[str, list[str]] = Field(default_factory=dict)
    extra_units: dict[str, Literal["per_item", "per_size"]] = Field(default_factory=dict)
    approval_rules: list[Literal["unsupported_request", "dietary", "accepted_change", "refund_dispute", "exact_slot", "all_orders"]] = Field(default_factory=list)
    currency: Literal["INR"]
    tone: str
    products: dict[str, Product]
    customizations: dict[str, int]
    addons: dict[str, int]
    fulfillment: dict[str, int]
    policy: Policy

    @field_validator('customizations', 'addons', 'fulfillment')
    @classmethod
    def valid_amounts(cls, values):
        if any(not key or value < 0 or value > 10000000 for key, value in values.items()):
            raise ValueError('Charges must be nonnegative integer INR amounts')
        return values


class ResetResponse(Strict):
    status: Literal['reset']
