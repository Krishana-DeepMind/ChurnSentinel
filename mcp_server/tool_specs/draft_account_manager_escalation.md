# Tool Specification: `draft_account_manager_escalation`

## Description
Writes a structured escalation file to `data/outbox/escalations/` for high-risk accounts (`CODE_RED`). It must never overwrite an existing file; filenames should be uniquely derived from `ticket_id` and a timestamp.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "ticket_id": { "type": "string" },
    "company_name": { "type": "string" },
    "annual_revenue": { "type": "number" },
    "days_until_renewal": { "type": "integer" },
    "account_manager_email": { "type": "string" },
    "churn_risk_score": { "type": "number" },
    "rationale": { "type": "string" },
    "recommended_action": { "type": "string" }
  },
  "required": [
    "ticket_id",
    "company_name",
    "annual_revenue",
    "days_until_renewal",
    "account_manager_email",
    "churn_risk_score",
    "rationale",
    "recommended_action"
  ]
}
```

## Output Schema
```json
{
  "success": "boolean",
  "file_path": "string"
}
```
