"""
Answer generation module for PartnerLens Copilot.
"""


def generate_answer(user_question: str, result_records: list[dict]) -> str:
    """Generate a simple business-friendly answer from SQL query results."""
    if not result_records:
        return (
            "No matching partner records were found for the question. "
            "Source fields checked: query result columns."
        )

    answer = (
        f"Based on the validated SQL query, I found "
        f"{len(result_records)} matching record(s).\n\n"
    )

    for record in result_records[:5]:
        answer += f"- {record}\n"

    answer += "\nSource fields used: query result columns from the SQLite database."

    return answer
