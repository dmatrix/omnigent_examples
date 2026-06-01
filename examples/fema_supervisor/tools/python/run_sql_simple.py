"""SQL execution tool — no mlflow, minimal deps."""

from __future__ import annotations

import sqlite3

import pandas as pd
from omniagents_client.tools import tool

from .fema_data import get_disaster_data

_db_conn: sqlite3.Connection | None = None


def _get_connection() -> sqlite3.Connection:
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(":memory:")
        get_disaster_data().to_sql(
            "disaster_data", _db_conn, index=False, if_exists="replace"
        )
    return _db_conn


@tool
def run_sql_simple(sql_query: str) -> str:
    """
    Execute a SQL query against the FEMA disaster data.

    :param sql_query: A valid SQLite SELECT statement.
    :returns: Formatted query results or an error message.
    """
    conn = _get_connection()
    try:
        result_df = pd.read_sql_query(sql_query, conn)
    except Exception as e:
        return f"SQL execution error: {e}\n\nQuery: {sql_query}"

    return f"Results ({len(result_df)} rows):\n{result_df.to_string(index=False)}"
