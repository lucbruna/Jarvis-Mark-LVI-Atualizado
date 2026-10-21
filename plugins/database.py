"""JARVIS plugin - query databases (SQLite/PostgreSQL/MySQL)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "database",
    "description": "Run SQL queries against SQLite (default) or PostgreSQL/MySQL. Actions: query, tables, schema.",
    "brief": "Database: run SQL queries (SQLite/Postgres/MySQL).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "query|tables|schema"},
            "sql": {"type": "STRING", "description": "SQL query (query)."},
            "db_path": {"type": "STRING", "description": "SQLite db path (default: memory/data.db)."},
            "connection_string": {"type": "STRING", "description": "Postgres/MySQL connection string (optional)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    db_path = params.get("db_path") or str(Path(__file__).resolve().parents[1] / "memory" / "data.db")
    conn_str = params.get("connection_string", "")

    # PostgreSQL/MySQL via sqlalchemy if available
    if conn_str:
        try:
            import sqlalchemy
            engine = sqlalchemy.create_engine(conn_str)
            with engine.connect() as conn:
                if action == "tables":
                    res = conn.execute(sqlalchemy.text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
                    rows = [r[0] for r in res]
                    return outcome.done("database", note="\n".join(rows) or "no tables", tables=rows)
                if action == "schema":
                    tbl = params.get("table", "")
                    res = conn.execute(sqlalchemy.text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{tbl}'"))
                    rows = [f"{r[0]}: {r[1]}" for r in res]
                    return outcome.done("database", note="\n".join(rows), columns=rows)
                sql = params.get("sql", "")
                res = conn.execute(sqlalchemy.text(sql))
                cols = list(res.keys()) if hasattr(res, "keys") else []
                rows = [dict(r._mapping) for r in res.fetchmany(50)]
                out = json.dumps(rows, default=str, indent=2)[:4000]
                return outcome.done("database", note=out, rows=rows, columns=cols)
        except ImportError:
            return outcome.failed("database", "sqlalchemy not installed. Run: pip install sqlalchemy")
        except Exception as e:
            return outcome.failed("database", str(e))

    # SQLite default
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        if action == "tables":
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            rows = [r[0] for r in cur.fetchall()]
            conn.close()
            return outcome.done("database", note="\n".join(rows) or "no tables", tables=rows)
        if action == "schema":
            tbl = params.get("table", "")
            cur.execute(f"PRAGMA table_info({tbl})")
            rows = [f"{r[1]}: {r[2]}" for r in cur.fetchall()]
            conn.close()
            return outcome.done("database", note="\n".join(rows), columns=rows)
        sql = params.get("sql", "")
        if not sql:
            conn.close()
            return outcome.failed("database", "sql required")
        cur.execute(sql)
        if sql.strip().lower().startswith(("select", "pragma", "with")):
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = [dict(zip(cols, r)) for r in cur.fetchmany(50)]
            conn.close()
            return outcome.done("database", note=json.dumps(rows, default=str)[:4000], rows=rows, columns=cols)
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return outcome.done("database", note=f"{affected} rows affected")
    except Exception as e:
        return outcome.failed("database", str(e))
