"""Crea la base de datos de SQL Server si todavía no existe.

SQL Server no crea la base sola (ver docs/database.md); sin este paso, el
primer `docker compose -f docker-compose.prod.yml up` fallaba en
`wait_for_db.py`. Se conecta a `master` con las mismas variables DB_* que
usa Django y nunca imprime credenciales.

Uso: python scripts/ensure_database.py [--timeout 90]
"""

import argparse
import os
import sys
import time

import pyodbc


def connection_string() -> str:
    trust = os.environ.get("DB_TRUST_SERVER_CERTIFICATE", "true").lower() in {"1", "true", "yes"}
    return (
        f"DRIVER={{{os.environ.get('DB_DRIVER', 'ODBC Driver 18 for SQL Server')}}};"
        f"SERVER={os.environ.get('DB_HOST', 'localhost')},{os.environ.get('DB_PORT', '1433')};"
        f"DATABASE=master;UID={os.environ['DB_USER']};PWD={os.environ['DB_PASSWORD']};"
        + ("TrustServerCertificate=yes;" if trust else "")
    )


def ensure_database(timeout: int) -> None:
    name = os.environ["DB_NAME"]
    if not name.replace("_", "").isalnum():
        sys.exit("DB_NAME solo admite letras, números y guion bajo.")
    deadline = time.monotonic() + timeout
    while True:
        try:
            with pyodbc.connect(connection_string(), autocommit=True, timeout=5) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT 1 FROM sys.databases WHERE name = ?", name)
                if cursor.fetchone():
                    print(f"La base de datos {name} ya existe.")
                else:
                    cursor.execute(f"CREATE DATABASE [{name}]")
                    print(f"Base de datos {name} creada.")
                return
        except pyodbc.Error:
            if time.monotonic() > deadline:
                sys.exit("SQL Server no respondió a tiempo.")
            print("SQL Server no disponible todavía, reintentando...")
            time.sleep(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=90)
    ensure_database(parser.parse_args().timeout)
