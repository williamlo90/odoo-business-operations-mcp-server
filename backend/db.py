from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from backend.config import settings


@contextmanager
def connection():
    with psycopg.connect(
        settings.database_url.get_secret_value(), row_factory=dict_row,
        connect_timeout=3, options="-c statement_timeout=5000 -c lock_timeout=3000",
    ) as conn:
        yield conn
