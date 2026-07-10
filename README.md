# PartnerLens Copilot: Citation-Audited Partner Pricing & Demographic Intelligence Assistant

## Project Overview

PartnerLens Copilot is a Version 1 baseline Generative AI solution that allows business users to ask natural-language questions about synthetic partner pricing, demographic, and transaction data.

The system converts a user question into SQL, validates the SQL, queries a SQLite database, generates a business-friendly answer, and audits the final response for source-field citations.

## Business Objective

Business users often need quick answers about partner demographics, pricing tiers, transaction growth, and regional distribution. However, this information is usually stored in structured databases that require SQL knowledge.

The objective of this project is to create a controlled Generative AI assistant that improves access to partner intelligence while reducing hallucination risk through SQL validation and citation auditing.

## Dataset Source and Licence

The dataset used in this project is fully synthetic and created for academic capstone purposes. It does not contain real company, partner, customer, pricing, or confidential information.

Licence: Academic use only.

## Repository Structure

```text
partnerlens-copilot/
├── data/
│   ├── raw/
│   ├── processed/
│   └── data_dictionary.md
├── src/
├── configs/
├── prompts/
├── notebooks/
├── docs/
├── tests/
├── assets/
├── README.md
├── requirements.txt
└── .gitignore
```

## Installation Instructions

Cloning the repository:

```bash
git clone https://github.com/m-ashir-siraj/partnerlens-copilot.git
cd partnerlens-copilot
```

Creating a virtual environment:

```bash
python -m venv venv
```

Activating the virtual environment.

For Windows:

```bash
venv\Scripts\activate
```

For Mac/Linux:

```bash
source venv/bin/activate
```

Installing dependencies:

```bash
pip install -r requirements.txt
```

## Execution Steps
### Data Preparation
```bash
python src/data_preparation.py
```
### SQLite database creation
```bash
python src/database_setup.py
```
### Running the baseline application
```bash
streamlit run src/app.py
```
### Runing Tests
```bash
pytest tests/
```
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

### Version 1 baseline includes:
1. Synthetic partner dataset
2. Data dictionary
3. SQLite database workflow
4. Natural-language-to-SQL baseline design
5. SQL validation layer
6. Query execution layer
7. Business answer generation
8. Citation audit logic
9. Initial evaluation examples
10. Modular repository structure

### Known Limitations
1. Dataset is synthetic and smaller than a real enterprise partner database.
2. SQL generation currently supports a limited set of question patterns.
3. Citation auditing is rule-based in the baseline version.
4. Complex multi-step analytical questions may require additional query planning.
5. The interface is basic and designed for baseline demonstration.

### Planned Improvements for Final Submission
1. Expanded synthetic dataset
2. Improved SQL generation
3. More advanced SQL validation
4. Better citation scoring
5. More formal evaluation metrics
6. Enhanced Streamlit interface
7. Additional unit tests
8. Improved error handling for ambiguous questions


```text
Updated README for baseline submission
