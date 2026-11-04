"""Idempotent schema migration and fictional seed. Run before serving requests."""
from pathlib import Path
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from .database import get_engine, business_id, businesses, customers
from .agent_models import Business

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / '.env')


def migrate(engine=None):
    engine = engine or get_engine()
    config = Config(str(BACKEND / 'alembic.ini'))
    with engine.begin() as conn:
        # Serialize concurrent container startups, including migration version writes.
        conn.execute(text('SELECT pg_advisory_xact_lock(7180246001)'))
        config.attributes['connection'] = conn
        command.upgrade(config, 'head')


def seed(engine=None, business=None):
    engine = engine or get_engine()
    bid = business or business_id()
    config = Business.model_validate_json((BACKEND.parent / 'fixtures' / 'business.json').read_text()).model_dump(mode='json')
    config['id'] = bid
    with engine.begin() as conn:
        conn.execute(insert(businesses).values(id=bid, config=config).on_conflict_do_nothing())
        conn.execute(insert(customers).values([
            {'business_id': bid, 'id': 'ananya-synthetic', 'name': 'Ananya Rao'},
            {'business_id': bid, 'id': 'kabir-synthetic', 'name': 'Kabir Shah'},
        ]).on_conflict_do_nothing())


def bootstrap():
    migrate()
    seed()


if __name__ == '__main__':
    bootstrap()
    print('PostgreSQL schema ready; fictional seed present.')
