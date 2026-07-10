"""
SQL validation module for PartnerLens Copilot.

The baseline validator only allows SELECT statements and blocks unsafe SQL keywords.
"""

import sqlparse


BLOCKED_KEYWORDS = [
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
]


def is_select_query(sql: str) -> bool:
    """Check whether the SQL query starts with SELECT."""
    parsed = sqlparse.parse(sql)

    if not parsed:
        return False

    first_statement = parsed[0]
    return first_statement.get_type() == "SELECT"


def contains_blocked_keywords(sql: str) -> bool:
    """Check whether SQL contains blocked keywords."""
    upper_sql = sql.upper()
    return any(keyword in upper_sql for keyword in BLOCKED_KEYWORDS)


def validate_sql(sql: str) -> tuple[bool, str]:
    """Validate SQL query for baseline safety."""
    if not sql or not sql.strip():
        return False, "SQL query is empty."

    if contains_blocked_keywords(sql):
        return False, "SQL query contains blocked keywords."

    if not is_select_query(sql):
        return False, "Only SELECT queries are allowed."

    return True, "SQL query passed validation."
