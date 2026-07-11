"""
Streamlit baseline application for PartnerLens Copilot.
"""

import streamlit as st

from sql_generator import generate_sql
from sql_validator import validate_sql
from query_executor import execute_query
from answer_generator import generate_answer
from citation_auditor import audit_citations


st.set_page_config(
    page_title="PartnerLens Copilot",
    page_icon="📊",
    layout="wide",
)

st.title("PartnerLens Copilot")
st.subheader("Citation-Audited Partner Pricing & Demographic Intelligence Assistant")

st.write(
    "Ask a natural-language question about the synthetic partner dataset. "
    "The baseline system generates SQL, validates it, executes it, "
    "generates an answer, and audits the answer for source-field support."
)

sample_questions = [
    "Show me partners in Arizona with transaction growth above 20%",
    "Show top partners by payment volume",
    "Show pricing information",
    "Show partner risk information",
]

selected_question = st.selectbox("Choose a sample question", sample_questions)

user_question = st.text_input("Or enter your own question", selected_question)

if st.button("Run PartnerLens Copilot"):
    sql = generate_sql(user_question)

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    is_valid, validation_message = validate_sql(sql)

    st.subheader("SQL Validation")
    st.write(validation_message)

    if is_valid:
        result_df = execute_query(sql)

        st.subheader("Query Results")
        st.dataframe(result_df)

        result_records = result_df.to_dict(orient="records")
        answer = generate_answer(user_question, result_records)

        st.subheader("Generated Answer")
        st.write(answer)

        audit_result = audit_citations(answer)

        st.subheader("Citation Audit")
        st.json(audit_result)
    else:
        st.error("The generated SQL did not pass validation.")
