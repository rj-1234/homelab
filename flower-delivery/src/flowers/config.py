"""Runtime config from env."""
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://flowers:flowers@localhost:5432/flowers"
)
