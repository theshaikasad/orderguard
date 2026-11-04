from typing import Literal
from pydantic import BaseModel, ConfigDict, AwareDatetime, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Evidence(Contract):
    message_ids: list[str] = Field(min_length=1)


class Fact(Contract):
    value: str
    evidence: Evidence


class Specification(Contract):
    size: Fact
    flavor: Fact
    date: Fact
    dietary: Fact
    inscription: Fact


class Message(Contract):
    id: str
    sender: Literal['customer', 'baker']
    sent_at: AwareDatetime
    text: str


class Order(Contract):
    id: str
    status: Literal['in_production']
    requested: Specification
    accepted: Specification
    production: Specification
    quote: Fact
    payment: Fact
    fulfillment: Fact


class Alert(Contract):
    id: str
    priority: Literal['critical', 'warning']
    title: str
    detail: str
    evidence: Evidence


class Conversation(Contract):
    id: str
    customer_name: str
    channel: str
    messages: list[Message] = Field(min_length=1)
    orders: list[Order]
    alerts: list[Alert]

    @model_validator(mode='after')
    def valid_evidence(self):
        ids = [m.id for m in self.messages]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate message IDs')
        if [m.sent_at for m in self.messages] != sorted(m.sent_at for m in self.messages):
            raise ValueError('Messages must be in source order')
        def walk(value):
            if isinstance(value, dict):
                if 'message_ids' in value and not set(value['message_ids']) <= set(ids):
                    raise ValueError('Evidence must reference this conversation')
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(self.model_dump())
        return self


class Demo(Contract):
    source: Literal['fixture'] = 'fixture'
    mode: Literal['demo']
    conversations: list[Conversation] = Field(min_length=1)

    @model_validator(mode='after')
    def unique_ids(self):
        for ids in ([c.id for c in self.conversations],
                    [m.id for c in self.conversations for m in c.messages],
                    [o.id for c in self.conversations for o in c.orders],
                    [a.id for c in self.conversations for a in c.alerts]):
            if len(ids) != len(set(ids)):
                raise ValueError('IDs must be unique')
        return self
