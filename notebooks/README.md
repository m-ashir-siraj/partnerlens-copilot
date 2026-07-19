# PartnerLens Notebooks

These notebooks are repository-native final-submission artifacts. They do not require Google Drive and use project-relative paths.

## Execution order

1. `Data_Inventory_and_Validation.ipynb`
2. `SQL_Baseline_PartnerLens.ipynb`
3. `Citation_Auditor_Guardrails.ipynb`
4. `PartnerLens_Assistant_Prototype.ipynb`
5. `Formal_Evaluation_PartnerLens.ipynb`

## Setup

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m notebook
```

Open the notebook from the `notebooks/` folder and run **Kernel → Restart Kernel and Run All Cells**.

## Generated evidence

The notebooks write computed evidence to:

- `artifacts/notebook_outputs/`
- `artifacts/evaluation/`

Commit those outputs for the final submission so evaluators can inspect the metrics without rerunning every notebook.

## Canonical table names

The notebooks and `src` modules consistently use:

- `partners`
- `partner_pricing`
- `monthly_partner_metrics`
- `partner_current_preview`

CSV filenames remain implementation details and are mapped to these canonical SQLite table names.
