import os
import sys

try:
    import psycopg2
except ImportError:
    print("Este script requer psycopg2. Instale com:")
    print("    pip install psycopg2-binary --break-system-packages")
    sys.exit(1)


# ==============================================================================
# CONFIGURAÇÃO
# ================================

DB_CONFIG = dict(
    host=os.environ.get("ECOCIENTE_DB_HOST", "localhost"),
    port=os.environ.get("ECOCIENTE_DB_PORT", "5432"),
    dbname=os.environ.get("ECOCIENTE_DB_NAME", "ecociente"),
    user=os.environ.get("ECOCIENTE_DB_USER", "postgres"),
    password=os.environ.get("ECOCIENTE_DB_PASSWORD", "postgres"),
)
#  connection string completa
DSN = os.environ.get("ECOCIENTE_DSN")

# ==============================================================================
# HELPERS DE BANCO
#===============================================================================

def get_connection():
    if DSN:
        conn = psycopg2.connect(DSN)
    else:
        conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def fetch_id(cur, sql, params):
    """Executa um INSERT ... RETURNING <pk> e devolve o id gerado."""
    cur.execute(sql, params)
    return cur.fetchone()[0]


def call_procedure(cur, sql, params):
    cur.execute(sql, params)

