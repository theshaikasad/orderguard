"""Explicit single-batch durable-inbox processor. Never sends outbound messages.

Run after configuring the adapter, or for synthetic replay verification. No
background service or in-memory queue is required. Error retries have stored
backoff and a three-attempt limit; restart cannot duplicate order mutations.
"""
import argparse
from datetime import datetime,timezone
from sqlalchemy import select,or_
from .database import get_engine,instagram_inbox
from .store import Store
from .provider import MetaProvider
from .instagram import process_one,register


def main():
    p=argparse.ArgumentParser();p.add_argument('--register-account');p.add_argument('--business');p.add_argument('--token-env');p.add_argument('--once',action='store_true');p.add_argument('--limit',type=int,default=10);args=p.parse_args()
    if args.register_account:
        if not args.business or not args.token_env:p.error('--business and --token-env are required')
        register(Store(business=args.business),args.register_account,args.token_env)
        print('Account configured locally. Permissions and OAuth remain unverified; outbound is disabled.')
        return
    if not args.once:p.error('Use --once to explicitly process one batch; no automatic sending is performed.')
    now=datetime.now(timezone.utc)
    with get_engine().connect() as conn:
        rows=conn.execute(select(instagram_inbox.c.business_id,instagram_inbox.c.account_id,instagram_inbox.c.id).where(
            instagram_inbox.c.status.in_(['pending','error']),instagram_inbox.c.attempts<3,
            or_(instagram_inbox.c.next_attempt_at.is_(None),instagram_inbox.c.next_attempt_at<=now)).limit(min(max(args.limit,1),100))).all()
    for row in rows:
        try:
            result=process_one(Store(business=row.business_id),MetaProvider(),row.account_id,row.id)
            print('Inbox result:',result['status'],'attempts:',result['attempts'])
        except Exception:
            # Never print credentials, customer content or upstream response bodies.
            print('Inbox processing aborted safely; inspect scoped status before retrying.')


if __name__=='__main__':main()
