"""
Baseline SQL generator for PartnerLens Copilot.

Version 1 uses rule-based SQL generation for demonstration.
The final version can replace this with an LLM-based SQL generator.
"""


def generate_sql(user_question: str) -> str:
    """Generate baseline SQL from a user question."""
    question = user_question.lower()

    if ("arizona" in question or "az" in question) and "growth" in question:
        return """
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
          AND txn_growth_pct > 20
        ORDER BY txn_growth_pct DESC
        LIMIT 25;
        """

    if "pricing" in question or "price" in question:
        return """
        SELECT
            p.partner_id,
            p.pricing_plan_id,
            p.recommended_pricing_plan_id,
            p.negotiated_bps,
            p.negotiated_per_txn_fee_usd,
            p.exception_flag,
            p.approval_status
        FROM partner_pricing p
        LIMIT 25;
        """

    if "top partners" in question or "payment volume" in question or "transaction volume" in question:
        return """
        SELECT
            partner_id,
            partner_name,
            industry_vertical,
            state,
            payment_volume_usd,
            txn_count,
            net_revenue_usd
        FROM partner_current_preview
        ORDER BY payment_volume_usd DESC
        LIMIT 10;
        """

    if "risk" in question:
        return """
        SELECT
            partner_id,
            partner_name,
            industry_vertical,
            state,
            risk_tier,
            kyc_status,
            pci_level
        FROM partners
        ORDER BY risk_tier
        LIMIT 25;
        """

    return """
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
    LIMIT 25;
    """
