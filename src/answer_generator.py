"""
Answer generation module for PartnerLens Copilot.

This module converts validated SQL query results into a concise,
business-friendly response with record-level source citations.
"""


def format_field_name(field_name: str) -> str:
    """
    Convert a database column name into a readable label.

    Example:
        partner_name -> Partner Name
        transaction_growth_pct -> Transaction Growth Pct
    """
    return field_name.replace("_", " ").title()


def format_value(value) -> str:
    """Convert database values into readable text."""
    if value is None:
        return "Not available"

    if isinstance(value, float):
        return f"{value:,.2f}"

    return str(value)


def generate_answer(
    user_question: str,
    result_records: list[dict],
    max_records: int = 5
) -> str:
    """
    Generate a grounded, business-friendly answer from validated SQL results.

    The function:
    - Reports the number of matching records.
    - Displays results in a readable format.
    - Adds record-level citations.
    - Avoids claims that are not supported by the SQL results.
    """

    if not isinstance(result_records, list):
        return (
            "The query results could not be processed because they were not "
            "returned in the expected format."
        )

    if not result_records:
        return (
            "No matching partner records were found for this question.\n\n"
            "The response was generated only from the validated SQLite "
            "query results. No unsupported assumptions were added."
        )

    total_records = len(result_records)
    displayed_records = result_records[:max_records]

    answer_lines = [
        f"Based on the validated SQL query, I found "
        f"{total_records} matching partner record(s).",
        ""
    ]

    for index, record in enumerate(displayed_records, start=1):
        partner_id = (
            record.get("partner_id")
            or record.get("Partner_ID")
            or record.get("id")
            or f"result-{index}"
        )

        partner_name = (
            record.get("partner_name")
            or record.get("Partner_Name")
            or record.get("name")
            or f"Partner {index}"
        )

        answer_lines.append(f"### {index}. {partner_name}")

        for field_name, value in record.items():
            if field_name.lower() not in {"partner_id", "partner_name"}:
                readable_field = format_field_name(field_name)
                readable_value = format_value(value)
                answer_lines.append(
                    f"- **{readable_field}:** {readable_value}"
                )

        answer_lines.append(
            f"- **Citation:** SQLite partner record `{partner_id}`; "
            f"fields returned by the validated SQL query."
        )
        answer_lines.append("")

    if total_records > max_records:
        answer_lines.append(
            f"Only the first {max_records} of {total_records} matching "
            f"records are displayed."
        )
        answer_lines.append("")

    answer_lines.extend(
        [
            "### Source and grounding",
            "This answer was generated exclusively from the validated SQL "
            "query results in the PartnerLens SQLite database. No information "
            "outside the returned database records was used."
        ]
    )

    return "\n".join(answer_lines)
