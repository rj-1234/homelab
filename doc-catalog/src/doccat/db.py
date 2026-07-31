"""Thin psycopg3 connection helper. No ORM — raw SQL, this is a small service."""
import psycopg

from . import config


def connect() -> psycopg.Connection:
    """A single autocommit-off connection. Callers manage transactions."""
    return psycopg.connect(config.DATABASE_URL)
