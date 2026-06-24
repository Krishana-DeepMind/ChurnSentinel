# Test Scenario: Churn Risk Scoring

This document details risk scoring test scenarios verifying interaction effects between revenue, renewal timing, and emotional/linguistic cues.

## Scenario 1: Polite low-value cosmetic issue (ticket_001.txt)
- **Inputs:**
  - Sentiment: calm, frustration score 20, no cancellation language.
  - CRM: ARR $1,200, 250 days to renewal.
- **Expected Output:**
  - Churn Risk Score: low (< 35)
  - Risk Tier: `LOW`
  - Action: No outbox actions drafted. Just mark processed.

## Scenario 2: Angry complaint from enterprise account near renewal (ticket_002.txt)
- **Inputs:**
  - Sentiment: angry/hostile, frustration score 85, explicit competitor evaluation and cancellation threat.
  - CRM: ARR $250,000, 12 days to renewal.
- **Expected Output:**
  - Churn Risk Score: extremely high (>= 75)
  - Risk Tier: `CODE_RED`
  - Action: Draft escalation file in outbox.

## Scenario 3: Calm but serious competitor inquiry from mid/high value account (ticket_003.txt)
- **Inputs:**
  - Sentiment: calm, frustration score 15, explicit cancellation/competitor evaluation signal.
  - CRM: ARR $450,000, 60 days to renewal.
- **Expected Output:**
  - Churn Risk Score: high (>= 75)
  - Risk Tier: `CODE_RED` (or `WATCH` depending on threshold tuning, but strictly MUST NOT be `LOW`).
  - Action: Draft escalation file or log watchlist.

## Scenario 4: Highly angry billing discrepancy from small account (ticket_004.txt)
- **Inputs:**
  - Sentiment: angry, frustration score 90, no cancellation language.
  - CRM: ARR $2,500, 180 days to renewal.
- **Expected Output:**
  - Churn Risk Score: medium (< 75)
  - Risk Tier: `WATCH` or `LOW` (strictly MUST NOT be `CODE_RED`).
  - Action: Watchlist log entry or mark processed.
