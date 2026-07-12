"""
Guardrailed SQL generation module for PartnerLens Copilot.

The Phase 8 implementation uses deterministic, rule-based query planning
for supported business questions. Each generated query includes:

- A recognized business intent
- Approved source tables
- Read-only SQL
- Bounded result limits
- An explanation of the applied rule

Unsupported questions are rejected instead of being mapped to an
unrelated generic query.
"""

from dataclasses import dataclass
import re


MAX_RESULT_ROWS = 25

ALLOWED_TABLES = {
    "partners",
    "partner_pricing",
    "partner_current_preview",
}

FORBIDDEN_SQL_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
}


@dataclass(frozen=True)
class SQLQueryPlan:
    """
    Structured result returned by the SQL generator.

    Attributes:
        supported: Whether the question matched an approved query pattern.
        intent: Business intent identified from the question.
        sql: Generated SQL, or None when the question is unsupported.
        source_tables: Database tables used by the query.
        explanation: Human-readable explanation of the selected rule.
    """

    supported: bool
    intent: str
    sql: str | None
    source_tables: tuple[str, ...]
    explanation: str


def normalize_question(user_question: str) -> str:
    """Normalize whitespace and capitalization for intent matching."""
    return re.sub(r"\s+", " ", user_question.strip().lower())


def contains_phrase(question: str, phrase: str) -> bool:
    """Check for a complete phrase instead of a partial word match."""
    pattern = rf"\b{re.escape(phrase.lower())}\b"
    return re.search(pattern, question) is not None


def extract_growth_filter(question: str) -> tuple[str, float] | None:
    """
    Extract a safe growth comparison and percentage threshold.

    Supported examples:
        above 20%
        over 15
        greater than 10%
        at least 25%
        below 5%
        at most 30%

    When no explicit threshold is supplied, the baseline default is > 20%.
    """

    patterns = [
        (
            r"\b(?:at least|minimum of)\s+(\d+(?:\.\d+)?)\s*%?",
            ">=",
        ),
        (
            r"\b(?:above|over|greater than|more than)\s+"
            r"(\d+(?:\.\d+)?)\s*%?",
            ">",
        ),
        (
            r"\b(?:at most|maximum of)\s+(\d+(?:\.\d+)?)\s*%?",
            "<=",
        ),
        (
            r"\b(?:below|under|less than)\s+"
            r"(\d+(?:\.\d+)?)\s*%?",
            "<",
        ),
        (
            r">\s*(\d+(?:\.\d+)?)\s*%?",
            ">",
        ),
        (
            r"<\s*(\d+(?:\.\d+)?)\s*%?",
            "<",
        ),
    ]

    for pattern, operator in patterns:
        match = re.search(pattern, question)

        if match:
            threshold = float(match.group(1))

            # Guard against unreasonable or malformed percentages.
            if not 0 <= threshold <= 500:
                return None

            return operator, threshold

    return ">", 20.0


def validate_generated_sql(sql: str) -> tuple[bool, str]:
    """
    Validate that generated SQL follows PartnerLens safety rules.

    This is a lightweight generator-level validation. The SQL executor
    should still apply its own read-only validation before execution.
    """

    normalized_sql = re.sub(r"\s+", " ", sql.strip().lower())

    if not normalized_sql.startswith("select"):
        return False, "Only SELECT queries are permitted."

    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized_sql):
            return False, f"Forbidden SQL keyword detected: {keyword}."

    referenced_tables = set(
        re.findall(
            r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            normalized_sql,
        )
    )

    unapproved_tables = referenced_tables - ALLOWED_TABLES

    if unapproved_tables:
        return (
            False,
            "Unapproved table reference detected: "
            + ", ".join(sorted(unapproved_tables)),
        )

    limit_match = re.search(r"\blimit\s+(\d+)", normalized_sql)

    if not limit_match:
        return False, "Every generated query must include a LIMIT clause."

    query_limit = int(limit_match.group(1))

    if query_limit > MAX_RESULT_ROWS:
        return (
            False,
            f"Query limit exceeds the maximum of {MAX_RESULT_ROWS}.",
        )

    return True, "SQL passed generator-level validation."


def create_query_plan(
    intent: str,
    sql: str,
    source_tables: tuple[str, ...],
    explanation: str,
) -> SQLQueryPlan:
    """Validate SQL and construct a supported query plan."""

    cleaned_sql = sql.strip()
    is_valid, validation_message = validate_generated_sql(cleaned_sql)

    if not is_valid:
        return SQLQueryPlan(
            supported=False,
            intent="validation_failed",
            sql=None,
            source_tables=(),
            explanation=validation_message,
        )

    return SQLQueryPlan(
        supported=True,
        intent=intent,
        sql=cleaned_sql,
        source_tables=source_tables,
        explanation=explanation,
    )


def unsupported_query_plan(explanation: str) -> SQLQueryPlan:
    """Return a safe result when no approved intent is recognized."""

    return SQLQueryPlan(
        supported=False,
        intent="unsupported",
        sql=None,
        source_tables=(),
        explanation=explanation,
    )


def generate_sql(user_question: str) -> SQLQueryPlan:
    """
    Generate an approved SQL query plan from a business question.

    The generator supports a controlled set of PartnerLens intents.
    User-provided text is never inserted directly into SQL.
    """

    if not isinstance(user_question, str):
        return unsupported_query_plan(
            "The question must be provided as text."
        )

    question = normalize_question(user_question)

    if not question:
        return unsupported_query_plan(
            "Please enter a business question before running a query."
        )

    # ---------------------------------------------------------
    # Intent 1: Arizona partners filtered by transaction growth
    # ---------------------------------------------------------
    is_arizona_question = (
        contains_phrase(question, "arizona")
        or contains_phrase(question, "az")
    )

    is_growth_question = (
        contains_phrase(question, "growth")
        or contains_phrase(question, "txn growth")
        or contains_phrase(question, "transaction growth")
    )

    if is_arizona_question and is_growth_question:
        growth_filter = extract_growth_filter(question)

        if growth_filter is None:
            return unsupported_query_plan(
                "The requested growth percentage is outside the "
                "supported range of 0% to 500%."
            )

        operator, threshold = growth_filter

        sql = f"""
        SELECT
            partner_id,
            partner_name,
            industry_vertical,
            state,
            txn_growth_pct,
            payment_volume_usd,
            net_revenue_usd
        FROM partner_current_preview
        WHERE state = 'AZ'
          AND txn_growth_pct {operator} {threshold}
        ORDER BY txn_growth_pct DESC, partner_name ASC
        LIMIT {MAX_RESULT_ROWS};
        """

        return create_query_plan(
            intent="arizona_growth_filter",
            sql=sql,
            source_tables=("partner_current_preview",),
            explanation=(
                "Matched the Arizona transaction-growth rule using "
                f"txn_growth_pct {operator} {threshold}%."
            ),
        )

    # ---------------------------------------------------------
    # Intent 2: Pricing and pricing-exception questions
    # ---------------------------------------------------------
    if any(
        contains_phrase(question, phrase)
        for phrase in (
            "pricing",
            "price",
            "pricing plan",
            "negotiated fee",
            "basis points",
            "bps",
            "pricing exception",
        )
    ):
        sql = f"""
        SELECT
            pp.partner_id,
            p.partner_name,
            p.industry_vertical,
            p.state,
            pp.pricing_plan_id,
            pp.recommended_pricing_plan_id,
            pp.negotiated_bps,
            pp.negotiated_per_txn_fee_usd,
            pp.exception_flag,
            pp.approval_status
        FROM partner_pricing AS pp
        LEFT JOIN partners AS p
            ON pp.partner_id = p.partner_id
        ORDER BY
            pp.exception_flag DESC,
            p.partner_name ASC
        LIMIT {MAX_RESULT_ROWS};
        """

        return create_query_plan(
            intent="partner_pricing",
            sql=sql,
            source_tables=("partner_pricing", "partners"),
            explanation=(
                "Matched the partner-pricing rule and joined partner "
                "master data to provide readable partner names."
            ),
        )

    # ---------------------------------------------------------
    # Intent 3: Top partners by payment volume
    # ---------------------------------------------------------
    if any(
        contains_phrase(question, phrase)
        for phrase in (
            "top partners",
            "payment volume",
            "transaction volume",
            "highest volume",
            "largest partners",
        )
    ):
        sql = """
        SELECT
            partner_id,
            partner_name,
            industry_vertical,
            state,
            payment_volume_usd,
            txn_count,
            net_revenue_usd
        FROM partner_current_preview
        ORDER BY
            payment_volume_usd DESC,
            partner_name ASC
        LIMIT 10;
        """

        return create_query_plan(
            intent="top_partners_by_payment_volume",
            sql=sql,
            source_tables=("partner_current_preview",),
            explanation=(
                "Matched the top-partners rule and ranked partners by "
                "payment_volume_usd in descending order."
            ),
        )

    # ---------------------------------------------------------
    # Intent 4: Partner risk and compliance
    # ---------------------------------------------------------
    if any(
        contains_phrase(question, phrase)
        for phrase in (
            "risk",
            "risk tier",
            "kyc",
            "pci",
            "compliance",
        )
    ):
        sql = f"""
        SELECT
            partner_id,
            partner_name,
            industry_vertical,
            state,
            risk_tier,
            kyc_status,
            pci_level
        FROM partners
        ORDER BY
            CASE
                WHEN LOWER(risk_tier) = 'high' THEN 1
                WHEN LOWER(risk_tier) = 'medium' THEN 2
                WHEN LOWER(risk_tier) = 'low' THEN 3
                ELSE 4
            END,
            partner_name ASC
        LIMIT {MAX_RESULT_ROWS};
        """

        return create_query_plan(
            intent="partner_risk",
            sql=sql,
            source_tables=("partners",),
            explanation=(
                "Matched the partner risk and compliance rule. Results "
                "are ordered from high risk to low risk."
            ),
        )

    # ---------------------------------------------------------
    # Intent 5: General partner directory
    # ---------------------------------------------------------
    if any(
        contains_phrase(question, phrase)
        for phrase in (
            "show partners",
            "list partners",
            "all partners",
            "partner directory",
            "partner list",
        )
    ):
        sql = f"""
        SELECT
            partner_id,
            partner_name,
            partner_type,
            industry_vertical,
            partner_size,
            partner_status,
            state,
            region,
            risk_tier,
            kyc_status
        FROM partners
        ORDER BY partner_name ASC
        LIMIT {MAX_RESULT_ROWS};
        """

        return create_query_plan(
            intent="partner_directory",
            sql=sql,
            source_tables=("partners",),
            explanation=(
                "Matched the general partner-directory rule."
            ),
        )

    # Do not silently run a broad query for an unrelated question.
    return unsupported_query_plan(
        "This question does not match a currently supported PartnerLens "
        "query pattern. Supported topics include Arizona transaction "
        "growth, partner pricing, top partners by payment volume, "
        "partner risk and compliance, and the general partner directory."
    )
