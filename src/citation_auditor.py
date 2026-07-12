"""
Record-level citation audit module for PartnerLens Copilot.

Phase 8 citation controls:

- Confirms that the answer contains grounding language.
- Extracts cited PartnerLens record identifiers.
- Compares cited record IDs with the displayed SQL results.
- Detects missing and fabricated record citations.
- Confirms that validated source tables are named in the answer.
- Handles successful, empty-result, and malformed-answer cases.
- Produces a machine-readable audit result for Streamlit and evaluation.

This auditor checks structural citation support. It does not claim to
perform full natural-language entailment or semantic fact verification.
"""

from collections.abc import Mapping
import re


try:
    # Used when imported as part of the src package.
    from .sql_validator import ALLOWED_TABLES
except ImportError:
    # Used when Streamlit runs src/app.py directly.
    from sql_validator import ALLOWED_TABLES


AUDIT_VERSION = "phase8-v1"

RECORD_ID_FIELDS = (
    "partner_id",
    "Partner_ID",
    "id",
)

CITATION_PATTERN = re.compile(
    r"""
    SQLite
    \s+partner
    \s+record
    \s+
    [`'"]?
    ([A-Za-z0-9_.:-]+)
    [`'"]?
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

GROUNDING_PATTERN = re.compile(
    r"\bvalidated\s+(?:SQL\s+)?query\s+results?\b",
    flags=re.IGNORECASE,
)

NO_RESULT_PATTERNS = (
    re.compile(
        r"\bno matching partner records? (?:were|was) found\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bno matching records? (?:were|was) found\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bthe query returned no records?\b",
        flags=re.IGNORECASE,
    ),
)


def normalize_identifier(value) -> str:
    """Convert a record identifier into normalized text."""

    if value is None:
        return ""

    return str(value).strip()


def canonical_identifier(value: str) -> str:
    """Create a case-insensitive identifier for comparison."""

    return normalize_identifier(value).casefold()


def unique_identifiers(
    identifiers: list[str],
) -> tuple[str, ...]:
    """Remove duplicate identifiers while preserving their order."""

    unique_values: list[str] = []
    seen_values: set[str] = set()

    for identifier in identifiers:
        normalized_identifier = normalize_identifier(
            identifier
        )

        if not normalized_identifier:
            continue

        canonical_value = canonical_identifier(
            normalized_identifier
        )

        if canonical_value not in seen_values:
            seen_values.add(canonical_value)
            unique_values.append(normalized_identifier)

    return tuple(unique_values)


def get_record_identifier(
    record: Mapping,
    record_number: int,
) -> str:
    """
    Get the auditable identifier used by the answer generator.

    The fallback identifier matches the answer generator's
    result-1, result-2, and similar behavior.
    """

    for field_name in RECORD_ID_FIELDS:
        value = record.get(field_name)

        normalized_value = normalize_identifier(value)

        if normalized_value:
            return normalized_value

    return f"result-{record_number}"


def get_expected_record_ids(
    result_records: list[dict],
    max_records: int,
) -> tuple[str, ...]:
    """
    Get the IDs of the records expected to appear in the answer.

    Only records displayed by the answer generator are audited.
    """

    expected_ids = []

    for record_number, record in enumerate(
        result_records[:max_records],
        start=1,
    ):
        expected_ids.append(
            get_record_identifier(
                record=record,
                record_number=record_number,
            )
        )

    return unique_identifiers(expected_ids)


def extract_cited_record_ids(
    answer: str,
) -> tuple[str, ...]:
    """Extract record IDs from PartnerLens citation statements."""

    matches = CITATION_PATTERN.findall(answer)

    return unique_identifiers(matches)


def normalize_source_tables(
    source_tables: list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    """Normalize source-table metadata."""

    if source_tables is None:
        return ()

    normalized_tables = []

    for table_name in source_tables:
        normalized_name = str(table_name).strip().lower()

        if normalized_name:
            normalized_tables.append(normalized_name)

    return unique_identifiers(normalized_tables)


def source_table_is_mentioned(
    answer: str,
    table_name: str,
) -> bool:
    """Check for an exact table name in the generated answer."""

    table_pattern = re.compile(
        rf"(?<![A-Za-z0-9_])"
        rf"{re.escape(table_name)}"
        rf"(?![A-Za-z0-9_])",
        flags=re.IGNORECASE,
    )

    return table_pattern.search(answer) is not None


def find_mentioned_source_tables(
    answer: str,
    expected_source_tables: tuple[str, ...],
) -> tuple[str, ...]:
    """Return expected source tables explicitly named in the answer."""

    return tuple(
        table_name
        for table_name in expected_source_tables
        if source_table_is_mentioned(
            answer=answer,
            table_name=table_name,
        )
    )


def has_no_result_message(answer: str) -> bool:
    """Check whether an empty result is explained accurately."""

    return any(
        pattern.search(answer)
        for pattern in NO_RESULT_PATTERNS
    )


def compare_identifiers(
    expected_identifiers: tuple[str, ...],
    actual_identifiers: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """
    Compare expected and actual identifiers.

    Returns:
        missing identifiers, unexpected identifiers
    """

    expected_map = {
        canonical_identifier(identifier): identifier
        for identifier in expected_identifiers
    }

    actual_map = {
        canonical_identifier(identifier): identifier
        for identifier in actual_identifiers
    }

    missing_identifiers = tuple(
        original_identifier
        for canonical_value, original_identifier
        in expected_map.items()
        if canonical_value not in actual_map
    )

    unexpected_identifiers = tuple(
        original_identifier
        for canonical_value, original_identifier
        in actual_map.items()
        if canonical_value not in expected_map
    )

    return (
        missing_identifiers,
        unexpected_identifiers,
    )


def audit_citations(
    answer: str,
    result_records: list[dict] | None,
    source_tables: list[str] | tuple[str, ...] | None,
    max_records: int = 5,
) -> dict:
    """
    Audit a PartnerLens answer against its SQL evidence.

    Args:
        answer:
            Business-friendly answer generated by PartnerLens.
        result_records:
            Records returned by the validated SQL query.
        source_tables:
            Tables approved by SQL validation and query execution.
        max_records:
            Maximum number of records displayed by the answer generator.

    Returns:
        Dictionary suitable for Streamlit JSON output, evaluation
        reports, and audit logging.
    """

    if max_records < 1:
        raise ValueError(
            "max_records must be at least 1."
        )

    answer_is_valid_text = (
        isinstance(answer, str)
        and bool(answer.strip())
    )

    safe_answer = (
        answer
        if isinstance(answer, str)
        else ""
    )

    result_metadata_available = (
        isinstance(result_records, list)
        and all(
            isinstance(record, Mapping)
            for record in result_records
        )
    )

    safe_result_records = (
        result_records
        if result_metadata_available
        else []
    )

    expected_source_tables = normalize_source_tables(
        source_tables
    )

    source_metadata_available = (
        source_tables is not None
        and bool(expected_source_tables)
    )

    unapproved_source_tables = tuple(
        table_name
        for table_name in expected_source_tables
        if table_name not in ALLOWED_TABLES
    )

    approved_source_metadata = (
        source_metadata_available
        and not unapproved_source_tables
    )

    expected_record_ids = get_expected_record_ids(
        result_records=safe_result_records,
        max_records=max_records,
    )

    cited_record_ids = extract_cited_record_ids(
        safe_answer
    )

    (
        missing_record_ids,
        unexpected_record_ids,
    ) = compare_identifiers(
        expected_identifiers=expected_record_ids,
        actual_identifiers=cited_record_ids,
    )

    mentioned_source_tables = (
        find_mentioned_source_tables(
            answer=safe_answer,
            expected_source_tables=expected_source_tables,
        )
    )

    missing_source_tables = tuple(
        table_name
        for table_name in expected_source_tables
        if table_name not in mentioned_source_tables
    )

    grounding_statement_present = (
        GROUNDING_PATTERN.search(safe_answer)
        is not None
    )

    checks: dict[str, bool] = {
        "answer_present": answer_is_valid_text,
        "result_metadata_available": (
            result_metadata_available
        ),
        "source_metadata_available": (
            source_metadata_available
        ),
        "source_tables_approved": (
            approved_source_metadata
        ),
        "grounding_statement_present": (
            grounding_statement_present
        ),
        "source_table_coverage_complete": (
            approved_source_metadata
            and not missing_source_tables
        ),
    }

    no_result_message_present: bool | None = None

    if result_metadata_available and expected_record_ids:
        checks["record_citation_present"] = bool(
            cited_record_ids
        )

        checks["record_citation_coverage_complete"] = (
            not missing_record_ids
        )

        checks["no_unexpected_record_citations"] = (
            not unexpected_record_ids
        )

    elif result_metadata_available:
        no_result_message_present = has_no_result_message(
            safe_answer
        )

        checks["no_result_message_present"] = (
            no_result_message_present
        )

        checks["no_unexpected_record_citations"] = (
            not cited_record_ids
        )

    passed_check_count = sum(
        1
        for passed in checks.values()
        if passed
    )

    audit_score = round(
        100 * passed_check_count / len(checks),
        1,
    )

    reason_codes: list[str] = []

    if not answer_is_valid_text:
        reason_codes.append("empty_or_invalid_answer")

    if not result_metadata_available:
        reason_codes.append(
            "result_metadata_missing_or_invalid"
        )

    if not source_metadata_available:
        reason_codes.append(
            "source_table_metadata_missing"
        )

    if unapproved_source_tables:
        reason_codes.append(
            "unapproved_source_table"
        )

    if not grounding_statement_present:
        reason_codes.append(
            "grounding_statement_missing"
        )

    if missing_source_tables:
        reason_codes.append(
            "source_table_citation_incomplete"
        )

    if (
        result_metadata_available
        and expected_record_ids
        and not cited_record_ids
    ):
        reason_codes.append(
            "record_citations_missing"
        )

    if missing_record_ids:
        reason_codes.append(
            "record_citation_coverage_incomplete"
        )

    if unexpected_record_ids:
        reason_codes.append(
            "unexpected_or_fabricated_record_citation"
        )

    if (
        result_metadata_available
        and not expected_record_ids
        and not no_result_message_present
    ):
        reason_codes.append(
            "no_result_message_missing"
        )

    citation_audit_passed = all(
        checks.values()
    )

    return {
        "audit_version": AUDIT_VERSION,
        "citation_audit_passed": (
            citation_audit_passed
        ),
        "audit_score_pct": audit_score,
        "reason_codes": reason_codes,
        "checks": checks,
        "expected_record_ids": list(
            expected_record_ids
        ),
        "cited_record_ids": list(
            cited_record_ids
        ),
        "missing_record_ids": list(
            missing_record_ids
        ),
        "unexpected_record_ids": list(
            unexpected_record_ids
        ),
        "expected_source_tables": list(
            expected_source_tables
        ),
        "mentioned_source_tables": list(
            mentioned_source_tables
        ),
        "missing_source_tables": list(
            missing_source_tables
        ),
        "unapproved_source_tables": list(
            unapproved_source_tables
        ),
        "no_result_message_present": (
            no_result_message_present
        ),
    }
