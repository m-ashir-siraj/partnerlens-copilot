"""
Phase 8 data preparation and validation module for PartnerLens Copilot.

This module validates the processed synthetic PartnerLens datasets before
they are loaded into SQLite.

Phase 8 controls include:

- Required-file validation
- Canonical schema validation using configs/schema_metadata.json
- Missing key and duplicate key checks
- Numeric and date-field validation
- State-code validation
- Synthetic-record flag validation
- Cross-table partner_id integrity checks
- Preview-to-master consistency checks
- SHA-256 file lineage
- Machine-readable validation and manifest reports

This module validates processed files. It does not modify or overwrite
the processed datasets.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json

import pandas as pd


# The file is expected to be located at:
# partnerlens-copilot/src/data_preparation.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SCHEMA_METADATA_PATH = (
    PROJECT_ROOT / "configs" / "schema_metadata.json"
)

PHASE8_REPORT_DIR = PROJECT_ROOT / "artifacts" / "phase8"

VALIDATION_REPORT_PATH = (
    PHASE8_REPORT_DIR / "data_validation_report.csv"
)

DATA_MANIFEST_PATH = (
    PHASE8_REPORT_DIR / "data_manifest.csv"
)


class DataPreparationError(Exception):
    """Raised when processed PartnerLens data fails validation."""


@dataclass(frozen=True)
class DatasetSpec:
    """
    Validation configuration for one processed dataset.

    Attributes:
        file_name: CSV filename in data/processed.
        schema_key: Key in schema_metadata.json, when applicable.
        required_columns: Additional minimum required columns.
        key_columns: Columns that should uniquely identify each row.
        critical_columns: Columns that cannot be missing or blank.
        numeric_columns: Columns expected to contain numeric values.
        nonnegative_columns: Numeric fields that cannot be negative.
        date_columns: Columns expected to contain valid dates.
        expected_row_count: Expected baseline row count.
    """

    file_name: str
    schema_key: str | None
    required_columns: tuple[str, ...]
    key_columns: tuple[str, ...]
    critical_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...] = ()
    nonnegative_columns: tuple[str, ...] = ()
    date_columns: tuple[str, ...] = ()
    expected_row_count: int | None = None


@dataclass(frozen=True)
class DataPreparationResult:
    """Summary returned by the Phase 8 validation workflow."""

    passed: bool
    passed_checks: int
    warning_checks: int
    failed_checks: int
    validated_files: int
    validation_report_path: Path
    manifest_path: Path


DATASET_SPECS: dict[str, DatasetSpec] = {
    "partners": DatasetSpec(
        file_name="partner_master_clean.csv",
        schema_key="partners",
        required_columns=(
            "partner_id",
            "partner_name",
            "state",
            "risk_tier",
            "kyc_status",
        ),
        key_columns=("partner_id",),
        critical_columns=(
            "partner_id",
            "partner_name",
            "synthetic_record_flag",
        ),
        date_columns=("onboarding_date",),
        expected_row_count=5_000,
    ),
    "partner_pricing": DatasetSpec(
        file_name="partner_pricing_clean.csv",
        schema_key="partner_pricing",
        required_columns=(
            "partner_id",
            "pricing_plan_id",
            "recommended_pricing_plan_id",
            "negotiated_bps",
            "negotiated_per_txn_fee_usd",
            "exception_flag",
            "approval_status",
        ),
        key_columns=("assignment_id",),
        critical_columns=(
            "assignment_id",
            "partner_id",
            "pricing_plan_id",
        ),
        numeric_columns=(
            "negotiated_bps",
            "negotiated_per_txn_fee_usd",
            "monthly_minimum_fee_usd",
        ),
        nonnegative_columns=(
            "negotiated_bps",
            "negotiated_per_txn_fee_usd",
            "monthly_minimum_fee_usd",
        ),
        date_columns=(
            "effective_date",
            "expiration_date",
            "review_due_date",
        ),
        expected_row_count=5_000,
    ),
    "monthly_partner_metrics": DatasetSpec(
        file_name="partner_metrics_clean.csv",
        schema_key="monthly_partner_metrics",
        required_columns=(
            "partner_id",
            "month",
            "txn_count",
            "payment_volume_usd",
            "txn_growth_pct",
            "net_revenue_usd",
        ),
        key_columns=(
            "partner_id",
            "month",
        ),
        critical_columns=(
            "partner_id",
            "month",
        ),
        numeric_columns=(
            "txn_count",
            "payment_volume_usd",
            "avg_ticket_usd",
            "txn_growth_pct",
            "volume_growth_pct",
            "chargeback_rate",
            "auth_approval_rate",
            "active_merchants",
            "refunds_usd",
            "net_revenue_usd",
            "gross_margin_usd",
            "gross_margin_rate",
        ),
        nonnegative_columns=(
            "txn_count",
            "payment_volume_usd",
            "avg_ticket_usd",
            "chargeback_rate",
            "auth_approval_rate",
            "active_merchants",
            "refunds_usd",
        ),
        date_columns=("month",),
        expected_row_count=120_000,
    ),
    "partner_current_preview": DatasetSpec(
        file_name="partner_current_preview_1000.csv",
        schema_key=None,
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
        key_columns=("partner_id",),
        critical_columns=(
            "partner_id",
            "partner_name",
        ),
        numeric_columns=(
            "txn_growth_pct",
            "payment_volume_usd",
            "txn_count",
            "net_revenue_usd",
        ),
        nonnegative_columns=(
            "payment_volume_usd",
            "txn_count",
        ),
        expected_row_count=1_000,
    ),
}


EVIDENCE_FILES = (
    "phase3_validation_summary.csv",
)


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 hash of a file."""

    hasher = hashlib.sha256()

    with file_path.open("rb") as source_file:
        for chunk in iter(
            lambda: source_file.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_schema_metadata(
    schema_path: Path | str = SCHEMA_METADATA_PATH,
) -> dict:
    """Load the canonical PartnerLens schema metadata."""

    resolved_path = Path(schema_path).expanduser().resolve()

    if not resolved_path.exists():
        raise DataPreparationError(
            "The schema metadata file could not be found."
        )

    try:
        with resolved_path.open(
            "r",
            encoding="utf-8",
        ) as schema_file:
            metadata = json.load(schema_file)

    except (OSError, json.JSONDecodeError) as error:
        raise DataPreparationError(
            "The schema metadata file could not be read."
        ) from error

    if not isinstance(metadata.get("tables"), dict):
        raise DataPreparationError(
            "The schema metadata does not contain a valid "
            "'tables' section."
        )

    return metadata


def get_csv_header(file_path: Path) -> list[str]:
    """Read the original CSV header without pandas renaming columns."""

    try:
        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader)

    except (OSError, StopIteration, csv.Error) as error:
        raise DataPreparationError(
            f"The header of '{file_path.name}' could not be read."
        ) from error

    return [
        str(column).strip()
        for column in header
    ]


def read_processed_csv(file_path: Path) -> pd.DataFrame:
    """
    Read a processed CSV while preserving identifiers as text.

    All columns are initially read as strings because this module
    validates data rather than transforming it.
    """

    try:
        dataframe = pd.read_csv(
            file_path,
            dtype="string",
            keep_default_na=True,
            low_memory=False,
        )

    except Exception as error:
        raise DataPreparationError(
            f"Processed file '{file_path.name}' could not be read."
        ) from error

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    return dataframe


def is_blank(series: pd.Series) -> pd.Series:
    """Return a mask identifying missing or blank values."""

    return (
        series.isna()
        | series.astype("string").str.strip().eq("").fillna(False)
    )


def add_check(
    checks: list[dict],
    dataset: str,
    check_name: str,
    passed: bool,
    details: str,
    warning_only: bool = False,
) -> None:
    """Add one validation outcome to the report."""

    if passed:
        status = "PASS"
    elif warning_only:
        status = "WARN"
    else:
        status = "FAIL"

    checks.append(
        {
            "dataset": dataset,
            "check_name": check_name,
            "status": status,
            "details": details,
        }
    )


def get_required_columns(
    specification: DatasetSpec,
    schema_metadata: dict,
) -> set[str]:
    """
    Get required columns from schema metadata and local requirements.
    """

    required_columns = set(
        specification.required_columns
    )

    if specification.schema_key:
        schema_columns = schema_metadata["tables"].get(
            specification.schema_key
        )

        if not isinstance(schema_columns, list):
            raise DataPreparationError(
                "Schema metadata is missing the table definition "
                f"for '{specification.schema_key}'."
            )

        required_columns.update(schema_columns)

    return required_columns


def validate_numeric_columns(
    dataframe: pd.DataFrame,
    dataset_name: str,
    specification: DatasetSpec,
    checks: list[dict],
) -> None:
    """Validate numeric parsing and nonnegative constraints."""

    for column in specification.numeric_columns:
        if column not in dataframe.columns:
            continue

        original_values = dataframe[column]

        populated_mask = ~is_blank(original_values)

        converted_values = pd.to_numeric(
            original_values,
            errors="coerce",
        )

        invalid_numeric_mask = (
            populated_mask
            & converted_values.isna()
        )

        invalid_count = int(
            invalid_numeric_mask.sum()
        )

        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name=f"numeric_field:{column}",
            passed=invalid_count == 0,
            details=(
                f"{invalid_count} nonnumeric populated value(s) "
                f"found in '{column}'."
            ),
        )

        if (
            column in specification.nonnegative_columns
            and invalid_count == 0
        ):
            negative_count = int(
                (converted_values < 0).fillna(False).sum()
            )

            add_check(
                checks=checks,
                dataset=dataset_name,
                check_name=f"nonnegative_field:{column}",
                passed=negative_count == 0,
                details=(
                    f"{negative_count} negative value(s) found "
                    f"in '{column}'."
                ),
            )


def validate_date_columns(
    dataframe: pd.DataFrame,
    dataset_name: str,
    specification: DatasetSpec,
    checks: list[dict],
) -> None:
    """Validate populated date fields."""

    for column in specification.date_columns:
        if column not in dataframe.columns:
            continue

        populated_mask = ~is_blank(dataframe[column])

        parsed_dates = pd.to_datetime(
            dataframe[column],
            errors="coerce",
        )

        invalid_date_count = int(
            (
                populated_mask
                & parsed_dates.isna()
            ).sum()
        )

        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name=f"date_field:{column}",
            passed=invalid_date_count == 0,
            details=(
                f"{invalid_date_count} invalid populated date "
                f"value(s) found in '{column}'."
            ),
        )


def validate_state_codes(
    dataframe: pd.DataFrame,
    dataset_name: str,
    checks: list[dict],
) -> None:
    """Validate populated state codes as two uppercase letters."""

    if "state" not in dataframe.columns:
        return

    populated_mask = ~is_blank(dataframe["state"])

    valid_state_mask = (
        dataframe["state"]
        .astype("string")
        .str.strip()
        .str.match(r"^[A-Z]{2}$", na=False)
    )

    invalid_state_count = int(
        (
            populated_mask
            & ~valid_state_mask
        ).sum()
    )

    add_check(
        checks=checks,
        dataset=dataset_name,
        check_name="state_code_format",
        passed=invalid_state_count == 0,
        details=(
            f"{invalid_state_count} invalid populated state "
            "code(s) found. Expected two uppercase letters."
        ),
    )


def validate_synthetic_flag(
    dataframe: pd.DataFrame,
    dataset_name: str,
    checks: list[dict],
) -> None:
    """Validate the synthetic-record indicator when available."""

    column = "synthetic_record_flag"

    if column not in dataframe.columns:
        return

    normalized_values = (
        dataframe[column]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    accepted_values = {
        "1",
        "true",
        "yes",
        "y",
        "synthetic",
    }

    invalid_mask = (
        ~is_blank(dataframe[column])
        & ~normalized_values.isin(accepted_values)
    )

    missing_count = int(
        is_blank(dataframe[column]).sum()
    )

    invalid_count = int(
        invalid_mask.sum()
    )

    add_check(
        checks=checks,
        dataset=dataset_name,
        check_name="synthetic_record_flag",
        passed=(
            missing_count == 0
            and invalid_count == 0
        ),
        details=(
            f"{missing_count} missing and {invalid_count} "
            "unexpected synthetic flag value(s) found."
        ),
    )


def validate_one_dataset(
    dataset_name: str,
    specification: DatasetSpec,
    processed_dir: Path,
    schema_metadata: dict,
    checks: list[dict],
) -> tuple[pd.DataFrame | None, Path]:
    """Validate one processed PartnerLens dataset."""

    file_path = processed_dir / specification.file_name

    file_exists = (
        file_path.exists()
        and file_path.is_file()
    )

    add_check(
        checks=checks,
        dataset=dataset_name,
        check_name="file_exists",
        passed=file_exists,
        details=(
            f"Required file: {specification.file_name}"
        ),
    )

    if not file_exists:
        return None, file_path

    try:
        original_header = get_csv_header(file_path)

    except DataPreparationError as error:
        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name="header_readable",
            passed=False,
            details=str(error),
        )

        return None, file_path

    duplicate_header_columns = sorted(
        {
            column
            for column in original_header
            if original_header.count(column) > 1
        }
    )

    add_check(
        checks=checks,
        dataset=dataset_name,
        check_name="duplicate_column_names",
        passed=not duplicate_header_columns,
        details=(
            "No duplicate column names found."
            if not duplicate_header_columns
            else (
                "Duplicate columns: "
                + ", ".join(duplicate_header_columns)
            )
        ),
    )

    try:
        dataframe = read_processed_csv(file_path)

    except DataPreparationError as error:
        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name="file_readable",
            passed=False,
            details=str(error),
        )

        return None, file_path

    add_check(
        checks=checks,
        dataset=dataset_name,
        check_name="file_readable",
        passed=True,
        details=(
            f"Loaded {len(dataframe):,} rows and "
            f"{len(dataframe.columns):,} columns."
        ),
    )

    add_check(
        checks=checks,
        dataset=dataset_name,
        check_name="nonempty_dataset",
        passed=not dataframe.empty,
        details=(
            f"Dataset contains {len(dataframe):,} rows."
        ),
    )

    if specification.expected_row_count is not None:
        row_count_matches = (
            len(dataframe)
            == specification.expected_row_count
        )

        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name="expected_row_count",
            passed=row_count_matches,
            warning_only=True,
            details=(
                f"Expected approximately "
                f"{specification.expected_row_count:,} rows; "
                f"found {len(dataframe):,}."
            ),
        )

    required_columns = get_required_columns(
        specification=specification,
        schema_metadata=schema_metadata,
    )

    missing_columns = sorted(
        required_columns
        - set(dataframe.columns)
    )

    add_check(
        checks=checks,
        dataset=dataset_name,
        check_name="required_columns",
        passed=not missing_columns,
        details=(
            "All required columns are present."
            if not missing_columns
            else (
                "Missing required columns: "
                + ", ".join(missing_columns)
            )
        ),
    )

    # Continue only with checks whose columns are available.
    available_critical_columns = [
        column
        for column in specification.critical_columns
        if column in dataframe.columns
    ]

    for column in available_critical_columns:
        missing_count = int(
            is_blank(dataframe[column]).sum()
        )

        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name=f"critical_field:{column}",
            passed=missing_count == 0,
            details=(
                f"{missing_count} missing or blank value(s) "
                f"found in '{column}'."
            ),
        )

    if all(
        column in dataframe.columns
        for column in specification.key_columns
    ):
        duplicate_mask = dataframe.duplicated(
            subset=list(specification.key_columns),
            keep=False,
        )

        duplicate_count = int(
            duplicate_mask.sum()
        )

        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name="duplicate_business_key",
            passed=duplicate_count == 0,
            details=(
                f"{duplicate_count} row(s) have duplicate values "
                f"for key {specification.key_columns}."
            ),
        )

    validate_numeric_columns(
        dataframe=dataframe,
        dataset_name=dataset_name,
        specification=specification,
        checks=checks,
    )

    validate_date_columns(
        dataframe=dataframe,
        dataset_name=dataset_name,
        specification=specification,
        checks=checks,
    )

    validate_state_codes(
        dataframe=dataframe,
        dataset_name=dataset_name,
        checks=checks,
    )

    validate_synthetic_flag(
        dataframe=dataframe,
        dataset_name=dataset_name,
        checks=checks,
    )

    return dataframe, file_path


def validate_evidence_files(
    processed_dir: Path,
    checks: list[dict],
) -> dict[str, tuple[pd.DataFrame | None, Path]]:
    """Validate Phase 3 evidence files retained for Phase 8."""

    evidence_data: dict[
        str,
        tuple[pd.DataFrame | None, Path],
    ] = {}

    for file_name in EVIDENCE_FILES:
        file_path = processed_dir / file_name
        dataset_name = Path(file_name).stem

        exists = (
            file_path.exists()
            and file_path.is_file()
        )

        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name="evidence_file_exists",
            passed=exists,
            details=f"Evidence file: {file_name}",
        )

        if not exists:
            evidence_data[dataset_name] = (
                None,
                file_path,
            )
            continue

        try:
            dataframe = read_processed_csv(file_path)

        except DataPreparationError as error:
            add_check(
                checks=checks,
                dataset=dataset_name,
                check_name="evidence_file_readable",
                passed=False,
                details=str(error),
            )

            evidence_data[dataset_name] = (
                None,
                file_path,
            )
            continue

        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name="evidence_file_readable",
            passed=not dataframe.empty,
            details=(
                f"Loaded {len(dataframe):,} validation "
                "summary row(s)."
            ),
        )

        evidence_data[dataset_name] = (
            dataframe,
            file_path,
        )

    return evidence_data


def validate_partner_relationships(
    dataframes: dict[str, pd.DataFrame],
    checks: list[dict],
) -> None:
    """Validate partner_id relationships across processed datasets."""

    partners = dataframes.get("partners")

    if (
        partners is None
        or "partner_id" not in partners.columns
    ):
        add_check(
            checks=checks,
            dataset="cross_table",
            check_name="partner_relationships",
            passed=False,
            details=(
                "Partner relationships could not be validated "
                "because the master partner identifiers are missing."
            ),
        )
        return

    master_partner_ids = set(
        partners["partner_id"]
        .dropna()
        .astype("string")
        .str.strip()
    )

    child_dataset_names = (
        "partner_pricing",
        "monthly_partner_metrics",
        "partner_current_preview",
    )

    for dataset_name in child_dataset_names:
        child_dataframe = dataframes.get(dataset_name)

        if (
            child_dataframe is None
            or "partner_id" not in child_dataframe.columns
        ):
            continue

        child_partner_ids = set(
            child_dataframe["partner_id"]
            .dropna()
            .astype("string")
            .str.strip()
        )

        orphan_ids = sorted(
            child_partner_ids
            - master_partner_ids
        )

        add_check(
            checks=checks,
            dataset=dataset_name,
            check_name="partner_id_referential_integrity",
            passed=not orphan_ids,
            details=(
                "All partner IDs exist in the master partner file."
                if not orphan_ids
                else (
                    f"{len(orphan_ids)} orphan partner ID(s) "
                    f"found. Examples: {orphan_ids[:5]}"
                )
            ),
        )


def validate_preview_consistency(
    dataframes: dict[str, pd.DataFrame],
    checks: list[dict],
) -> None:
    """
    Confirm that preview master fields match partner master fields.

    This protects answer citations from being generated from inconsistent
    joined preview data.
    """

    partners = dataframes.get("partners")
    preview = dataframes.get("partner_current_preview")

    if partners is None or preview is None:
        return

    comparison_columns = [
        column
        for column in (
            "partner_name",
            "industry_vertical",
            "state",
        )
        if (
            column in partners.columns
            and column in preview.columns
        )
    ]

    if not comparison_columns:
        return

    master_subset = partners[
        ["partner_id", *comparison_columns]
    ].copy()

    preview_subset = preview[
        ["partner_id", *comparison_columns]
    ].copy()

    merged = preview_subset.merge(
        master_subset,
        on="partner_id",
        how="left",
        suffixes=("_preview", "_master"),
    )

    for column in comparison_columns:
        preview_values = (
            merged[f"{column}_preview"]
            .astype("string")
            .str.strip()
            .fillna("")
        )

        master_values = (
            merged[f"{column}_master"]
            .astype("string")
            .str.strip()
            .fillna("")
        )

        mismatch_count = int(
            (preview_values != master_values).sum()
        )

        add_check(
            checks=checks,
            dataset="partner_current_preview",
            check_name=f"master_consistency:{column}",
            passed=mismatch_count == 0,
            details=(
                f"{mismatch_count} preview-to-master mismatch(es) "
                f"found for '{column}'."
            ),
        )


def create_manifest_record(
    dataset_name: str,
    file_path: Path,
    dataframe: pd.DataFrame | None,
) -> dict:
    """Create one source-lineage manifest record."""

    file_exists = (
        file_path.exists()
        and file_path.is_file()
    )

    return {
        "dataset": dataset_name,
        "source_file": file_path.name,
        "file_exists": file_exists,
        "file_size_bytes": (
            file_path.stat().st_size
            if file_exists
            else None
        ),
        "sha256": (
            calculate_sha256(file_path)
            if file_exists
            else None
        ),
        "row_count": (
            len(dataframe)
            if dataframe is not None
            else None
        ),
        "column_count": (
            len(dataframe.columns)
            if dataframe is not None
            else None
        ),
        "columns": (
            ",".join(dataframe.columns.astype(str))
            if dataframe is not None
            else None
        ),
        "last_modified_utc": (
            datetime.fromtimestamp(
                file_path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
            if file_exists
            else None
        ),
    }


def validate_processed_data(
    processed_dir: Path | str = PROCESSED_DIR,
    schema_metadata_path: Path | str = SCHEMA_METADATA_PATH,
    validation_report_path: Path | str = VALIDATION_REPORT_PATH,
    manifest_path: Path | str = DATA_MANIFEST_PATH,
    fail_on_error: bool = True,
) -> DataPreparationResult:
    """
    Run the complete Phase 8 processed-data validation workflow.

    Reports are written even when validation fails, so the failure
    evidence can be reviewed.

    Args:
        processed_dir: Directory containing processed CSV files.
        schema_metadata_path: Canonical schema metadata JSON file.
        validation_report_path: Output CSV for validation checks.
        manifest_path: Output CSV for file lineage.
        fail_on_error: Raise DataPreparationError when a FAIL occurs.

    Returns:
        DataPreparationResult with validation counts and report paths.
    """

    resolved_processed_dir = Path(
        processed_dir
    ).expanduser().resolve()

    resolved_validation_report_path = Path(
        validation_report_path
    ).expanduser().resolve()

    resolved_manifest_path = Path(
        manifest_path
    ).expanduser().resolve()

    if not resolved_processed_dir.exists():
        raise DataPreparationError(
            "The processed-data directory could not be found."
        )

    schema_metadata = load_schema_metadata(
        schema_metadata_path
    )

    checks: list[dict] = []
    loaded_dataframes: dict[str, pd.DataFrame] = {}
    manifest_records: list[dict] = []

    for dataset_name, specification in DATASET_SPECS.items():
        dataframe, file_path = validate_one_dataset(
            dataset_name=dataset_name,
            specification=specification,
            processed_dir=resolved_processed_dir,
            schema_metadata=schema_metadata,
            checks=checks,
        )

        if dataframe is not None:
            loaded_dataframes[dataset_name] = dataframe

        manifest_records.append(
            create_manifest_record(
                dataset_name=dataset_name,
                file_path=file_path,
                dataframe=dataframe,
            )
        )

    evidence_data = validate_evidence_files(
        processed_dir=resolved_processed_dir,
        checks=checks,
    )

    for dataset_name, (
        dataframe,
        file_path,
    ) in evidence_data.items():
        manifest_records.append(
            create_manifest_record(
                dataset_name=dataset_name,
                file_path=file_path,
                dataframe=dataframe,
            )
        )

    validate_partner_relationships(
        dataframes=loaded_dataframes,
        checks=checks,
    )

    validate_preview_consistency(
        dataframes=loaded_dataframes,
        checks=checks,
    )

    generated_at_utc = datetime.now(
        timezone.utc
    ).isoformat()

    validation_report = pd.DataFrame(checks)

    validation_report.insert(
        0,
        "generated_at_utc",
        generated_at_utc,
    )

    manifest_dataframe = pd.DataFrame(
        manifest_records
    )

    manifest_dataframe.insert(
        0,
        "generated_at_utc",
        generated_at_utc,
    )

    resolved_validation_report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    resolved_manifest_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    validation_report.to_csv(
        resolved_validation_report_path,
        index=False,
    )

    manifest_dataframe.to_csv(
        resolved_manifest_path,
        index=False,
    )

    passed_checks = int(
        (validation_report["status"] == "PASS").sum()
    )

    warning_checks = int(
        (validation_report["status"] == "WARN").sum()
    )

    failed_checks = int(
        (validation_report["status"] == "FAIL").sum()
    )

    result = DataPreparationResult(
        passed=failed_checks == 0,
        passed_checks=passed_checks,
        warning_checks=warning_checks,
        failed_checks=failed_checks,
        validated_files=len(manifest_dataframe),
        validation_report_path=(
            resolved_validation_report_path
        ),
        manifest_path=resolved_manifest_path,
    )

    if fail_on_error and failed_checks:
        raise DataPreparationError(
            f"Processed-data validation failed with "
            f"{failed_checks} failed check(s). Review "
            f"'{resolved_validation_report_path.name}'."
        )

    return result


def print_validation_summary(
    result: DataPreparationResult,
) -> None:
    """Print a concise Phase 8 validation summary."""

    overall_status = (
        "PASSED"
        if result.passed
        else "FAILED"
    )

    print()
    print("PartnerLens Phase 8 Data Validation")
    print("-----------------------------------")
    print(f"Overall status: {overall_status}")
    print(f"Files inspected: {result.validated_files}")
    print(f"Passed checks: {result.passed_checks}")
    print(f"Warnings: {result.warning_checks}")
    print(f"Failed checks: {result.failed_checks}")
    print(
        "Validation report: "
        f"{result.validation_report_path}"
    )
    print(
        f"Data manifest: {result.manifest_path}"
    )


def main() -> None:
    """Run the Phase 8 data-validation workflow."""

    try:
        result = validate_processed_data(
            fail_on_error=False
        )

        print_validation_summary(result)

        if not result.passed:
            raise SystemExit(1)

    except DataPreparationError as error:
        print(f"Data validation failed: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
