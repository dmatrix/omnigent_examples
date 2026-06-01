"""Self-contained SQL tool — no relative imports, no mlflow."""

from __future__ import annotations

from omniagents_client.tools import tool


@tool
def run_sql_standalone(sql_query: str) -> str:
    """
    Execute a SQL query against the FEMA disaster data.

    :param sql_query: A valid SQLite SELECT statement.
    :returns: Formatted query results or an error message.
    """
    import sqlite3
    import pandas as pd

    conn = sqlite3.connect(":memory:")
    data = [
        {"disaster_id": "DR-4001", "year": 2020, "state": "California", "disaster_type": "Wildfire", "severity": 5, "affected_population": 820000, "federal_aid_amount": 1800000000},
        {"disaster_id": "DR-4031", "year": 2021, "state": "Louisiana", "disaster_type": "Hurricane", "severity": 5, "affected_population": 950000, "federal_aid_amount": 2100000000},
        {"disaster_id": "DR-4066", "year": 2022, "state": "Florida", "disaster_type": "Hurricane", "severity": 5, "affected_population": 1500000, "federal_aid_amount": 2800000000},
        {"disaster_id": "DR-4101", "year": 2023, "state": "Hawaii", "disaster_type": "Wildfire", "severity": 5, "affected_population": 850000, "federal_aid_amount": 2000000000},
        {"disaster_id": "DR-4136", "year": 2024, "state": "Florida", "disaster_type": "Hurricane", "severity": 5, "affected_population": 1300000, "federal_aid_amount": 2500000000},
        {"disaster_id": "DR-4171", "year": 2025, "state": "California", "disaster_type": "Wildfire", "severity": 5, "affected_population": 1100000, "federal_aid_amount": 2400000000},
        {"disaster_id": "DR-4003", "year": 2020, "state": "Louisiana", "disaster_type": "Hurricane", "severity": 5, "affected_population": 760000, "federal_aid_amount": 1500000000},
        {"disaster_id": "DR-4035", "year": 2021, "state": "Kentucky", "disaster_type": "Tornado", "severity": 5, "affected_population": 300000, "federal_aid_amount": 650000000},
        {"disaster_id": "DR-4068", "year": 2022, "state": "Kentucky", "disaster_type": "Flood", "severity": 5, "affected_population": 400000, "federal_aid_amount": 850000000},
        {"disaster_id": "DR-4074", "year": 2022, "state": "Puerto Rico", "disaster_type": "Hurricane", "severity": 5, "affected_population": 1200000, "federal_aid_amount": 2200000000},
    ]
    pd.DataFrame(data).to_sql("disaster_data", conn, index=False, if_exists="replace")

    try:
        result_df = pd.read_sql_query(sql_query, conn)
    except Exception as e:
        return f"SQL execution error: {e}\n\nQuery: {sql_query}"
    finally:
        conn.close()

    return f"Results ({len(result_df)} rows):\n{result_df.to_string(index=False)}"
