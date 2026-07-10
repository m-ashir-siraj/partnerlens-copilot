# Data Dictionary

This document describes the synthetic PartnerLens dataset used for the capstone baseline solution.

## Dataset Overview

The dataset contains synthetic partner demographic, pricing, transaction, exception, and segmentation data. It was created for academic capstone use and does not contain real company or partner information.

## Processed Dataset Files

| File | Rows | Purpose |
|---|---:|---|
| partner_master_clean.csv | 5,000 | Cleaned partner master table |
| partner_pricing_clean.csv | 5,000 | Cleaned partner pricing table |
| partner_metrics_clean.csv | 120,000 | Cleaned monthly partner metrics table |
| partner_current_preview_1000.csv | 1,000 | Joined preview sample for demo and inspection |
| phase3_validation_summary.csv | 13 | Data validation summary |
| partnerlens_phase3_validated_dataset.xlsx | Workbook | Validated dataset workbook with summary and sample query outputs |

## SQLite Table Mapping

| Processed File | SQLite Table |
|---|---|
| partner_master_clean.csv | partners |
| partner_pricing_clean.csv | partner_pricing |
| partner_metrics_clean.csv | monthly_partner_metrics |
| partner_current_preview_1000.csv | partner_current_preview |

## Main Join Key

The main join key across partner-level tables is:

```text
partner_id
```

## Important Notes
   * All records are synthetic.
   * State values use abbreviations such as AZ, CA, TX, and NY.
   * The dataset is intended for academic demonstration only.
