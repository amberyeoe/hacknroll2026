import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        database_path = Path(current_app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        db = g._database = sqlite3.connect(database_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


def close_db(exception=None):
    db = g.pop("_database", None)
    if db is not None:
        db.close()


def init_db():
    schema_path = Path(current_app.root_path) / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")
    db = get_db()
    db.executescript(schema)
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
