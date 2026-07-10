from src.citation_auditor import audit_citations


def test_citation_audit_passes():
    answer = "The answer is based on source fields from the partners table."
    result = audit_citations(answer)
    assert result["citation_audit_passed"] is True


def test_citation_audit_fails():
    answer = "The answer is based on the result."
    result = audit_citations(answer)
    assert result["citation_audit_passed"] is False
