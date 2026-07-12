"""
Grounded answer-generation module for PartnerLens Copilot.

Phase 8 answer-generation controls:

- Uses only validated SQL result records.
- Includes record-level citations for every displayed record.
- Identifies the validated source tables.
- Formats business values consistently.
- Limits the number of displayed records.
- Handles empty query results without adding unsupported claims.
- Rejects malformed answer-generation inputs.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from numbers import Integral, Real
import math
import re


DEFAULT_MAX_RECORDS = 5
MAX_DISPLAY_RECORDS = 10

RECORD_ID_FIELDS = {
    "partner_id",
    "id",
}

PARTNER_NAME_FIELDS = {
    "partner_name",
    "name",
}

FIELD_LABELS = {
    "partner_id": "Partner ID",
    "partner_name": "Partner Name",
    "partner_type": "Partner Type",
    "industry_vertical": "Industry Vertical",
    "partner_size": "Partner Size",
    "partner_status": "Partner Status",
    "state": "State",
    "region": "Region",
    "risk_tier": "Risk Tier",
    "kyc_status": "KYC Status",
    "pci_level": "PCI Level",
    "txn_growth_pct": "Transaction Growth",
    "payment_volume_usd": "Payment Volume",
    "txn_count": "Transaction Count",
    "net_revenue_usd": "Net Revenue",
    "pricing_plan_id": "Pricing Plan ID",
    "recommended_pricing_plan_id": (
        "Recommended Pricing Plan ID"
    ),
    "negotiated_bps": "Negotiated Rate",
    "negotiated_per_txn_fee_usd": (
        "Negotiated Per-Transaction Fee"
    ),
    "monthly_minimum_fee_usd": "Monthly Minimum Fee",
    "exception_flag": "Pricing Exception",
    "approval_status": "Approval Status",
}


class AnswerGenerationError(ValueError):
    """Raised when a grounded answer cannot be generated safely."""


def escape_markdown(value: object) -> str:
    """
    Escape Markdown control characters in database values.

    This prevents partner names or other returned text from changing
    the intended answer structure.
    """

    text = str(value)

    for character in (
        "\\",
        "`",
        "*",
        "_",
        "{",
        "}",
        "[",
        "]",
        "<",
        ">",
    ):
        text = text.replace(
            character,
            f"\\{character}",
        )

    return text


def is_missing_value(value: object) -> bool:
    """Check for None, NaN, pandas NA, and pandas NaT values."""

    if value is None:
        return True

    if type(value).__name__ in {
        "NAType",
        "NaTType",
    }:
        return True

    if isinstance(value, Decimal):
        return value.is_nan()

    if (
        isinstance(value, Real)
        and not isinstance(value, Integral)
    ):
        try:
            return math.isnan(float(value))
        except (TypeError, ValueError):
            return False

    return False


def convert_to_number(
    value: object,
) -> float | None:
    """Convert a database value to a number when possible."""

    if is_missing_value(value):
        return None

    if isinstance(value, bool):
        return None

    if isinstance(
        value,
        (Integral, Real, Decimal),
    ):
        return float(value)

    try:
        normalized_value = (
            str(value)
            .strip()
            .replace(",", "")
            .replace("$", "")
            .replace("%", "")
        )

        return float(normalized_value)

    except (TypeError, ValueError):
        return None


def format_number(
    numeric_value: float,
    decimal_places: int = 2,
) -> str:
    """Format a number with thousands separators."""

    if numeric_value.is_integer():
        return f"{int(numeric_value):,}"

    return f"{numeric_value:,.{decimal_places}f}"


def format_field_name(
    field_name: str,
) -> str:
    """Convert a database column name into a business label."""

    normalized_name = (
        str(field_name)
        .strip()
        .lower()
    )

    if normalized_name in FIELD_LABELS:
        return FIELD_LABELS[normalized_name]

    acronym_labels = {
        "id": "ID",
        "usd": "USD",
        "pct": "Percent",
        "bps": "BPS",
        "kyc": "KYC",
        "pci": "PCI",
        "txn": "Transaction",
    }

    words = normalized_name.split("_")

    formatted_words = [
        acronym_labels.get(
            word,
            word.title(),
        )
        for word in words
    ]

    return " ".join(formatted_words)


def format_boolean_value(
    value: object,
) -> str | None:
    """Convert common boolean representations into Yes or No."""

    if isinstance(value, bool):
        return "Yes" if value else "No"

    normalized_value = str(value).strip().lower()

    true_values = {
        "1",
        "true",
        "yes",
        "y",
    }

    false_values = {
        "0",
        "false",
        "no",
        "n",
    }

    if normalized_value in true_values:
        return "Yes"

    if normalized_value in false_values:
        return "No"

    return None


def format_value(
    field_name: str,
    value: object,
) -> str:
    """
    Format a returned database value according to its business type.

    Examples:
        payment_volume_usd -> $1,250,000.00
        txn_growth_pct -> 24.50%
        negotiated_bps -> 35.00 bps
        txn_count -> 25,000
        exception_flag -> Yes
    """

    if is_missing_value(value):
        return "Not available"

    normalized_field_name = (
        str(field_name)
        .strip()
        .lower()
    )

    if normalized_field_name == "exception_flag":
        boolean_value = format_boolean_value(value)

        if boolean_value is not None:
            return boolean_value

    if isinstance(value, bool):
        return "Yes" if value else "No"

    numeric_value = convert_to_number(value)

    if (
        normalized_field_name.endswith("_usd")
        and numeric_value is not None
    ):
        return f"${numeric_value:,.2f}"

    if (
        normalized_field_name.endswith("_pct")
        and numeric_value is not None
    ):
        return f"{numeric_value:,.2f}%"

    if (
        normalized_field_name.endswith("_bps")
        and numeric_value is not None
    ):
        return f"{numeric_value:,.2f} bps"

    if (
        (
            normalized_field_name.endswith("_count")
            or normalized_field_name
            in {
                "active_merchants",
            }
        )
        and numeric_value is not None
    ):
        return format_number(
            numeric_value=numeric_value,
            decimal_places=0,
        )

    if isinstance(value, Integral):
        return f"{int(value):,}"

    if isinstance(value, Real):
        return format_number(
            numeric_value=float(value),
        )

    return escape_markdown(value)


def normalize_source_tables(
    source_tables: Sequence[str],
) -> tuple[str, ...]:
    """
    Normalize validated source-table names.

    This function does not decide whether a table is approved. Table
    approval belongs to the centralized SQL validator.
    """

    if isinstance(source_tables, str):
        raise AnswerGenerationError(
            "Source tables must be provided as a sequence, "
            "not as one text value."
        )

    normalized_tables: list[str] = []
    seen_tables: set[str] = set()

    for table_name in source_tables:
        normalized_name = (
            str(table_name)
            .strip()
            .lower()
        )

        if not normalized_name:
            continue

        if not re.fullmatch(
            r"[a-z_][a-z0-9_]*",
            normalized_name,
        ):
            raise AnswerGenerationError(
                "An invalid source-table name was provided."
            )

        if normalized_name not in seen_tables:
            seen_tables.add(normalized_name)
            normalized_tables.append(
                normalized_name
            )

    if not normalized_tables:
        raise AnswerGenerationError(
            "At least one validated source table is required."
        )

    return tuple(normalized_tables)


def get_record_value(
    record: Mapping,
    accepted_fields: set[str],
) -> object | None:
    """Find a record value using case-insensitive field matching."""

    for field_name, value in record.items():
        normalized_field_name = (
            str(field_name)
            .strip()
            .lower()
        )

        if normalized_field_name in accepted_fields:
            if not is_missing_value(value):
                if str(value).strip():
                    return value

    return None


def get_record_identifier(
    record: Mapping,
    record_number: int,
) -> str:
    """
    Get the identifier used in the record citation.

    When the query did not return an identifier, a deterministic
    result-N identifier is used.
    """

    identifier = get_record_value(
        record=record,
        accepted_fields=RECORD_ID_FIELDS,
    )

    if identifier is None:
        return f"result-{record_number}"

    normalized_identifier = str(identifier).strip()

    if not re.fullmatch(
        r"[A-Za-z0-9_.:-]+",
        normalized_identifier,
    ):
        return f"result-{record_number}"

    return normalized_identifier


def get_partner_name(
    record: Mapping,
    record_number: int,
) -> str:
    """Get a readable partner name for a result heading."""

    partner_name = get_record_value(
        record=record,
        accepted_fields=PARTNER_NAME_FIELDS,
    )

    if partner_name is None:
        return f"Partner {record_number}"

    return escape_markdown(partner_name)


def should_display_field(
    field_name: object,
) -> bool:
    """Determine whether a returned field belongs in the answer body."""

    normalized_field_name = (
        str(field_name)
        .strip()
        .lower()
    )

    if normalized_field_name in (
        RECORD_ID_FIELDS
        | PARTNER_NAME_FIELDS
    ):
        return False

    # Hide application-internal fields if they are ever returned.
    if normalized_field_name.startswith("_"):
        return False

    return True


def validate_answer_inputs(
    user_question: str,
    result_records: list[dict],
    source_tables: Sequence[str],
    max_records: int,
) -> tuple[tuple[str, ...], list[Mapping]]:
    """Validate all inputs before generating an answer."""

    if (
        not isinstance(user_question, str)
        or not user_question.strip()
    ):
        raise AnswerGenerationError(
            "A nonempty user question is required."
        )

    if not isinstance(result_records, list):
        raise AnswerGenerationError(
            "Query results must be provided as a list of records."
        )

    invalid_record_count = sum(
        1
        for record in result_records
        if not isinstance(record, Mapping)
    )

    if invalid_record_count:
        raise AnswerGenerationError(
            "Every query result must be a record mapping."
        )

    if (
        isinstance(max_records, bool)
        or not isinstance(max_records, int)
    ):
        raise AnswerGenerationError(
            "max_records must be an integer."
        )

    if not 1 <= max_records <= MAX_DISPLAY_RECORDS:
        raise AnswerGenerationError(
            f"max_records must be between 1 and "
            f"{MAX_DISPLAY_RECORDS}."
        )

    normalized_source_tables = normalize_source_tables(
        source_tables
    )

    return (
        normalized_source_tables,
        result_records,
    )


def format_source_tables(
    source_tables: tuple[str, ...],
) -> str:
    """Format validated source-table names for Markdown output."""

    return ", ".join(
        f"`{table_name}`"
        for table_name in source_tables
    )


def generate_answer(
    user_question: str,
    result_records: list[dict],
    source_tables: Sequence[str],
    max_records: int = DEFAULT_MAX_RECORDS,
) -> str:
    """
    Generate a grounded answer from validated SQL query results.

    Every displayed record receives a record-level citation. The answer
    also identifies all validated source tables used by the query.
    """

    (
        normalized_source_tables,
        validated_records,
    ) = validate_answer_inputs(
        user_question=user_question,
        result_records=result_records,
        source_tables=source_tables,
        max_records=max_records,
    )

    source_table_text = format_source_tables(
        normalized_source_tables
    )

    if not validated_records:
        return "\n".join(
            [
                (
                    "No matching partner records were found "
                    "for this question."
                ),
                "",
                "### Source and grounding",
                (
                    f"- **Source tables:** "
                    f"{source_table_text}"
                ),
                (
                    "- **Grounding:** This answer was generated "
                    "exclusively from the validated SQL query results "
                    "in the PartnerLens SQLite database."
                ),
                (
                    "- **Result status:** The validated query returned "
                    "zero matching records. No unsupported assumptions "
                    "were added."
                ),
            ]
        )

    total_records = len(validated_records)

    displayed_records = validated_records[
        :max_records
    ]

    answer_lines = [
        (
            "Based on the validated SQL query results, "
            f"I found {total_records:,} matching partner "
            "record(s)."
        ),
        "",
    ]

    for record_number, record in enumerate(
        displayed_records,
        start=1,
    ):
        record_identifier = get_record_identifier(
            record=record,
            record_number=record_number,
        )

        partner_name = get_partner_name(
            record=record,
            record_number=record_number,
        )

        answer_lines.append(
            f"### {record_number}. {partner_name}"
        )

        displayed_field_count = 0

        for field_name, value in record.items():
            if not should_display_field(field_name):
                continue

            answer_lines.append(
                f"- **{format_field_name(field_name)}:** "
                f"{format_value(field_name, value)}"
            )

            displayed_field_count += 1

        if displayed_field_count == 0:
            answer_lines.append(
                "- No additional business fields were returned."
            )

        answer_lines.append(
            "- **Citation:** SQLite partner record "
            f"`{record_identifier}`; fields returned by the "
            "validated SQL query."
        )

        answer_lines.append("")

    if total_records > len(displayed_records):
        answer_lines.extend(
            [
                (
                    f"Only the first "
                    f"{len(displayed_records):,} of "
                    f"{total_records:,} matching records "
                    "are displayed."
                ),
                "",
            ]
        )

    answer_lines.extend(
        [
            "### Source and grounding",
            (
                f"- **Source tables:** "
                f"{source_table_text}"
            ),
            (
                "- **Grounding:** This answer was generated "
                "exclusively from the validated SQL query results "
                "in the PartnerLens SQLite database."
            ),
            (
                "- **Evidence scope:** Only fields returned by the "
                "validated query were used. No external information "
                "or unsupported assumptions were added."
            ),
        ]
    )

    return "\n".join(answer_lines)
