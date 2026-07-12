# Notebooks

This folder contains supporting Python notebooks for the PartnerLens Copilot baseline submission.

The notebooks demonstrate data validation, SQLite baseline development, citation-auditor guardrails, and the prototype assistant workflow.

## Notebook Execution Order

| Order | Notebook | Purpose |
|---:|---|---|
| 1 | Data_Inventory_and_Validation.ipynb | Performs data inventory checks, validation checks, and confirms readiness of the raw and processed synthetic datasets |
| 2 | SQL_Baseline_PartnerLens.ipynb | Builds the SQLite baseline, loads processed data into database tables, and demonstrates sample SQL queries |
| 3 | Citation_Auditor_Guardrails.ipynb | Demonstrates citation-auditing logic, guardrails, and evidence checks for generated answers |
| 4 | PartnerLens_Assistant_Prototype.ipynb | Demonstrates the end-to-end PartnerLens assistant prototype workflow |
| 5 | Formal_Evaluation_PartnerLens.ipynb | Formally evaluates PartnerLens against the SQL baseline using execution, answer-quality, citation, safety, and error-analysis metrics|

## Notes

These notebooks are included as supporting artefacts for evaluator review.

The main reusable project implementation is stored in the `src/` folder. The notebooks should not be treated as the only implementation of the project.

Some notebook cells may reference Google Colab or Google Drive paths from the development environment. For repository execution, use the project-relative paths documented in the main `README.md`.
