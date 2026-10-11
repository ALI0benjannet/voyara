"""Crée les bases de données manquantes sur le Postgres local (dev sans Docker).

Usage : .venv\\Scripts\\python scripts\\create_databases.py
Lit la connexion dans services/auth/.env (host/port/user/password).
"""

import sys
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DBS = ["voyara", "voyara_catalog", "voyara_booking", "voyara_payment", "voyara_review"]


def parse_env(path: Path) -> dict:
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    return values


def main() -> int:
    env = parse_env(Path(__file__).resolve().parents[1] / "services" / "auth" / ".env")
    conn = psycopg2.connect(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    for db in DBS:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
        if cur.fetchone():
            print(f"  = {db} (existe déjà)")
        else:
            cur.execute(f'CREATE DATABASE "{db}"')
            print(f"  + {db} (créée)")
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
