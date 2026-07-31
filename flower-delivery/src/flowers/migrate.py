"""Apply SQL migrations in order. Idempotent — tracks applied files in a table."""
from pathlib import Path

from . import db

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def main() -> None:
    conn = db.connect()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(filename text PRIMARY KEY, applied_at timestamptz DEFAULT now())"
            )
            cur.execute("SELECT filename FROM schema_migrations")
            done = {r[0] for r in cur.fetchall()}

        for sql_file in sorted(MIGRATIONS.glob("*.sql")):
            if sql_file.name in done:
                continue
            print(f"applying {sql_file.name}")
            with conn.cursor() as cur:
                cur.execute(sql_file.read_text())
                cur.execute(
                    "INSERT INTO schema_migrations(filename) VALUES (%s)",
                    (sql_file.name,),
                )
    print("migrations up to date")


if __name__ == "__main__":
    main()
