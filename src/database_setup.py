"""
Validated database build module for PartnerLens Copilot.

Phase 8 database-build controls:

- Validates every required processed CSV before database creation.
- Validates required columns and numeric fields.
- Detects duplicate and missing primary identifiers.
- Detects orphan partner IDs across related tables.
- Builds the database in a temporary file.
- Replaces the existing database only after a successful build.
- Creates indexes for approved PartnerLens query patterns.
- Records source-file hashes, row counts, and build metadata.
- Runs SQLite integrity checks before publishing the database.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import os
import sqlite3
import uuid

import pandas as pd


# This assumes the file is located at src/database_setup.py.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATABASE_PATH = PROCESSED_DIR / "partnerlens.db"

DATABASE_SCHEMA_VERSION = "phase8-v1"


@dataclass(frozen=True)
class TableSpec:
    """Configuration and validation rules for one SQLite table."""

    file_name: str
    required_columns: tuple[str, ...]
    non_null_columns: tuple[str, ...] = ()
    unique_columns: tuple[str, ...] = ()
    numeric_columns: tuple[str, ...] = ()


TABLE_SPECS: dict[str, TableSpec] = {
    "partners": TableSpec(
        file_name="partner_master_clean.csv",
        required_columns=(
            "partner_id",
            "partner_name",
            "partner_type",
            "industry_vertical",
            "partner_size",
            "partner_status",
            "state",
            "region",
            "risk_tier",
            "kyc_status",
            "pci_level",
        ),
        non_null_columns=(
            "partner_id",
            "partner_name",
        ),
        unique_columns=(
            "partner_id",
        ),
    ),
    "partner_pricing": TableSpec(
        file_name="partner_pricing_clean.csv",
        required_columns=(
            "partner_id",
            "pricing_plan_id",
            "recommended_pricing_plan_id",
            "negotiated_bps",
            "negotiated_per_txn_fee_usd",
            "exception_flag",
            "approval_status",
        ),
        non_null_columns=(
            "partner_id",
        ),
        numeric_columns=(
            "negotiated_bps",
            "negotiated_per_txn_fee_usd",
        ),
    ),
    "monthly_partner_metrics": TableSpec(
        file_name="partner_metrics_clean.csv",
        required_columns=(
            "partner_id",
        ),
        non_null_columns=(
            "partner_id",
        ),
    ),
    "partner_current_preview": TableSpec(
        file_name="partner_current_preview_1000.csv",
        required_columns=(
            "partner_id",
            "partner_name",
            "industry_vertical",
            "state",
            "txn_growth_pct",
            "payment_volume_usd",
            "txn_count",
            "net_revenue_usd",
        ),
        non_null_columns=(
            "partner_id",
            "partner_name",
        ),
        unique_columns=(
            "partner_id",
        ),
        numeric_columns=(
            "txn_growth_pct",
            "payment_volume_usd",
            "txn_count",
            "net_revenue_usd",
        ),
    ),
}


INDEX_STATEMENTS = (
    """
    CREATE UNIQUE INDEX idx_partners_partner_id
    ON partners(partner_id)
    """,
    """
    CREATE INDEX idx_partners_name
    ON partners(partner_name)
    """,
    """
    CREATE INDEX idx_partners_state
    ON partners(state)
    """,
    """
    CREATE INDEX idx_partners_risk_tier
    ON partners(risk_tier)
    """,
    """
    CREATE INDEX idx_partner_pricing_partner_id
    ON partner_pricing(partner_id)
    """,
    """
    CREATE INDEX idx_partner_pricing_exception
    ON partner_pricing(exception_flag)
    """,
    """
    CREATE INDEX idx_monthly_metrics_partner_id
    ON monthly_partner_metrics(partner_id)
    """,
    """
    CREATE UNIQUE INDEX idx_current_preview_partner_id
    ON partner_current_preview(partner_id)
    """,
    """
    CREATE INDEX idx_current_preview_state_growth
    ON partner_current_preview(state, txn_growth_pct)
    """,
    """
    CREATE INDEX idx_current_preview_payment_volume
    ON partner_current_preview(payment_volume_usd)
    """,
)


class DatabaseBuildError(Exception):
    """Raised when the PartnerLens database cannot be built safely."""


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 hash of a source file."""

    hasher = hashlib.sha256()

    with file_path.open("rb") as source_file:
        for chunk in iter(
            lambda: source_file.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def find_duplicate_columns(columns: list[str]) -> list[str]:
    """Return duplicated column names."""

    column_series = pd.Series(columns)

    return sorted(
        column_series[
            column_series.duplicated(keep=False)
        ].unique()
    )


def validate_non_null_columns(
    dataframe: pd.DataFrame,
    table_name: str,
    columns: tuple[str, ...],
) -> None:
    """Validate critical columns for missing or blank values."""

    for column in columns:
        missing_mask = dataframe[column].isna()

        blank_mask = (
            dataframe[column]
            .astype("string")
            .str.strip()
            .eq("")
            .fillna(False)
        )

        invalid_count = int(
            (missing_mask | blank_mask).sum()
        )

        if invalid_count:
            raise DatabaseBuildError(
                f"Table '{table_name}' contains "
                f"{invalid_count} missing or blank value(s) "
                f"in required field '{column}'."
            )


def validate_unique_columns(
    dataframe: pd.DataFrame,
    table_name: str,
    columns: tuple[str, ...],
) -> None:
    """Validate uniqueness for configured key columns."""

    if not columns:
        return

    duplicated_mask = dataframe.duplicated(
        subset=list(columns),
        keep=False,
    )

    if duplicated_mask.any():
        duplicate_count = int(duplicated_mask.sum())

        duplicate_examples = (
            dataframe.loc[
                duplicated_mask,
                list(columns),
            ]
            .head(5)
            .to_dict(orient="records")
        )

        raise DatabaseBuildError(
            f"Table '{table_name}' contains "
            f"{duplicate_count} row(s) with duplicate key values. "
            f"Example duplicates: {duplicate_examples}"
        )


def convert_numeric_columns(
    dataframe: pd.DataFrame,
    table_name: str,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    """Convert configured fields into numeric values."""

    converted_dataframe = dataframe.copy()

    for column in columns:
        original_values = converted_dataframe[column]

        converted_values = pd.to_numeric(
            original_values,
            errors="coerce",
        )

        invalid_mask = (
            original_values.notna()
            & converted_values.isna()
        )

        if invalid_mask.any():
            invalid_examples = (
                original_values[invalid_mask]
                .astype(str)
                .head(5)
                .tolist()
            )

            raise DatabaseBuildError(
                f"Table '{table_name}' contains nonnumeric "
                f"values in '{column}'. "
                f"Examples: {invalid_examples}"
            )

        converted_dataframe[column] = converted_values

    return converted_dataframe


def load_and_validate_csv(
    table_name: str,
    table_spec: TableSpec,
    processed_dir: Path,
) -> tuple[pd.DataFrame, Path]:
    """
    Load and validate one processed PartnerLens CSV.

    The database is not modified during this step.
    """

    csv_path = processed_dir / table_spec.file_name

    if not csv_path.exists():
        raise DatabaseBuildError(
            f"Required processed file was not found: "
            f"{table_spec.file_name}. "
            "Confirm that all Phase 8 processed files are present "
            "in data/processed."
        )

    if not csv_path.is_file():
        raise DatabaseBuildError(
            f"The configured source is not a file: "
            f"{table_spec.file_name}."
        )

    try:
        header_dataframe = pd.read_csv(
            csv_path,
            nrows=0,
        )
    except Exception as error:
        raise DatabaseBuildError(
            f"The header of '{table_spec.file_name}' "
            "could not be read."
        ) from error

    original_columns = list(header_dataframe.columns)
    normalized_columns = [
        str(column).strip()
        for column in original_columns
    ]

    duplicate_columns = find_duplicate_columns(
        normalized_columns
    )

    if duplicate_columns:
        raise DatabaseBuildError(
            f"File '{table_spec.file_name}' contains duplicate "
            f"column names after normalization: "
            f"{duplicate_columns}"
        )

    # Preserve identifier fields as text.
    identifier_dtype = {
        original_column: "string"
        for original_column in original_columns
        if str(original_column).strip().endswith("_id")
    }

    try:
        dataframe = pd.read_csv(
            csv_path,
            dtype=identifier_dtype,
        )
    except Exception as error:
        raise DatabaseBuildError(
            f"File '{table_spec.file_name}' could not be read."
        ) from error

    dataframe.columns = normalized_columns

    if dataframe.empty:
        raise DatabaseBuildError(
            f"File '{table_spec.file_name}' contains no data rows."
        )

    missing_columns = sorted(
        set(table_spec.required_columns)
        - set(dataframe.columns)
    )

    if missing_columns:
        raise DatabaseBuildError(
            f"Table '{table_name}' is missing required columns: "
            + ", ".join(missing_columns)
        )

    validate_non_null_columns(
        dataframe=dataframe,
        table_name=table_name,
        columns=table_spec.non_null_columns,
    )

    validate_unique_columns(
        dataframe=dataframe,
        table_name=table_name,
        columns=table_spec.unique_columns,
    )

    dataframe = convert_numeric_columns(
        dataframe=dataframe,
        table_name=table_name,
        columns=table_spec.numeric_columns,
    )

    return dataframe, csv_path


def validate_partner_relationships(
    table_dataframes: dict[str, pd.DataFrame],
) -> None:
    """
    Confirm that related tables reference valid partner IDs.

    Every partner_id in child tables must exist in the partners table.
    """

    master_partner_ids = set(
        table_dataframes["partners"]["partner_id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    child_tables = (
        "partner_pricing",
        "monthly_partner_metrics",
        "partner_current_preview",
    )

    for table_name in child_tables:
        child_partner_ids = set(
            table_dataframes[table_name]["partner_id"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        orphan_partner_ids = sorted(
            child_partner_ids - master_partner_ids
        )

        if orphan_partner_ids:
            raise DatabaseBuildError(
                f"Table '{table_name}' contains partner IDs "
                "that are not present in the partners table. "
                f"Examples: {orphan_partner_ids[:5]}"
            )


def create_indexes(
    connection: sqlite3.Connection,
) -> None:
    """Create indexes for approved PartnerLens query patterns."""

    for index_statement in INDEX_STATEMENTS:
        connection.execute(index_statement)


def create_build_metadata(
    connection: sqlite3.Connection,
    build_id: str,
    build_timestamp: str,
    source_paths: dict[str, Path],
    table_dataframes: dict[str, pd.DataFrame],
) -> None:
    """Store database lineage and reproducibility metadata."""

    build_info = pd.DataFrame(
        [
            {
                "build_id": build_id,
                "built_at_utc": build_timestamp,
                "schema_version": DATABASE_SCHEMA_VERSION,
                "table_count": len(table_dataframes),
                "total_row_count": sum(
                    len(dataframe)
                    for dataframe in table_dataframes.values()
                ),
            }
        ]
    )

    build_info.to_sql(
        "database_build_info",
        connection,
        if_exists="fail",
        index=False,
    )

    manifest_records = []

    for table_name, dataframe in table_dataframes.items():
        source_path = source_paths[table_name]

        manifest_records.append(
            {
                "build_id": build_id,
                "table_name": table_name,
                "source_file": source_path.name,
                "source_sha256": calculate_sha256(
                    source_path
                ),
                "row_count": len(dataframe),
                "column_count": len(dataframe.columns),
                "column_names": ",".join(
                    dataframe.columns.astype(str)
                ),
            }
        )

    manifest_dataframe = pd.DataFrame(
        manifest_records
    )

    manifest_dataframe.to_sql(
        "database_source_manifest",
        connection,
        if_exists="fail",
        index=False,
    )


def verify_database(
    connection: sqlite3.Connection,
    expected_row_counts: dict[str, int],
) -> None:
    """Verify integrity and loaded table row counts."""

    integrity_result = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()

    if not integrity_result or integrity_result[0] != "ok":
        raise DatabaseBuildError(
            "SQLite integrity verification failed."
        )

    for table_name, expected_count in expected_row_counts.items():
        actual_count = connection.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]

        if actual_count != expected_count:
            raise DatabaseBuildError(
                f"Row-count verification failed for "
                f"'{table_name}'. Expected {expected_count}, "
                f"but found {actual_count}."
            )


def remove_temporary_database_files(
    temporary_path: Path,
) -> None:
    """Remove temporary SQLite database and sidecar files."""

    candidate_paths = (
        temporary_path,
        Path(f"{temporary_path}-wal"),
        Path(f"{temporary_path}-shm"),
        Path(f"{temporary_path}-journal"),
    )

    for candidate_path in candidate_paths:
        candidate_path.unlink(missing_ok=True)


def create_database(
    processed_dir: Path | str = PROCESSED_DIR,
    database_path: Path | str = DATABASE_PATH,
) -> dict[str, int]:
    """
    Build and publish the validated PartnerLens SQLite database.

    A temporary database is created first. The existing database is
    replaced only after all validation and integrity checks pass.

    Returns:
        Dictionary containing the loaded row count for each table.
    """

    resolved_processed_dir = Path(
        processed_dir
    ).expanduser().resolve()

    resolved_database_path = Path(
        database_path
    ).expanduser().resolve()

    if not resolved_processed_dir.exists():
        raise DatabaseBuildError(
            "The processed-data directory could not be found."
        )

    resolved_database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_database_path = (
        resolved_database_path.parent
        / f".{resolved_database_path.name}.building"
    )

    remove_temporary_database_files(
        temporary_database_path
    )

    table_dataframes: dict[str, pd.DataFrame] = {}
    source_paths: dict[str, Path] = {}

    # Validate every input before creating any database file.
    for table_name, table_spec in TABLE_SPECS.items():
        dataframe, source_path = load_and_validate_csv(
            table_name=table_name,
            table_spec=table_spec,
            processed_dir=resolved_processed_dir,
        )

        table_dataframes[table_name] = dataframe
        source_paths[table_name] = source_path

    validate_partner_relationships(
        table_dataframes
    )

    build_id = uuid.uuid4().hex

    build_timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    expected_row_counts = {
        table_name: len(dataframe)
        for table_name, dataframe
        in table_dataframes.items()
    }

    try:
        with sqlite3.connect(
            temporary_database_path
        ) as connection:
            connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            connection.execute(
                "PRAGMA journal_mode = DELETE"
            )
            connection.execute(
                "PRAGMA synchronous = FULL"
            )

            for table_name, dataframe in table_dataframes.items():
                dataframe.to_sql(
                    table_name,
                    connection,
                    if_exists="fail",
                    index=False,
                )

            create_indexes(connection)

            create_build_metadata(
                connection=connection,
                build_id=build_id,
                build_timestamp=build_timestamp,
                source_paths=source_paths,
                table_dataframes=table_dataframes,
            )

            # Collect statistics used by SQLite's query planner.
            connection.execute("ANALYZE")

            verify_database(
                connection=connection,
                expected_row_counts=expected_row_counts,
            )

            connection.commit()

        # Publish only after the temporary database passes verification.
        os.replace(
            temporary_database_path,
            resolved_database_path,
        )

    except Exception:
        remove_temporary_database_files(
            temporary_database_path
        )
        raise

    print()
    print("PartnerLens database build completed.")
    print(f"Schema version: {DATABASE_SCHEMA_VERSION}")
    print(f"Build ID: {build_id}")
    print(f"Database: {resolved_database_path.name}")
    print()

    for table_name, row_count in expected_row_counts.items():
        print(
            f"- {table_name}: "
            f"{row_count:,} rows"
        )

    print(
        f"- Total rows: "
        f"{sum(expected_row_counts.values()):,}"
    )

    return expected_row_counts


def main() -> None:
    """Run the PartnerLens database build workflow."""

    try:
        create_database()

    except DatabaseBuildError as error:
        print(
            f"Database build failed: {error}"
        )
        raise SystemExit(1) from error

    except Exception as error:
        print(
            "Database build failed because of an unexpected error."
        )
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
