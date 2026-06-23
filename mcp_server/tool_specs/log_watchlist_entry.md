# Tool Specification: `log_watchlist_entry`

## Description
Writes a lighter-weight log record to `data/outbox/watchlist/` for medium-risk accounts (`WATCH`) that do not require an immediate escalation but should be reviewed. Filenames should be uniquely derived from `ticket_id` and a timestamp.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "ticket_id": { "type": "string" },
    "company_name": { "type": "string" },
    "churn_risk_score": { "type": "number" },
    "rationale": { "type": "string" }
  },
  "required": [
    "ticket_id",
    "company_name",
    "churn_risk_score",
    "rationale"
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
