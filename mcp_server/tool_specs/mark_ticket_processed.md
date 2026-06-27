# Tool Specification: `mark_ticket_processed`

## Description
Moves a ticket file from the `data/tickets/inbox/` directory to `data/tickets/processed/` so it is not processed on subsequent runs. This should be the final action taken on every ticket.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "ticket_id": { "type": "string" }
  },
  "required": ["ticket_id"]
}
```

## Output Schema
```json
{
  "success": "boolean",
  "new_path": "string"
}
```
