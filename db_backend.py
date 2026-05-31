"""
Capa de acceso a datos compatible con SQLite (local) y PostgreSQL (Neon en la nube).
"""
import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
IS_POSTGRES = DATABASE_URL.startswith("postgres")

if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras
    IntegrityError = psycopg2.IntegrityError
    OperationalError = psycopg2.OperationalError
else:
    IntegrityError = sqlite3.IntegrityError
    OperationalError = sqlite3.OperationalError

if getattr(__import__("sys"), "frozen", False):
    _BASE_DIR = os.path.dirname(__import__("sys").executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SQLITE_PATH = os.environ.get(
    "STOCKVIBE_DB_PATH",
    os.path.join(_BASE_DIR, "inventory.db"),
)


class _RowDict:
    def __init__(self, mapping):
        self._mapping = mapping

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self._mapping.values())[key]
        return self._mapping[key]

    def keys(self):
        return self._mapping.keys()

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self):
        return len(self._mapping)


class _CursorWrapper:
    def __init__(self, cursor, is_postgres):
        self._cursor = cursor
        self._is_postgres = is_postgres
        self.lastrowid = None

    def execute(self, sql, params=None):
        params = params or ()
        adapted = _adapt_sql(sql)
        if self._is_postgres and _should_return_id(adapted):
            adapted = adapted.rstrip().rstrip(";") + " RETURNING id"
            self._cursor.execute(adapted, params)
            row = self._cursor.fetchone()
            self.lastrowid = row["id"] if row else None
        else:
            self._cursor.execute(adapted, params)
            if not self._is_postgres:
                self.lastrowid = self._cursor.lastrowid

    def executemany(self, sql, params_list):
        self._cursor.executemany(_adapt_sql(sql), params_list)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._is_postgres:
            return _RowDict(dict(row))
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        if self._is_postgres:
            return [_RowDict(dict(r)) for r in rows]
        return rows


class _ConnectionWrapper:
    def __init__(self, conn, is_postgres):
        self._conn = conn
        self._is_postgres = is_postgres

    def cursor(self):
        if self._is_postgres:
            return _CursorWrapper(
                self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor),
                True,
            )
        return _CursorWrapper(self._conn.cursor(), False)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params or ())
        return cur


def _is_insert(sql):
    return sql.lstrip().upper().startswith("INSERT")


def _should_return_id(sql):
    """Solo tablas con columna serial id; settings usa key como PK."""
    if not _is_insert(sql):
        return False
    upper = sql.upper()
    if "RETURNING" in upper:
        return False
    if "INTO SETTINGS" in upper:
        return False
    return True


def _adapt_sql(sql):
    if not IS_POSTGRES:
        return sql

    adapted = sql
    adapted = adapted.replace(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        "INSERT INTO settings (key, value) VALUES (%s, %s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
    )
    adapted = adapted.replace("date(timestamp)", "DATE(timestamp::timestamp)")
    adapted = adapted.replace("?", "%s")
    return adapted


def get_db_connection():
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public")
        return _ConnectionWrapper(conn, True)

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return _ConnectionWrapper(conn, False)


def get_postgres_ddl():
    """DDL compatible con PostgreSQL para init_db."""
    return [
        """
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            description TEXT,
            purchase_price DOUBLE PRECISION NOT NULL,
            sale_price DOUBLE PRECISION NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            min_stock INTEGER NOT NULL DEFAULT 5
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            timestamp TEXT NOT NULL,
            total_amount DOUBLE PRECISION NOT NULL,
            total_cost DOUBLE PRECISION NOT NULL,
            total_profit DOUBLE PRECISION NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'contado',
            customer_name TEXT,
            amount_paid DOUBLE PRECISION NOT NULL DEFAULT 0.0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sale_items (
            id SERIAL PRIMARY KEY,
            sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
            quantity INTEGER NOT NULL,
            purchase_price DOUBLE PRECISION NOT NULL,
            sale_price DOUBLE PRECISION NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            phone TEXT DEFAULT ''
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS credit_payments (
            id SERIAL PRIMARY KEY,
            sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
            timestamp TEXT NOT NULL,
            amount DOUBLE PRECISION NOT NULL
        )
        """,
    ]
