"""Atomic PostgreSQL persistence behind the existing agent State contract."""
import json
from contextlib import contextmanager
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from fastapi import HTTPException
from .agent_models import State, Business
from .database import get_engine, business_id, businesses, conversations, messages, events

CUSTOMER_FOR_CONVERSATION = {
    'sales-demo': 'ananya-synthetic', 'sales-m12': 'ananya-synthetic',
    'second-customer': 'kabir-synthetic', 'second-m12': 'kabir-synthetic',
}


class Store:
    def __init__(self, url=None, business=None):
        self.engine = get_engine(url)
        self.business_id = business or business_id()
        self._session = None
        self._versions = {}

    def reopen(self):
        return Store(self.engine.url, self.business_id)

    @contextmanager
    def transaction(self):
        if self._session is not None:
            yield self
            return
        with Session(self.engine, expire_on_commit=False) as session:
            self._session = session
            original_versions = self._versions.copy()
            try:
                with session.begin():
                    # All writers for this business, across processes, share this
                    # lock. Held through interpretation, capacity checks and save.
                    row = session.execute(select(businesses.c.id).where(
                        businesses.c.id == self.business_id).with_for_update()).first()
                    if row is None:
                        raise RuntimeError('Business seed is missing. Run app.bootstrap.')
                    yield self
            except BaseException:
                self._versions = original_versions
                raise
            finally:
                self._session = None

    @contextmanager
    def _read(self):
        if self._session is not None:
            yield self._session
        else:
            with Session(self.engine) as session:
                yield session

    def _scope(self, table):
        return table.c.business_id == self.business_id

    def catalogue(self):
        with self._read() as session:
            config = session.execute(select(businesses.c.config).where(businesses.c.id == self.business_id)).scalar_one()
            return Business.model_validate_json(json.dumps(config)).model_dump()

    def get(self, cid):
        with self._read() as session:
            row = session.execute(select(conversations.c.state, conversations.c.version).where(
                self._scope(conversations), conversations.c.id == cid)).first()
        self._versions[cid] = row.version if row else 0
        return State.model_validate_json(json.dumps(row.state)) if row else State(id=cid)

    def all(self):
        with self._read() as session:
            rows = session.execute(select(conversations.c.state).where(self._scope(conversations))).scalars().all()
        return [State.model_validate_json(json.dumps(value)) for value in rows]

    def save(self, state):
        # Keep the caller's previously read version across standalone saves.
        expected = self._versions.get(state.id, 0)
        with self.transaction():
            session = self._session
            row = session.execute(select(conversations).where(
                self._scope(conversations), conversations.c.id == state.id)).mappings().first()
            if (row['version'] if row else 0) != expected:
                raise HTTPException(409, 'Conversation changed. Reload before retrying.')
            data = state.model_dump(mode='json')
            old = row['state'] if row else {'turns': [], 'events': []}
            for key in ('turns', 'events'):
                if data[key][:len(old[key])] != old[key]:
                    raise HTTPException(409, 'Existing messages and audit events cannot be rewritten.')
            values = dict(state=data, version=expected + 1)
            if row:
                session.execute(update(conversations).where(self._scope(conversations),
                    conversations.c.id == state.id).values(**values))
            else:
                session.execute(insert(conversations).values(business_id=self.business_id, id=state.id,
                    customer_id=CUSTOMER_FOR_CONVERSATION.get(state.id), **values))
            for table, key in ((messages, 'turns'), (events, 'events')):
                additions = []
                for pos, item in enumerate(data[key][len(old[key]):], start=len(old[key])):
                    entry = dict(business_id=self.business_id, conversation_id=state.id,
                                 id=item['id'], position=pos, data=item)
                    if key == 'turns':
                        entry['sender'] = item['sender']
                    additions.append(entry)
                if additions:
                    session.execute(insert(table), additions)
            self._versions[state.id] = expected + 1

    def reset(self):
        with self.transaction():
            self._session.execute(delete(conversations).where(self._scope(conversations)))
            self._versions.clear()
