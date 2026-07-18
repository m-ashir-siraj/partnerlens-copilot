# PartnerLens File-to-Table Mapping

| Source or processed file | SQLite table | Purpose |
|---|---|---|
| partner_master_clean.csv | partners | Partner demographic, status, risk and compliance information |
| partner_pricing_clean.csv | partner_pricing | Partner pricing assignments, negotiated fees and exceptions |
| partner_metrics_clean.csv | monthly_partner_metrics | Monthly transaction, volume, growth, revenue and margin metrics |
| partner_current_preview_1000.csv | partner_current_preview | Current joined partner-level preview used for common demonstration queries |

## Canonical Naming Rule

All SQL queries, notebooks, prompts, evaluations and source modules must use:

- `partners`
- `partner_pricing`
- `monthly_partner_metrics`
- `partner_current_preview`

The names `partner_master` and `partner_metrics` may describe Python DataFrames or processed filenames, but they must not be used as SQLite table names.
