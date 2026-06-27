# Tool Specification: `read_new_tickets`

## Description
Scans `data/tickets/inbox/` for `.txt` files not yet marked processed, parses each into a structured object, and returns the list. Does not delete or move files.

## Input Schema
```json
{}
```

## Output Schema
```json
[
  {
    "ticket_id": "string (filename without extension, e.g. ticket_001)",
    "sender_email": "string (extracted from body)",
    "raw_text": "string (full email text content)",
    "file_path": "string (absolute file path)"
  }
]
```
