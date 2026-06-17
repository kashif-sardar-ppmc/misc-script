# db.py
import psycopg2
from contextlib import contextmanager
from config import DB_CONFIG


@contextmanager
def get_db_cursor():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
