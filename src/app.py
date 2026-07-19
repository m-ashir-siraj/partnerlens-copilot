"""
Phase 8 Streamlit application for PartnerLens Copilot.

This application demonstrates the complete guarded PartnerLens pipeline:

1. Route a natural-language question to an approved business intent.
2. Generate deterministic SQL from an approved template.
3. Validate the SQL against PartnerLens safety rules.
4. Execute the query using a read-only SQLite connection.
5. Generate a grounded, business-friendly answer.
6. Audit record-level citations against the SQL evidence.
7. Record sanitized execution and citation-audit metadata.

The application uses synthetic PartnerLens data only.
"""

from datetime import datetime, timezone
from pathlib import Path
import json

import streamlit as st


# Support both:
#   streamlit run src/app.py
# and package-based execution.
try:
    from .answer_generator import generate_answer
    from .citation_auditor import audit_citations
    from .query_executor import (
        QueryExecutionError,
        dataframe_to_records,
        execute_query_detailed,
    )
    from .sql_generator import generate_sql
    from .sql_validator import validate_sql_detailed

except ImportError:
    from answer_generator import generate_answer
    from citation_auditor import audit_citations
    from query_executor import (
        QueryExecutionError,
        dataframe_to_records,
        execute_query_detailed,
    )
    from sql_generator import generate_sql
    from sql_validator import validate_sql_detailed


PROJECT_ROOT = Path(__file__).resolve().parents[1]

AUDIT_LOG_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "phase8"
    / "query_audit_log.jsonl"
)

APP_VERSION = "PartnerLens Copilot 2.0 Final"


SAMPLE_QUESTIONS = {
    "Arizona partners with growth above 20%": (
        "Show me partners in Arizona with transaction growth above 20%"
    ),
    "Arizona partners with growth above 15%": (
        "Show me AZ partners with transaction growth above 15%"
    ),
    "Top partners by payment volume": (
        "Show the top partners by payment volume"
    ),
    "Partner pricing information": (
        "Show partner pricing information"
    ),
    "Partner pricing exceptions": (
        "Show partner pricing exceptions"
    ),
    "Partner risk and compliance": (
        "Show partner risk, KYC, and PCI information"
    ),
    "General partner directory": (
        "List all partners"
    ),
    "Unsupported-question demonstration": (
        "What is the weather today?"
    ),
}


def save_audit_record(audit_record: dict) -> bool:
    """
    Append one sanitized application audit record to a JSONL file.

    Raw exception messages and full database paths must not be included
    in the record.
    """

    try:
        AUDIT_LOG_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with AUDIT_LOG_PATH.open(
            "a",
            encoding="utf-8",
        ) as audit_file:
            audit_file.write(
                json.dumps(
                    audit_record,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

        return True

    except OSError:
        # Audit-log failure should be reported in the UI but should not
        # expose local filesystem information.
        return False


def create_base_audit_record(
    user_question: str,
) -> dict:
    """Create the common fields for one application audit record."""

    return {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "application_version": APP_VERSION,
        "user_question": user_question,
        "recognized_intent": None,
        "query_supported": False,
        "generated_sql": None,
        "source_tables": [],
        "validation_status": "not_run",
        "validation_reason_code": None,
        "validation_message": None,
        "validated_row_limit": None,
        "execution_status": "not_run",
        "execution_reason_code": None,
        "row_count": 0,
        "result_columns": [],
        "elapsed_ms": None,
        "citation_audit_status": "not_run",
        "citation_audit_score_pct": None,
        "citation_reason_codes": [],
    }


def render_audit_download(
    audit_record: dict,
    log_saved: bool,
) -> None:
    """Display audit persistence status and a download button."""

    st.subheader("Run Audit Evidence")

    if log_saved:
        st.success(
            "A sanitized audit record was saved successfully."
        )
    else:
        st.warning(
            "The run completed, but the local audit log could not "
            "be updated."
        )

    st.download_button(
        label="Download this run's audit record",
        data=json.dumps(
            audit_record,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        file_name="partnerlens_phase8_run_audit.json",
        mime="application/json",
        use_container_width=True,
    )


def render_supported_topics() -> None:
    """Display topics currently supported by the SQL planner."""

    with st.expander(
        "Questions currently supported by PartnerLens"
    ):
        st.markdown(
            """
            PartnerLens currently supports these controlled query patterns:

            - Arizona partners filtered by transaction growth
            - Top partners ranked by payment volume
            - Partner pricing and pricing exceptions
            - Partner risk, KYC, and PCI information
            - General partner directory questions

            Questions outside these approved patterns are rejected rather
            than mapped to an unrelated database query.
            """
        )


def render_sidebar() -> tuple[int, bool]:
    """Render Phase 8 configuration and control information."""

    with st.sidebar:
        st.header("PartnerLens Controls")

        st.info(
            "This application uses synthetic partner data."
        )

        st.markdown(
            """
            **Phase 8 safeguards**

            - Approved query intents
            - Table allowlisting
            - SELECT-only validation
            - Mandatory row limits
            - Read-only SQLite execution
            - Execution timeout
            - Record-level citations
            - Citation verification
            - Sanitized audit logging
            """
        )

        max_display_records = st.slider(
            "Maximum records in generated answer",
            min_value=1,
            max_value=10,
            value=5,
            help=(
                "The same value is used by the answer generator "
                "and citation auditor."
            ),
        )

        show_technical_details = st.checkbox(
            "Show detailed technical evidence",
            value=True,
        )

        st.divider()
        st.caption(APP_VERSION)

    return max_display_records, show_technical_details


def run_partnerlens(
    user_question: str,
    max_display_records: int,
    show_technical_details: bool,
) -> None:
    """Run and display the complete Phase 8 PartnerLens workflow."""

    audit_record = create_base_audit_record(
        user_question=user_question
    )

    # ---------------------------------------------------------
    # Step 1: Intent routing and SQL generation
    # ---------------------------------------------------------
    with st.spinner(
        "Routing the question to an approved PartnerLens intent..."
    ):
        query_plan = generate_sql(user_question)

    audit_record["recognized_intent"] = (
        query_plan.intent
    )

    audit_record["query_supported"] = (
        query_plan.supported
    )

    audit_record["generated_sql"] = (
        query_plan.sql
    )

    audit_record["source_tables"] = list(
        query_plan.source_tables
    )

    st.subheader("1. Request Routing")

    routing_col1, routing_col2 = st.columns(2)

    routing_col1.metric(
        "Recognized intent",
        query_plan.intent,
    )

    routing_col2.metric(
        "Query supported",
        "Yes" if query_plan.supported else "No",
    )

    st.caption(query_plan.explanation)

    if not query_plan.supported:
        st.warning(
            "PartnerLens did not generate or execute SQL because the "
            "question does not match an approved query pattern."
        )

        audit_record["execution_status"] = (
            "not_executed"
        )

        log_saved = save_audit_record(
            audit_record
        )

        render_supported_topics()

        if show_technical_details:
            with st.expander(
                "Unsupported-request audit details",
                expanded=True,
            ):
                st.json(audit_record)

        render_audit_download(
            audit_record=audit_record,
            log_saved=log_saved,
        )

        return

    # ---------------------------------------------------------
    # Step 2: Generated SQL
    # ---------------------------------------------------------
    st.subheader("2. Generated SQL")

    st.code(
        query_plan.sql,
        language="sql",
    )

    st.caption(
        "SQL was generated from an approved deterministic "
        "PartnerLens query template."
    )

    # ---------------------------------------------------------
    # Step 3: Central SQL validation
    # ---------------------------------------------------------
    validation = validate_sql_detailed(
        query_plan.sql
    )

    audit_record["validation_status"] = (
        "passed"
        if validation.is_valid
        else "failed"
    )

    audit_record["validation_reason_code"] = (
        validation.reason_code
    )

    audit_record["validation_message"] = (
        validation.message
    )

    audit_record["source_tables"] = list(
        validation.referenced_tables
    )

    audit_record["validated_row_limit"] = (
        validation.row_limit
    )

    st.subheader("3. SQL Safety Validation")

    if validation.is_valid:
        st.success(validation.message)
    else:
        st.error(validation.message)

    validation_col1, validation_col2 = st.columns(2)

    validation_col1.metric(
        "Validated tables",
        len(validation.referenced_tables),
    )

    validation_col2.metric(
        "Validated row limit",
        (
            validation.row_limit
            if validation.row_limit is not None
            else "Not approved"
        ),
    )

    if validation.referenced_tables:
        st.caption(
            "Approved source tables: "
            + ", ".join(
                validation.referenced_tables
            )
        )

    if show_technical_details:
        with st.expander(
            "Detailed validation evidence"
        ):
            st.json(
                {
                    "is_valid": validation.is_valid,
                    "reason_code": validation.reason_code,
                    "message": validation.message,
                    "referenced_tables": list(
                        validation.referenced_tables
                    ),
                    "row_limit": validation.row_limit,
                }
            )

    if not validation.is_valid:
        audit_record["execution_status"] = (
            "blocked_by_validation"
        )

        log_saved = save_audit_record(
            audit_record
        )

        render_audit_download(
            audit_record=audit_record,
            log_saved=log_saved,
        )

        return

    # ---------------------------------------------------------
    # Step 4: Read-only query execution
    # ---------------------------------------------------------
    st.subheader("4. Read-Only Query Execution")

    try:
        with st.spinner(
            "Executing the validated query using a read-only "
            "database connection..."
        ):
            execution_result = execute_query_detailed(
                sql=query_plan.sql
            )

    except QueryExecutionError as error:
        audit_record["execution_status"] = "failed"
        audit_record["execution_reason_code"] = (
            error.reason_code
        )

        st.error(
            "PartnerLens could not safely complete the query."
        )

        st.warning(error.safe_message)

        log_saved = save_audit_record(
            audit_record
        )

        render_audit_download(
            audit_record=audit_record,
            log_saved=log_saved,
        )

        return

    except Exception as error:
        # Do not expose the raw exception or filesystem details.
        audit_record["execution_status"] = "failed"
        audit_record["execution_reason_code"] = (
            f"unexpected_{type(error).__name__}"
        )

        st.error(
            "PartnerLens encountered an unexpected execution error."
        )

        st.warning(
            "The query was stopped and no unvalidated result "
            "was displayed."
        )

        log_saved = save_audit_record(
            audit_record
        )

        render_audit_download(
            audit_record=audit_record,
            log_saved=log_saved,
        )

        return

    audit_record["execution_status"] = (
        execution_result.status
    )

    audit_record["row_count"] = (
        execution_result.row_count
    )

    audit_record["result_columns"] = list(
        execution_result.columns
    )

    audit_record["source_tables"] = list(
        execution_result.source_tables
    )

    audit_record["validated_row_limit"] = (
        execution_result.validated_row_limit
    )

    audit_record["elapsed_ms"] = (
        execution_result.elapsed_ms
    )

    execution_col1, execution_col2, execution_col3 = (
        st.columns(3)
    )

    execution_col1.metric(
        "Rows returned",
        execution_result.row_count,
    )

    execution_col2.metric(
        "Execution time",
        f"{execution_result.elapsed_ms:,.2f} ms",
    )

    execution_col3.metric(
        "Validated limit",
        execution_result.validated_row_limit,
    )

    st.caption(
        "Executed against approved source tables: "
        + ", ".join(execution_result.source_tables)
    )

    st.dataframe(
        execution_result.dataframe,
        use_container_width=True,
        hide_index=True,
    )

    # ---------------------------------------------------------
    # Step 5: Grounded answer generation
    # ---------------------------------------------------------
    result_records = dataframe_to_records(
        execution_result.dataframe
    )

    try:
        answer = generate_answer(
            user_question=user_question,
            result_records=result_records,
            source_tables=execution_result.source_tables,
            max_records=max_display_records,
        )

    except Exception as error:
        audit_record["citation_audit_status"] = (
            "answer_generation_failed"
        )

        audit_record["citation_reason_codes"] = [
            f"unexpected_{type(error).__name__}"
        ]

        st.error(
            "PartnerLens could not generate the grounded answer."
        )

        st.warning(
            "The SQL results are shown above, but no generated answer "
            "was published."
        )

        log_saved = save_audit_record(
            audit_record
        )

        render_audit_download(
            audit_record=audit_record,
            log_saved=log_saved,
        )

        return

    st.subheader("5. Grounded Business Answer")

    st.markdown(answer)

    # ---------------------------------------------------------
    # Step 6: Citation audit
    # ---------------------------------------------------------
    citation_audit = audit_citations(
        answer=answer,
        result_records=result_records,
        source_tables=execution_result.source_tables,
        max_records=max_display_records,
    )

    audit_record["citation_audit_status"] = (
        "passed"
        if citation_audit["citation_audit_passed"]
        else "failed"
    )

    audit_record["citation_audit_score_pct"] = (
        citation_audit["audit_score_pct"]
    )

    audit_record["citation_reason_codes"] = (
        citation_audit["reason_codes"]
    )

    st.subheader("6. Citation Audit")

    if citation_audit["citation_audit_passed"]:
        st.success(
            "The answer passed the record-level citation audit."
        )
    else:
        st.error(
            "The answer failed one or more citation-audit checks."
        )

    citation_col1, citation_col2, citation_col3 = (
        st.columns(3)
    )

    citation_col1.metric(
        "Audit score",
        f"{citation_audit['audit_score_pct']}%",
    )

    citation_col2.metric(
        "Expected citations",
        len(
            citation_audit["expected_record_ids"]
        ),
    )

    citation_col3.metric(
        "Citations found",
        len(
            citation_audit["cited_record_ids"]
        ),
    )

    if citation_audit["reason_codes"]:
        st.warning(
            "Audit findings: "
            + ", ".join(
                citation_audit["reason_codes"]
            )
        )

    if show_technical_details:
        with st.expander(
            "Detailed citation-audit evidence",
            expanded=not citation_audit[
                "citation_audit_passed"
            ],
        ):
            st.json(citation_audit)

    # ---------------------------------------------------------
    # Step 7: Persist audit evidence
    # ---------------------------------------------------------
    log_saved = save_audit_record(
        audit_record
    )

    if show_technical_details:
        with st.expander(
            "Complete sanitized run record"
        ):
            st.json(audit_record)

    render_audit_download(
        audit_record=audit_record,
        log_saved=log_saved,
    )


def main() -> None:
    """Render the PartnerLens Phase 8 application."""

    st.set_page_config(
        page_title="PartnerLens Copilot",
        page_icon="🔎",
        layout="wide",
    )

    max_display_records, show_technical_details = (
        render_sidebar()
    )

    st.title("PartnerLens Copilot")

    st.subheader(
        "Citation-Audited Partner Pricing and "
        "Demographic Intelligence Assistant"
    )

    st.markdown(
        """
        Ask a natural-language business question about the synthetic
        PartnerLens dataset. The application generates approved SQL,
        validates it, executes it through a read-only database connection,
        produces a grounded answer, and audits the answer against the
        returned records.
        """
    )

    render_supported_topics()

    st.divider()

    selected_sample_label = st.selectbox(
        "Choose a demonstration question",
        options=list(SAMPLE_QUESTIONS.keys()),
    )

    selected_sample_question = SAMPLE_QUESTIONS[
        selected_sample_label
    ]

    custom_question = st.text_area(
        "Optional: enter your own question",
        placeholder=(
            "Leave this blank to use the selected "
            "demonstration question."
        ),
        height=100,
    )

    user_question = (
        custom_question.strip()
        if custom_question.strip()
        else selected_sample_question
    )

    st.caption(
        f"Question to be submitted: {user_question}"
    )

    run_button = st.button(
        "Run PartnerLens Copilot",
        type="primary",
        use_container_width=True,
    )

    if not run_button:
        return

    if not user_question.strip():
        st.warning(
            "Enter a PartnerLens business question."
        )
        return

    run_partnerlens(
        user_question=user_question,
        max_display_records=max_display_records,
        show_technical_details=show_technical_details,
    )


if __name__ == "__main__":
    main()
