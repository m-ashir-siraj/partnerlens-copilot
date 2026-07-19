# PartnerLens Copilot
## Citation-Audited Partner Pricing & Demographic Intelligence Assistant

**Final Capstone Submission — Version 2.0**

PartnerLens Copilot is a controlled natural-language-to-SQL
assistant for synthetic partner demographic, pricing, transaction,
risk, and compliance data.

## Business Objective

Business users often need quick answers about partner demographics, pricing tiers, transaction growth, revenue, margins, and regional distribution. However, this information is usually stored in structured databases that require SQL knowledge.

The objective of this project is to create a controlled Generative AI assistant that improves access to partner intelligence while reducing hallucination risk through SQL validation and citation auditing.

## Dataset Source and Licence

The dataset used in this project is fully synthetic and created for academic capstone purposes. It does not contain real company, partner, customer, pricing, or confidential information.

The project includes both raw and processed data.

### Raw Data

| File | Description |
|---|---|
| partners.csv | Partner demographic and master profile data |
| partner_pricing.csv | Partner-level pricing assignments and negotiated pricing values |
| pricing_plans.csv | Pricing plan reference table |
| pricing_exceptions.csv | Pricing exception requests and approval status |
| monthly_partner_metrics.csv | Monthly transaction, volume, revenue, margin, approval, and growth metrics |
| partner_segments.csv | Partner segmentation output and segment explanation |

### Processed Data

| File | Description |
|---|---|
| partner_master_clean.csv | Cleaned partner master profile data |
| partner_pricing_clean.csv | Cleaned partner pricing data |
| partner_metrics_clean.csv | Cleaned monthly partner metrics |
| partner_current_preview_1000.csv | Joined 1,000-record preview sample for demo and inspection |
| phase3_validation_summary.csv | Validation summary output |
| partnerlens_phase3_validated_dataset.xlsx | Validated Excel workbook with datasets, summary, and sample outputs |

Licence: Academic use only.

## Repository Structure

```text
partnerlens-copilot/
├── data/
│   ├── raw/
│   ├── processed/
│   └── data_dictionary.md
├── configs/
│   ├── config.yaml
│   └── schema_metadata.json
├── notebooks/
├── src/
├── prompts/
├── docs/
├── tests/
├── assets/
├── README.md
├── requirements.txt
└── .gitignore
```
## Installation Instructions

Clone the repository:

```bash
git clone https://github.com/m-ashir-siraj/partnerlens-copilot.git
cd partnerlens-copilot
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment.

For Windows:

```bash
venv\Scripts\activate
```

For Mac/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Execution Steps

Validate processed files:

```bash
python src/data_preparation.py
```

Create the SQLite database:

```bash
python src/database_setup.py
```

Run the baseline application:

```bash
streamlit run src/app.py
```

Run tests:

```bash
pytest tests/
``````

## Supporting Notebooks
| Notebook | Purpose |
|---|---|
| Data_Inventory_and_Validation.ipynb | Data inventory and validation |
| SQL_Baseline_PartnerLens.ipynb | Canonical SQLite tables and baseline SQL |
| Citation_Auditor_Guardrails.ipynb | Citation and grounding guardrails |
| PartnerLens_Assistant_Prototype.ipynb | End-to-end modular workflow |
| Formal_Evaluation_PartnerLens.ipynb | Final metrics and failure analysis |                                       |

The notebooks are supporting artefacts. The modular implementation used for execution is stored in the ```text src/``` folder.

## Baseline Workflow
```text
User Question
      ↓
PartnerLens Copilot Interface
      ↓
Schema and Data Dictionary Context
      ↓
SQL Generator / Query Planner
      ↓
SQL Validator
      ↓
SQLite Partner Database
      ↓
Query Results
      ↓
Answer Generator
      ↓
Citation Auditor
      ↓
Final Answer with Source Fields
```
## Final Evaluation Results

| Metric | Result |
|---|---:|
| Evaluation cases | 8 |
| Routing accuracy | 100.0% |
| Intent accuracy | 100.0% |
| Source-table consistency | 100.0% |
| SQL validation pass rate | 100.0% |
| Query execution success rate | 100.0% |
| Answer-generation rate | 100.0% |
| Citation-audit pass rate | 100.0% |
| Unsupported-question rejection rate | 100.0% |
| End-to-end case pass rate | 100.0% |

Detailed results:
- `artifacts/evaluation/README.md`
- `artifacts/evaluation/formal_evaluation_metrics.csv`
- `artifacts/evaluation/formal_evaluation_case_results.csv`
- `artifacts/evaluation/formal_evaluation_failure_analysis.csv`

## Final Implementation

The final version of PartnerLens Copilot delivers a modular, reproducible, and citation-audited natural-language-to-SQL solution for partner pricing, demographic, and transaction intelligence.

The implementation includes:

* A synthetic multi-table partner dataset designed to represent enterprise partner information without exposing confidential data.
* Cleaned, processed, and validated datasets with supporting validation outputs.
* A documented data dictionary and schema metadata.
* A reproducible SQLite database creation workflow.
* Repository-relative paths so notebooks can run locally or in a cloned Google Colab environment without requiring Google Drive.
* Consistent SQLite table names across notebooks and Python source modules:

  * `partners`
  * `partner_pricing`
  * `monthly_partner_metrics`
  * `partner_current_preview`
* A natural-language-to-SQL query-generation layer.
* Schema-aware query and prompt handling.
* A SQL validation layer that restricts execution to approved read-only queries.
* A controlled query-execution layer for the PartnerLens SQLite database.
* Business-friendly answer generation based on returned query results.
* Record-level citation auditing that checks cited partner identifiers, source tables, missing citations, and fabricated citations.
* Handling for valid results, empty result sets, unsupported questions, and malformed responses.
* A Streamlit interface for end-to-end demonstration.
* Modular Python components covering data preparation, database setup, SQL generation, SQL validation, query execution, answer generation, citation auditing, and application orchestration.
* Supporting notebooks for data validation, SQL baselining, citation guardrails, assistant prototyping, and formal evaluation.
* Automated tests and evaluation cases covering successful and unsuccessful scenarios.
* Repository-based evaluation artefacts and computed performance metrics.
* Architecture diagrams, workflow documentation, deployment guidance, and final-submission evidence.

## Phase 8 Improvements Completed

The following enhancements were implemented after the Version 1 baseline review:

* Expanded SQL-generation coverage for additional supported business-question patterns.
* Improved schema-aware processing to reduce invalid table and column references.
* Strengthened citation auditing through record-level identifier verification, source-table checks, fabricated-citation detection, and machine-readable audit results.
* Added more formal evaluation metrics and failure analysis.
* Surfaced evaluation results directly within the repository.
* Improved the Streamlit user interface and presentation of generated SQL, query results, business answers, and citation-audit outcomes.
* Added clearer error handling for ambiguous, unsupported, unsafe, and empty-result questions.
* Expanded positive, negative, and edge-case test coverage.
* Removed mandatory Google Drive dependencies from the notebooks.
* Standardized table names across the notebooks, SQLite database, and `src` modules.
* Added clearer roadmap justifications, final documentation, setup instructions, and local execution guidance.
* Added repository-based notebook outputs and evaluation artefacts to improve reproducibility and reviewer visibility.

## Current Limitations

Although the final implementation demonstrates the complete PartnerLens workflow, several limitations remain:

* The dataset is synthetic and smaller than a production-scale enterprise partner database.
* SQL generation supports a controlled set of business-question patterns and is not intended to interpret every possible natural-language request.
* The citation auditor performs structural and record-level grounding checks; it does not provide full semantic entailment or independent verification of every natural-language claim.
* Complex questions requiring multiple dependent queries, advanced calculations, forecasting, or multi-step reasoning may require a more sophisticated query planner.
* The current implementation uses SQLite and would require additional security, authentication, authorization, and performance controls before enterprise deployment.
* The Streamlit interface is intended for capstone demonstration and has not been optimized for production-scale usage.
* Evaluation is performed against a defined synthetic test set and may not represent every real-world user question or data-quality condition.
* Production deployment would require integration with approved enterprise data sources, access controls, monitoring, audit logging, and organizational governance standards.

## Final Submission Status

This repository represents the final submission of the PartnerLens Copilot capstone project.

The completed solution demonstrates:

* Synthetic raw and processed partner data.
* Data-quality validation and validation artefacts.
* Schema metadata and a documented data dictionary.
* Reproducible SQLite database setup.
* Modular Python source code.
* Structured prompt and configuration files.
* Natural-language-to-SQL generation.
* SQL safety validation.
* Controlled query execution.
* Business-readable answer generation.
* Record-level citation auditing.
* End-to-end Streamlit application integration.
* Reproducible supporting notebooks.
* Automated tests and formal evaluation.
* Computed performance metrics and failure analysis.
* Architecture and workflow documentation.
* Final setup, execution, demonstration, and deployment guidance.

Together, these components provide an end-to-end demonstration of how generative AI can make structured partner information more accessible while reducing hallucination risk through controlled SQL execution, explicit source attribution, and citation auditing.

