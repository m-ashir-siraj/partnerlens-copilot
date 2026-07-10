# Processed Data

This folder contains the cleaned, validated, and analysis-ready outputs for the PartnerLens Copilot baseline project.

## Files

| File | Description |
|---|---|
| partner_master_clean.csv | Cleaned partner master profile data |
| partner_pricing_clean.csv | Cleaned partner pricing assignment data |
| partner_metrics_clean.csv | Cleaned monthly partner metrics |
| partner_current_preview_1000.csv | Joined preview sample containing 1,000 current partner records for quick inspection and demo use |
| phase3_validation_summary.csv | Validation summary showing data-quality and readiness checks |
| partnerlens_phase3_validated_dataset.xlsx | Excel workbook containing validated datasets, validation summary, and sample query output tabs |

## Processed Data Notes

The processed files are derived from the synthetic raw data files in `data/raw/`.

These files are included to make the baseline solution easier to evaluate and reproduce.

The SQLite database can be created from the processed CSV files by running:

```bash
python src/database_setup.py
