import os
import mysql.connector
from mysql.connector import pooling

_pool = None


def init_pool():
    global _pool
    _pool = pooling.MySQLConnectionPool(
        pool_name="campus_cleaning_pool",
        pool_size=10,
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "campus_cleaning"),
    )
    return _pool


def get_connection():
    if _pool is None:
        init_pool()
    return _pool.get_connection()


def query(sql, params=None, fetchone=False):
    """Run a SELECT and return rows as a list of dicts (or one dict/None)."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        if fetchone:
            row = cur.fetchone()
            cur.fetchall()
            return row
        rows = cur.fetchall()
        return rows
    finally:
        conn.close()


def execute(sql, params=None):
    """Run an INSERT/UPDATE/DELETE. Returns (lastrowid, rowcount)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid, cur.rowcount
    finally:
        conn.close()


def test_connection():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchall()
    finally:
        conn.close()
