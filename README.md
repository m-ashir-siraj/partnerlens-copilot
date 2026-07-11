# PartnerLens Copilot: Citation-Audited Partner Pricing & Demographic Intelligence Assistant

## Project Overview

PartnerLens Copilot is a Version 1 baseline Generative AI solution that allows business users to ask natural-language questions about synthetic partner pricing, demographic, transaction, and segmentation data.

The system converts a user question into SQL, validates the SQL, queries a SQLite database, generates a business-friendly answer, and audits the final response for source-field support.

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
| Notebook                              | Purpose                                                                                            |
| ------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Data_Inventory_and_Validation.ipynb   | Documents data inventory, data quality checks, and validation of the synthetic PartnerLens dataset |
| SQL_Baseline_PartnerLens.ipynb        | Demonstrates SQLite database creation and baseline SQL query testing                               |
| Citation_Auditor_Guardrails.ipynb     | Demonstrates citation-auditing logic and guardrail checks                                          |
| PartnerLens_Assistant_Prototype.ipynb | Demonstrates the end-to-end assistant prototype workflow                                           |

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
## Current Implementation Status
   * Version 1 baseline includes:
   * Synthetic multi-table partner dataset
   * Processed and validated data files
* Schema metadata
* Data dictionary
* SQLite database creation workflow
* Natural-language-to-SQL baseline design
* SQL validation layer
* Query execution layer
* Business answer generation
* Citation audit logic
* Supporting notebooks
* Initial evaluation examples
* Modular repository structure

## Known Limitations
* Dataset is synthetic and smaller than a real enterprise partner database.
* SQL generation currently supports a limited set of question patterns.
* Citation auditing is rule-based in the baseline version.
* Complex multi-step analytical questions may require additional query planning.
* Some notebooks may include development-environment references from Colab or Google Drive.
* The interface is basic and designed for baseline demonstration.

## Planned Improvements for Final Submission
* Expand SQL generation logic.
* Add richer schema-aware prompt handling.
* Improve citation auditing with claim-level evidence checks.
* Add more formal evaluation metrics.
* Improve Streamlit user interface.
* Add better error handling for ambiguous questions.
* Add more test cases.
* Improve final documentation and deployment instructions.

## Mid-Submission Baseline Notes

This repository represents the Version 1 baseline submission for the PartnerLens Copilot capstone project.

The current baseline demonstrates:
* Raw synthetic data
* Processed clean datasets
* Validation artefacts
* SQLite database setup
* Modular Python source code
* Prompt files
* Supporting notebooks
* Baseline evaluation documentation
* Planned enhancements for the final submission
