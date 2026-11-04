"""Read-only, atomic import of M1/M1.2 SQLite snapshots into PostgreSQL."""
import argparse
import sqlite3
from pathlib import Path
from .agent_models import State
from .bootstrap import bootstrap
from .store import Store


def import_sqlite(path, store):
    source = Path(path).resolve(strict=True)
    # URI mode=ro prevents accidental creation or modification of the source.
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as db:
        db.execute('BEGIN')
        rows = db.execute('SELECT id, state FROM conversations ORDER BY id').fetchall()
    states = []
    for cid, payload in rows:
        state = State.model_validate_json(payload)
        if state.id != cid:
            raise ValueError('Legacy conversation ID does not match its snapshot.')
        states.append(state)
    imported = 0
    with store.transaction():
        for state in states:
            existing = store.get(state.id)
            # Distinguish an absent record from a persisted, empty conversation.
            if store._versions[state.id]:
                if existing != state:
                    raise ValueError('Destination conversation conflicts; entire import rolled back.')
                continue
            store.save(state)
            imported += 1
    return imported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sqlite_path')
    args = parser.parse_args()
    bootstrap()
    count = import_sqlite(args.sqlite_path, Store())
    print(f'Imported {count} conversations; source unchanged. Matching existing records skipped.')


if __name__ == '__main__':
    main()
