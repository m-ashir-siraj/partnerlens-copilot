"""
Citation audit module for PartnerLens Copilot.

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
        "citation_audit_passed": passed,
        "missing_terms": missing_terms,
    }
