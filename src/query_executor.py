"""
Query execution module for PartnerLens Copilot.
"""

from pathlib import Path
import sqlite3
import pandas as pd


DATABASE_PATH = Path("data/processed/partnerlens.db")


def execute_query(sql: str, db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """Execute validated SQL against the SQLite database."""
    conn = sqlite3.connect(db_path)
    result_df = pd.read_sql_query(sql, conn)
    conn.close()
    return result_df
