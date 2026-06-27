# Test Scenario: Escalation and Watchlist File Outputs

This document defines schema compliance validation for files written by the MCP server tools.

## Scenario 1: Escalation JSON Output Schema
- **Target Folder:** `data/outbox/escalations/`
- **Filename Pattern:** `escalation_{ticket_id}_{timestamp}.json`
- **Required Fields:**
  - `ticket_id`: string
  - `company_name`: string
  - `annual_revenue`: number
  - `days_until_renewal`: integer
  - `account_manager_email`: string
  - `churn_risk_score`: number
  - `rationale`: string
  - `recommended_action`: string
  - `escalated_at`: string (ISO datetime)

## Scenario 2: Watchlist JSON Output Schema
- **Target Folder:** `data/outbox/watchlist/`
- **Filename Pattern:** `watchlist_{ticket_id}_{timestamp}.json`
- **Required Fields:**
  - `ticket_id`: string
  - `company_name`: string
  - `churn_risk_score`: number
  - `rationale`: string
  - `logged_at`: string (ISO datetime)
