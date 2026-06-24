# Test Scenario: CRM Lookup

This document lists test scenarios to verify customer lookup operations.

## Scenario 1: Exact Email Match
- **Input:** `bob.jones@megacorp.com`
- **Expected Action:** Query `crm.json` and locate Bob Jones's record.
- **Expected Output:** `found` is true, and the JSON record details (MegaCorp Inc., $250k ARR, 12 days to renewal) are returned.

## Scenario 2: Unknown Customer Graceful Handle
- **Input:** `doesnotexist@unknown.com`
- **Expected Action:** Query `crm.json` and return a clean "not found" status rather than crashing.
- **Expected Output:** `found` is false, and `record` is null.

## Scenario 3: Case-Insensitivity Check
- **Input:** `BOB.JONES@MEGACORP.COM`
- **Expected Action:** Query matching should be case-insensitive.
- **Expected Output:** `found` is true, record is located successfully.
