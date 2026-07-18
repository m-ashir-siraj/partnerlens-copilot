"""
Record-level citation audit module for PartnerLens Copilot.

The baseline auditor checks whether the generated answer includes
basic source-field language.
"""


def audit_citations(answer: str, required_terms: list[str] | None = None) -> dict:
    """Audit whether the answer includes source-field support language."""
    if required_terms is None:
        required_terms = ["source fields", "query result"]

    answer_lower = answer.lower()

    missing_terms = [
        term for term in required_terms
        if term.lower() not in answer_lower
    ]

    passed = len(missing_terms) == 0

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