# Baseline Evaluation

## Evaluation Objective

The goal of the baseline evaluation is to confirm that PartnerLens Copilot can generate safe SQL, execute the query, return relevant results, and produce an answer with source-field support.

## Sample Evaluation Questions

| Test Case | User Question | Expected Table | Expected Behavior |
|---|---|---|---|
| 1 | Show me partners in Arizona with transaction growth above 20% | partner_current_preview | Return AZ partners with txn_growth_pct greater than 20 |
| 2 | Show top partners by payment volume | partner_current_preview | Return highest-volume partners |
| 3 | Show pricing information | partner_pricing | Return partner pricing records |
| 4 | Show partner risk information | partners | Return risk, KYC, and PCI fields |

## Evaluation Criteria

| Metric | Description |
|---|---|
| SQL validity | Generated SQL is syntactically valid |
| SQL safety | SQL is SELECT-only and blocks unsafe commands |
| Query execution | SQL runs against SQLite without manual modification |
| Answer relevance | Answer reflects the query result |
| Citation support | Answer includes source-field or query-result support |
| Reproducibility | Evaluator can run the project using README steps |

## Baseline Result

The Version 1 baseline demonstrates a modular workflow using synthetic data, SQL generation, SQL validation, SQLite execution, answer generation, and citation auditing. Further improvements will be added in the final submission.
  
