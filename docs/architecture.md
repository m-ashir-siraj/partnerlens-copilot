# Architecture

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

## Components
|Component	|Purpose
|User Interface	|Allows user to ask natural-language questions
|SQL Generator	|Converts questions into SQL
|SQL Validator	|Blocks unsafe or unsupported SQL
|SQLite Database	|Stores processed synthetic partner data
|Query Executor	|Runs validated SQL
|Answer Generator	|Converts results into business response
|Citation Auditor	|Checks whether response is supported by source fields
