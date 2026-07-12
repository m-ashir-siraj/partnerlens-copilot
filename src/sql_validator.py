"""
Guardrailed SQL validation module for PartnerLens Copilot.

Phase 8 validation rules:

1. Only one SQL statement is allowed.
2. Only SELECT statements are allowed.
3. SQL comments are rejected.
4. Data-changing and administrative commands are blocked.
5. Only approved PartnerLens tables may be referenced.
6. Subqueries and compound queries are rejected.
7. SELECT * is rejected to support data minimization and citations.
8. Every query must have a bounded LIMIT clause.
9. Risky SQLite functions are blocked.

This validator is a defense-in-depth control. The database connection
should also be opened in read-only mode before query execution.
"""

from dataclasses import dataclass
import re

import sqlparse
from sqlparse.sql import (
    Identifier,
    IdentifierList,
    Parenthesis,
    TokenList,
)
from sqlparse.tokens import Keyword, Name, Wildcard


MAX_RESULT_ROWS = 25

ALLOWED_TABLES = frozenset(
    {
        "partners",
        "partner_pricing",
        "partner_current_preview",
    }
)

BLOCKED_KEYWORDS = frozenset(
    {
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "REPLACE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "VACUUM",
        "REINDEX",
        "ANALYZE",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "RELEASE",
        "GRANT",
        "REVOKE",
        "MERGE",
        "CALL",
        "EXECUTE",
        "INTO",
    }
)

UNSUPPORTED_SQL_KEYWORDS = frozenset(
    {
        "WITH",
        "UNION",
        "INTERSECT",
        "EXCEPT",
    }
)

BLOCKED_FUNCTIONS = frozenset(
    {
        "load_extension",
        "readfile",
        "writefile",
    }
)

COMMENT_PATTERN = re.compile(
    r"--[^\r\n]*|/\*.*?\*/",
    flags=re.DOTALL,
)

STRING_LITERAL_PATTERN = re.compile(
    r"'(?:''|[^'])*'",
    flags=re.DOTALL,
)


@dataclass(frozen=True)
class SQLValidationResult:
    """
    Detailed result produced by the Phase 8 SQL validator.

    Attributes:
        is_valid: Whether the SQL passed all validation rules.
        reason_code: Machine-readable validation outcome.
        message: User-safe explanation of the outcome.
        referenced_tables: Approved tables found in the query.
        row_limit: LIMIT value found in the query.
    """

    is_valid: bool
    reason_code: str
    message: str
    referenced_tables: tuple[str, ...] = ()
    row_limit: int | None = None


class SQLStructureError(ValueError):
    """Raised when unsupported SQL structure is detected."""


def _invalid_result(
    reason_code: str,
    message: str,
    referenced_tables: tuple[str, ...] = (),
    row_limit: int | None = None,
) -> SQLValidationResult:
    """Create a failed validation result."""

    return SQLValidationResult(
        is_valid=False,
        reason_code=reason_code,
        message=message,
        referenced_tables=referenced_tables,
        row_limit=row_limit,
    )


def _mask_string_literals(sql: str) -> str:
    """
    Mask single-quoted values before keyword inspection.

    This prevents a value such as 'Drop Zone Payments' from being
    mistaken for the SQL command DROP.
    """

    return STRING_LITERAL_PATTERN.sub("''", sql)


def _contains_exact_keyword(sql: str, keyword: str) -> bool:
    """Check for a complete SQL keyword using word boundaries."""

    return (
        re.search(
            rf"\b{re.escape(keyword)}\b",
            sql,
            flags=re.IGNORECASE,
        )
        is not None
    )


def contains_blocked_keywords(sql: str) -> bool:
    """
    Check for blocked keywords without substring false positives.

    For example, UPDATE is blocked, but updated_at is not.
    """

    masked_sql = _mask_string_literals(sql)

    return any(
        _contains_exact_keyword(masked_sql, keyword)
        for keyword in BLOCKED_KEYWORDS
    )


def is_select_query(sql: str) -> bool:
    """Check that SQL contains exactly one SELECT statement."""

    if not isinstance(sql, str) or not sql.strip():
        return False

    parsed_statements = [
        statement
        for statement in sqlparse.parse(sql)
        if str(statement).strip()
    ]

    if len(parsed_statements) != 1:
        return False

    return parsed_statements[0].get_type() == "SELECT"


def _contains_subquery(token_list: TokenList) -> bool:
    """Detect SELECT statements nested inside parentheses."""

    for token in token_list.tokens:
        if isinstance(token, Parenthesis):
            if re.search(
                r"\bSELECT\b",
                token.value,
                flags=re.IGNORECASE,
            ):
                return True

        if isinstance(token, TokenList):
            if _contains_subquery(token):
                return True

    return False


def _normalize_table_name(table_name: str) -> str:
    """Normalize an extracted table name."""

    return table_name.strip().strip('`"[]').lower()


def _extract_table_from_identifier(identifier: Identifier) -> str:
    """
    Extract a table name from a sqlparse Identifier.

    Subqueries and schema-qualified references are rejected because
    Phase 8 generated SQL uses only direct PartnerLens table references.
    """

    if any(
        isinstance(token, Parenthesis)
        for token in identifier.tokens
    ):
        raise SQLStructureError(
            "Subqueries and table-valued functions are not supported."
        )

    if identifier.get_parent_name():
        raise SQLStructureError(
            "Schema-qualified table references are not supported."
        )

    table_name = identifier.get_real_name()

    if not table_name:
        raise SQLStructureError(
            "A referenced table name could not be identified."
        )

    return _normalize_table_name(table_name)


def _extract_referenced_tables(statement: TokenList) -> tuple[str, ...]:
    """
    Extract tables appearing after FROM and JOIN clauses.

    Explicit JOIN syntax and comma-separated table lists are inspected.
    """

    referenced_tables: list[str] = []
    expecting_table = False

    for token in statement.tokens:
        if token.is_whitespace:
            continue

        if token.ttype in Keyword:
            normalized_keyword = token.normalized.upper()

            if (
                normalized_keyword == "FROM"
                or normalized_keyword.endswith("JOIN")
            ):
                expecting_table = True
                continue

        if not expecting_table:
            continue

        if isinstance(token, IdentifierList):
            for identifier in token.get_identifiers():
                if not isinstance(identifier, Identifier):
                    raise SQLStructureError(
                        "Unsupported table-list structure detected."
                    )

                referenced_tables.append(
                    _extract_table_from_identifier(identifier)
                )

        elif isinstance(token, Identifier):
            referenced_tables.append(
                _extract_table_from_identifier(token)
            )

        elif token.ttype in (Name, Keyword):
            referenced_tables.append(
                _normalize_table_name(token.value)
            )

        else:
            raise SQLStructureError(
                "Unsupported table-reference structure detected."
            )

        expecting_table = False

    if expecting_table:
        raise SQLStructureError(
            "A FROM or JOIN clause is missing its table reference."
        )

    return tuple(dict.fromkeys(referenced_tables))


def _contains_wildcard(statement: TokenList) -> bool:
    """Check whether the query contains SELECT * or table.*."""

    return any(
        token.ttype == Wildcard
        for token in statement.flatten()
    )


def _extract_limit(masked_sql: str) -> tuple[int | None, str | None]:
    """
    Extract and validate the LIMIT clause.

    Returns:
        A tuple containing:
        - The numeric limit, or None
        - An error message, or None
    """

    normalized_sql = re.sub(r"\s+", " ", masked_sql.strip())

    # Reject SQLite's LIMIT offset, count syntax because the second
    # number represents the actual row count.
    if re.search(
        r"\bLIMIT\s+\d+\s*,",
        normalized_sql,
        flags=re.IGNORECASE,
    ):
        return (
            None,
            "Comma-based LIMIT syntax is not supported.",
        )

    limit_matches = re.findall(
        r"\bLIMIT\s+(\d+)\b",
        normalized_sql,
        flags=re.IGNORECASE,
    )

    if not limit_matches:
        return (
            None,
            "Every query must include a LIMIT clause.",
        )

    if len(limit_matches) != 1:
        return (
            None,
            "Exactly one LIMIT clause is required.",
        )

    row_limit = int(limit_matches[0])

    if row_limit < 1:
        return (
            None,
            "The query LIMIT must be at least 1.",
        )

    if row_limit > MAX_RESULT_ROWS:
        return (
            row_limit,
            f"The query LIMIT cannot exceed {MAX_RESULT_ROWS}.",
        )

    return row_limit, None


def validate_sql_detailed(sql: str) -> SQLValidationResult:
    """
    Apply all Phase 8 SQL validation rules.

    This function returns detailed metadata suitable for audit logging.
    """

    if not isinstance(sql, str):
        return _invalid_result(
            reason_code="invalid_input_type",
            message="SQL must be provided as text.",
        )

    if not sql.strip():
        return _invalid_result(
            reason_code="empty_sql",
            message="SQL query is empty.",
        )

    masked_sql = _mask_string_literals(sql)

    if COMMENT_PATTERN.search(masked_sql):
        return _invalid_result(
            reason_code="comments_not_allowed",
            message="SQL comments are not allowed.",
        )

    try:
        parsed_statements = [
            statement
            for statement in sqlparse.parse(sql)
            if str(statement).strip()
        ]
    except Exception:
        return _invalid_result(
            reason_code="parse_failed",
            message="The SQL statement could not be parsed.",
        )

    if len(parsed_statements) != 1:
        return _invalid_result(
            reason_code="multiple_statements",
            message="Exactly one SQL statement is allowed.",
        )

    statement = parsed_statements[0]

    if statement.get_type() != "SELECT":
        return _invalid_result(
            reason_code="not_select",
            message="Only SELECT queries are allowed.",
        )

    for keyword in BLOCKED_KEYWORDS:
        if _contains_exact_keyword(masked_sql, keyword):
            return _invalid_result(
                reason_code="blocked_keyword",
                message=(
                    "The SQL query contains a blocked operation: "
                    f"{keyword}."
                ),
            )

    for keyword in UNSUPPORTED_SQL_KEYWORDS:
        if _contains_exact_keyword(masked_sql, keyword):
            return _invalid_result(
                reason_code="unsupported_sql_structure",
                message=(
                    "The following SQL structure is not supported: "
                    f"{keyword}."
                ),
            )

    for function_name in BLOCKED_FUNCTIONS:
        if re.search(
            rf"\b{re.escape(function_name)}\s*\(",
            masked_sql,
            flags=re.IGNORECASE,
        ):
            return _invalid_result(
                reason_code="blocked_function",
                message=(
                    "The SQL query contains a blocked function: "
                    f"{function_name}."
                ),
            )

    if _contains_subquery(statement):
        return _invalid_result(
            reason_code="subquery_not_allowed",
            message="Subqueries are not supported.",
        )

    if _contains_wildcard(statement):
        return _invalid_result(
            reason_code="wildcard_not_allowed",
            message=(
                "Wildcard selection is not allowed. "
                "List the required columns explicitly."
            ),
        )

    try:
        referenced_tables = _extract_referenced_tables(statement)
    except SQLStructureError as error:
        return _invalid_result(
            reason_code="unsupported_table_structure",
            message=str(error),
        )

    if not referenced_tables:
        return _invalid_result(
            reason_code="missing_source_table",
            message=(
                "The query must reference an approved PartnerLens table."
            ),
        )

    unapproved_tables = sorted(
        set(referenced_tables) - ALLOWED_TABLES
    )

    if unapproved_tables:
        return _invalid_result(
            reason_code="unapproved_table",
            message=(
                "The query references an unapproved table: "
                + ", ".join(unapproved_tables)
                + "."
            ),
            referenced_tables=referenced_tables,
        )

    row_limit, limit_error = _extract_limit(masked_sql)

    if limit_error:
        return _invalid_result(
            reason_code="invalid_limit",
            message=limit_error,
            referenced_tables=referenced_tables,
            row_limit=row_limit,
        )

    return SQLValidationResult(
        is_valid=True,
        reason_code="validation_passed",
        message="SQL query passed all Phase 8 validation checks.",
        referenced_tables=referenced_tables,
        row_limit=row_limit,
    )


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Backward-compatible validation function.

    Existing application code can continue using:

        is_valid, message = validate_sql(sql)

    Use validate_sql_detailed when audit metadata is required.
    """

    result = validate_sql_detailed(sql)

    return result.is_valid, result.message
