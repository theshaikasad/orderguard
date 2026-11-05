"""Request-local timing of SQL executions; never stores SQL or bound data."""
from contextvars import ContextVar
from time import perf_counter
from sqlalchemy import event
sql_metrics = ContextVar('orderguard_sql_metrics',default=None)


def instrument(engine):
    @event.listens_for(engine,'before_cursor_execute')
    def before(conn,cursor,statement,parameters,context,executemany):
        context.orderguard_started=perf_counter()
    @event.listens_for(engine,'after_cursor_execute')
    def after(conn,cursor,statement,parameters,context,executemany):
        metrics=sql_metrics.get()
        if metrics is not None:
            metrics.append((perf_counter()-context.orderguard_started)*1000)
