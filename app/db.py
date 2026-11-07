"""Small parameterized SQL layer; one connection per request or CLI context."""
from contextlib import contextmanager
import pymysql
from flask import current_app, g


def connect(config):
    return pymysql.connect(
        host=config['DB_HOST'], port=int(config['DB_PORT']),
        user=config['DB_USER'], password=config['DB_PASSWORD'],
        database=config['DB_NAME'], charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor, autocommit=False,
        init_command="SET time_zone = '+00:00'", connect_timeout=5,
    )


def get_db():
    if 'db' not in g:
        g.db = connect(current_app.config)
    return g.db


def query(sql, params=(), one=False):
    with get_db().cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()


def execute(sql, params=()):
    with get_db().cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.lastrowid


@contextmanager
def transaction():
    connection = get_db()
    connection.begin()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def close_db(_error=None):
    connection = g.pop('db', None)
    if connection is not None:
        connection.rollback()
        connection.close()
