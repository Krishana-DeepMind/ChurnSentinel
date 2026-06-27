# Tool Specification: `query_crm_by_email`

## Description
Looks up a customer record in `crm.json` by exact email match. Returns a "not found" result if no match is located.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "email": {
      "type": "string",
      "description": "The exact sender email address to look up in the CRM database."
    }
  },
  "required": ["email"]
}
```

## Output Schema
```json
{
  "found": "boolean",
  "record": {
    "company_name": "string",
    "annual_revenue": "number",
    "days_until_renewal": "integer",
    "account_manager_email": "string",
    "account_manager_name": "string",
    "tier": "string"
  }
}
```
*(If no matching record is found, `found` is `false` and `record` is `null`.)*
