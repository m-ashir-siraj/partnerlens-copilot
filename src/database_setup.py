"""
Database setup module for PartnerLens Copilot.

This script creates a SQLite database from the processed synthetic PartnerLens files.
Each processed CSV is loaded into a SQLite table.
"""

from pathlib import Path
import sqlite3
import pandas as pd


PROCESSED_DIR = Path("data/processed")
DATABASE_PATH = Path("data/processed/partnerlens.db")

TABLE_FILES = {
    "partners": "partner_master_clean.csv",
    "partner_pricing": "partner_pricing_clean.csv",
    "monthly_partner_metrics": "partner_metrics_clean.csv",
    "partner_current_preview": "partner_current_preview_1000.csv",
}


def load_csv_to_table(conn: sqlite3.Connection, table_name: str, file_name: str) -> None:
    """Load one processed CSV file into a SQLite table."""
    csv_path = PROCESSED_DIR / file_name

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed file not found: {csv_path}. "
            "Confirm the processed files are uploaded to data/processed/."
        )

    df = pd.read_csv(csv_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    print(f"Created table '{table_name}' with {len(df)} rows from {file_name}")


def create_database() -> None:
    """Create SQLite database from processed CSV files."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)

    for table_name, file_name in TABLE_FILES.items():
        load_csv_to_table(conn, table_name, file_name)

    conn.close()

    print(f"Database created at {DATABASE_PATH}")


def main() -> None:
    """Run database creation workflow."""
    create_database()


if __name__ == "__main__":
    main()
