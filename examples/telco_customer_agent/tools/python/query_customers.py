"""Query customer and device data from the local telco SQLite database."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from omniagents_client.tools import tool


def _find_db() -> Path:
    candidates = [
        Path(os.getcwd()) / "examples" / "tools" / "data" / "telco.db",
        Path(__file__).resolve().parent.parent.parent.parent / "tools" / "data" / "telco.db",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


@tool
def query_customers(sql_query: str) -> str:
    """
    Execute a SQL query against the customers and devices tables in the telco database.

    :param sql_query: A valid SQLite SELECT statement to run against the customers and/or devices tables. You can JOIN them via subscriptions.
    :returns: Formatted query results or an error message.
    """
    db_path = _find_db()
    if not db_path.exists():
        return f"Error: database not found at {db_path}. Run: python examples/tools/create_telco_db.py"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(sql_query)
        rows = cursor.fetchall()
        if not rows:
            return f"Query returned 0 rows.\n\nSQL: {sql_query}"
        columns = rows[0].keys()
        lines = ["\t".join(columns)]
        for row in rows:
            lines.append("\t".join(str(v) for v in row))
        return f"Results ({len(rows)} rows):\n" + "\n".join(lines)
    except Exception as e:
        return f"SQL execution error: {e}\n\nQuery: {sql_query}"
    finally:
        conn.close()
