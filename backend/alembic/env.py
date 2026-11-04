from alembic import context
from app.database import metadata, get_engine

# Bootstrap supplies a connection under the migration advisory lock. Direct
# Alembic commands also work; URLs/credentials are never printed or put in ini.
connection = context.config.attributes.get('connection')
if context.is_offline_mode():
    raise RuntimeError('Use an online PostgreSQL migration connection.')

def migrate(conn):
    context.configure(connection=conn, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()

if connection is not None:
    migrate(connection)
else:
    with get_engine().begin() as conn:
        migrate(conn)
