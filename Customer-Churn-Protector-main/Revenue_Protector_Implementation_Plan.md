# The Revenue Protector — Churn Risk & Rescue Agent
## Implementation Blueprint for Kaggle "Vibecoding Agents Capstone" (Agents for Business Track)

**Document purpose:** This is an architectural specification, not code. It is intended to be handed to a developer (or developer-agent) who will implement the system exactly as described. No Python, no pseudocode-as-code — only structure, schemas, contracts, and sequencing.

---

## 1. System Architecture

### 1.1 Actors and Components

| Component | Role |
|---|---|
| **User** | Triggers a "run inbox check" event (manually, via CLI command, or on a schedule). Receives the final escalation report. |
| **Orchestrator Agent** | The only component that talks to the User. Owns the workflow state machine. Delegates work to sub-agents, never does sentiment or risk math itself. |
| **Sentiment Analyst Sub-Agent** | Receives raw ticket text only. Has no knowledge of CRM data. Returns a structured emotional-risk judgment per ticket. |
| **Risk Assessor Sub-Agent** | Receives the Sentiment Analyst's output plus CRM facts (revenue, days-to-renewal). Computes the Churn Risk Score and the escalation recommendation. Has no access to raw ticket text — only structured inputs — to keep its reasoning auditable and isolated from prompt-injection in ticket content. |
| **Custom File System / CRM MCP Server** | The only component that touches disk. Exposes a fixed set of tools (Section 4). Neither sub-agent reads files directly — everything is mediated through MCP tool calls, which is what makes the "local-only, no PII leakage" claim auditable. |

### 1.2 Data Flow (Sequence)

1. **User → Orchestrator:** "Run the daily churn check."
2. **Orchestrator → MCP Server:** Calls `read_new_tickets` to retrieve all unprocessed tickets from the inbox directory.
3. **MCP Server → Orchestrator:** Returns a list of ticket objects (id, sender_email, raw_text, received_at).
4. **Orchestrator → Sentiment Analyst (per ticket, looped):** Sends only `raw_text`. Asks for a structured sentiment verdict.
5. **Sentiment Analyst → Orchestrator:** Returns `{sentiment_label, frustration_score, key_phrases, churn_signals_detected}`.
6. **Orchestrator → MCP Server:** Calls `query_crm_by_email` using `sender_email` extracted from the ticket.
7. **MCP Server → Orchestrator:** Returns CRM record `{company_name, annual_revenue, days_until_renewal, account_manager_email}` or a "not found" result.
8. **Orchestrator → Risk Assessor:** Passes the sentiment verdict + CRM record (never the raw email body). Asks for a Churn Risk Score and an action recommendation.
9. **Risk Assessor → Orchestrator:** Returns `{churn_risk_score, risk_tier, rationale, recommended_action}`.
10. **Orchestrator (decision point):**
    - If `risk_tier == "CODE_RED"` → calls MCP tool `draft_account_manager_escalation` to write an escalation file to the outbox.
    - If `risk_tier == "WATCH"` → calls MCP tool `log_watchlist_entry` (see Section 4) instead of escalating.
    - If `risk_tier == "LOW"` → calls MCP tool `mark_ticket_processed` only, no escalation.
11. **MCP Server → Orchestrator:** Confirms write success + file path.
12. **Orchestrator → User:** Final summary report: tickets processed, escalations raised, watchlist entries, and a one-line rationale per case.

### 1.3 Why This Is a Genuine Multi-Agent System (Not a Single Prompt)

- **Separation of concerns enforces honesty:** The Risk Assessor cannot "see" emotionally charged language directly — it only sees the Sentiment Analyst's structured output. This prevents an angry-but-low-value email from accidentally inflating the financial risk score through raw emotional language bleeding into the financial reasoning step.
- **Tool-mediated isolation enforces the privacy claim:** Because all disk/CRM access goes through one MCP server with fixed tool contracts, you can demonstrate in your Kaggle writeup that no agent has unmediated file access, and no data ever leaves localhost.
- **Orchestrator as state machine, not a thinker:** It routes and aggregates; it does not reinterpret ticket content or CRM numbers itself. This makes the audit trail clean — every escalation decision can be traced to two specific sub-agent outputs.

---

## 2. Project File Structure

```
revenue-protector/
├── README.md
├── requirements.txt
├── .env.example                      # placeholder only — no real keys, since budget is $0.00
│
├── config/
│   └── risk_thresholds.json          # tunable constants: CODE_RED cutoff, WATCH cutoff, weighting
│
├── data/
│   ├── crm/
│   │   └── crm.json                  # the synthetic CRM "database"
│   │
│   ├── tickets/
│   │   ├── inbox/                    # unprocessed .txt tickets land here
│   │   │   ├── ticket_001.txt
│   │   │   ├── ticket_002.txt
│   │   │   ├── ticket_003.txt
│   │   │   └── ticket_004.txt
│   │   └── processed/                # MCP server moves tickets here once handled
│   │
│   └── outbox/
│       ├── escalations/              # CODE_RED account-manager escalation drafts
│       └── watchlist/                # WATCH-tier log entries
│
├── mcp_server/
│   ├── server_manifest.md            # documents tool names/schemas (mirrors Section 4 below)
│   └── tool_specs/                   # one spec file per tool, no code — just I/O contract
│       ├── read_new_tickets.md
│       ├── query_crm_by_email.md
│       ├── draft_account_manager_escalation.md
│       ├── log_watchlist_entry.md
│       └── mark_ticket_processed.md
│
├── agents/
│   ├── orchestrator/
│   │   └── system_prompt.md
│   ├── sentiment_analyst/
│   │   └── system_prompt.md
│   └── risk_assessor/
│       └── system_prompt.md
│
├── logs/
│   └── run_history/                  # one JSON per run: full decision trail for demo/audit
│
└── tests/
    ├── test_crm_lookup.md             # test scenarios described, not implemented
    ├── test_risk_scoring.md
    └── test_escalation_format.md
```

**Notes for the implementer:**
- `data/`, `logs/`, and the `outbox` subfolders should be git-ignored except for the seed synthetic files, so the repo always resets to a clean demo state.
- `mcp_server/tool_specs/` is documentation, not code — Opus will generate the actual server implementation from these specs, but the specs themselves should be committed as the source of truth.

---

## 3. Synthetic Data Schemas

### 3.1 Mock Support Tickets (`data/tickets/inbox/*.txt`)

Each ticket is a loosely formatted plain-text file simulating a forwarded email. Deliberately inconsistent formatting (real inboxes are messy) — do not make these clean JSON.

**ticket_001.txt — Trivial bug, low-value client**
- From a small client with low ARR.
- Tone: mildly annoyed but polite, reporting a cosmetic UI bug (e.g., a button is misaligned).
- No churn language, no renewal urgency.
- Purpose: should be scored LOW risk even though it's a "complaint," proving the system isn't just keyword-matching on "annoyed."

**ticket_002.txt — Angry complaint, high-value client near renewal**
- From a client with high ARR and very few days left until renewal.
- Tone: openly frustrated, references repeated unresolved issues, hints at "looking at alternatives," uses words like "unacceptable" and "third time asking."
- Purpose: the canonical CODE_RED case — high emotional signal + high revenue + renewal imminent.

**ticket_003.txt — Calm but explicit cancellation threat, mid-value client, mid-range renewal window**
- Tone: notably calm and businesslike — no angry language at all — but explicitly states they are "evaluating other vendors" and asks about contract termination terms.
- Purpose: tests whether the system can catch churn risk that is *not* expressed via anger (a calm, rational cancellation threat). This guards against an agent that equates "frustration_score" with "churn risk" — they are related but not identical signals, and the Risk Assessor's prompt must treat explicit churn language as its own signal independent of tone.

**ticket_004.txt — Genuinely angry but low-stakes, low-value client, renewal far away**
- Tone: very angry, all-caps in places, about a minor billing discrepancy.
- Low ARR, renewal months away.
- Purpose: a high-frustration but low-financial-risk case — should land as WATCH or LOW, not CODE_RED, proving revenue/timing gates the outcome rather than tone alone.

Each `.txt` file should informally include, somewhere in the body: a sender name, a sender email address (matching an entry in `crm.json`), a subject-like first line, and a few paragraphs of free-text complaint. No fixed structure — simulate copy-pasted email bodies.

### 3.2 CRM Database Schema (`data/crm/crm.json`)

A JSON array of customer records. Exact field list:

```
[
  {
    "email": "string — must exactly match the sender address used in ticket text",
    "company_name": "string",
    "annual_revenue": "number — Annual Recurring Revenue (ARR) in USD",
    "days_until_renewal": "integer — can be negative if already past due, to test edge cases",
    "account_manager_email": "string — the internal AM who should receive escalations",
    "account_manager_name": "string",
    "tier": "string — e.g. 'Enterprise' | 'Mid-Market' | 'SMB', for human-readable context only"
  },
  ...
]
```

Seed the file with one record per ticket sender (4 records minimum) plus 2–3 extra "decoy" customers not referenced by any ticket, to prove `query_crm_by_email` does real lookups rather than the agent hallucinating data.

---

## 4. MCP Tool Definitions

All tools are exposed by a single local MCP server process. Each tool spec below should become its own file under `mcp_server/tool_specs/`.

### 4.1 `read_new_tickets`
- **Description:** Scans `data/tickets/inbox/` for `.txt` files not yet marked processed, parses each into a structured object, and returns the list. Does not delete or move files (that's `mark_ticket_processed`'s job).
- **Input schema:** `{}` (no arguments — always reads the full inbox).
- **Output schema:** `[{ "ticket_id": string, "sender_email": string, "raw_text": string, "file_path": string }]`

### 4.2 `query_crm_by_email`
- **Description:** Looks up a single customer record in `crm.json` by exact email match. Returns a "not found" result rather than erroring if no match exists, so the agent has a defined path for unknown senders.
- **Input schema:** `{ "email": string }`
- **Output schema:** `{ "found": boolean, "record": { company_name, annual_revenue, days_until_renewal, account_manager_email, account_manager_name, tier } | null }`

### 4.3 `draft_account_manager_escalation`
- **Description:** Writes a structured escalation file to `data/outbox/escalations/`. This is the "Code Red" action. Must never overwrite an existing file for the same ticket — filenames should be uniquely derived from ticket_id + timestamp.
- **Input schema:** `{ "ticket_id": string, "company_name": string, "annual_revenue": number, "days_until_renewal": integer, "account_manager_email": string, "churn_risk_score": number, "rationale": string, "recommended_action": string }`
- **Output schema:** `{ "success": boolean, "file_path": string }`

### 4.4 `log_watchlist_entry`
- **Description:** Writes a lighter-weight record to `data/outbox/watchlist/` for medium-risk cases that don't warrant a full escalation but should be reviewed by a human within the week.
- **Input schema:** `{ "ticket_id": string, "company_name": string, "churn_risk_score": number, "rationale": string }`
- **Output schema:** `{ "success": boolean, "file_path": string }`

### 4.5 `mark_ticket_processed`
- **Description:** Moves a ticket file from `inbox/` to `processed/` so it is not re-evaluated on the next run. Should be the final action taken on every ticket regardless of risk tier.
- **Input schema:** `{ "ticket_id": string }`
- **Output schema:** `{ "success": boolean, "new_path": string }`

**Design note for the implementer:** every tool's output should include enough information that the Orchestrator never needs to re-read a file to "double check" something — this keeps file I/O entirely inside the MCP server boundary, which is the core of the security/privacy story for the capstone.

---

## 5. Multi-Agent Persona & Prompt Strategy

### 5.1 Orchestrator Agent

**Role:** Workflow conductor. Has access to all MCP tools but should call sentiment/risk reasoning out to the sub-agents rather than reasoning about tone or financial risk itself.

**Goal statement (for its system prompt):** Process every new ticket in the inbox exactly once per run; for each ticket, obtain a sentiment verdict and a risk verdict before taking any outbox action; never escalate or watchlist a ticket without both verdicts present; always call `mark_ticket_processed` last.

**Key behavioral constraints to encode in its prompt:**
- It must not invent CRM numbers — if `query_crm_by_email` returns `found: false`, it should still log the ticket (e.g., to watchlist with a "no CRM match" rationale) rather than skipping it silently.
- It must pass the Risk Assessor structured fields only, never the raw ticket text.
- It must summarize its run for the user in plain language at the end (tickets processed, escalations, watchlist items).

### 5.2 Sentiment Analyst Sub-Agent

**Role:** Pure linguistic/emotional reasoning, no business context.

**Goal statement:** Given raw ticket text only, produce a structured judgment of the sender's emotional state and any explicit signals of dissatisfaction or intent to leave — independent of who the sender is or what they pay.

**Required output fields:**
- `sentiment_label`: one of `calm`, `mildly_frustrated`, `angry`, `hostile`
- `frustration_score`: 0–100
- `churn_signals_detected`: boolean — true if the text contains explicit cancellation/competitor-evaluation language, regardless of tone (this is what catches ticket_003's calm-but-serious case)
- `key_phrases`: short list of the phrases that drove the verdict (for human auditability)

**Prompt instruction to emphasize:** explicitly tell this agent that calm language can still carry high churn signal, and angry language can be about something trivial — its job is to separate *emotional intensity* from *churn intent*, and report both, not collapse them into one number.

### 5.3 Risk Assessor Sub-Agent

**Role:** Combines sentiment verdict + CRM facts into a single actionable score. Never sees raw ticket text.

**Goal statement:** Given a structured sentiment verdict and a CRM record, compute a Churn Risk Score, assign a risk tier, and write a one-sentence rationale and a recommended next action.

**Reasoning approach to specify in its prompt (semantic, not hardcoded keyword math):**
- Treat `annual_revenue` and `days_until_renewal` as the financial-exposure axis, and `frustration_score` + `churn_signals_detected` as the dissatisfaction axis.
- Reason explicitly about interaction effects, not a fixed formula: e.g., high revenue + imminent renewal + explicit churn signal should dominate the decision even with only moderate frustration; conversely, high frustration with a distant renewal date and low revenue should rarely justify CODE_RED.
- Required output fields: `churn_risk_score` (0–100), `risk_tier` (`CODE_RED` | `WATCH` | `LOW`), `rationale` (1–2 sentences, referencing the specific revenue/timing/sentiment combination), `recommended_action` (a short instruction, e.g., "Account Manager should call within 24 hours and offer a renewal incentive call").
- The exact numeric thresholds for tiers should live in `config/risk_thresholds.json` (Section 2) so they're tunable without touching the prompt — but the agent should be instructed to use its judgment near the boundaries rather than treating thresholds as rigid cutoffs, which is the "agentic reasoning vs hardcoded keywords" story for the capstone judges.

---

## 6. Step-by-Step Execution Plan for Opus

1. **Scaffold the repository** exactly per the file structure in Section 2, including empty placeholder folders (`logs/run_history/`, `data/outbox/escalations/`, `data/outbox/watchlist/`, `data/tickets/processed/`).
2. **Write the synthetic data first.** Create `crm.json` per the schema in 3.2, then write the four `.txt` tickets per the personas in 3.1, making sure sender emails match CRM entries exactly.
3. **Document the MCP tool specs** as standalone markdown files under `mcp_server/tool_specs/`, matching Section 4 exactly (name, description, input schema, output schema) before writing any server code — this becomes the contract the implementation must satisfy.
4. **Implement the MCP server** exposing the five tools from Section 4, with all file I/O contained inside it. Validate each tool independently (e.g., a quick manual call to `query_crm_by_email` with a known and an unknown email) before wiring up the agents.
5. **Write the three agent system prompts** (`agents/*/system_prompt.md`) following the personas and constraints in Section 5. Keep them as separate files so they can be iterated on independently of orchestration code.
6. **Implement agent wiring**, ensuring the Orchestrator only ever passes raw ticket text to the Sentiment Analyst, and only ever passes structured fields (never raw text) to the Risk Assessor.
7. **Implement the decision routing logic** in the Orchestrator: CODE_RED → `draft_account_manager_escalation`; WATCH → `log_watchlist_entry`; LOW → no outbox action; all three → `mark_ticket_processed`.
8. **Implement run logging**: each full run writes one JSON file to `logs/run_history/` capturing every ticket's full decision trail (sentiment verdict, CRM record, risk verdict, action taken) — this is your demo evidence and your audit trail for the capstone writeup.
9. **Dry-run against all four seed tickets** and confirm: ticket_001 → LOW, ticket_002 → CODE_RED, ticket_003 → CODE_RED or WATCH depending on threshold tuning (but must NOT be LOW — this is the key test of the "calm but serious" case), ticket_004 → WATCH or LOW (must NOT be CODE_RED — the key test of "anger isn't the same as risk").
10. **Tune `risk_thresholds.json`** if the dry run doesn't produce the expected tier outcomes above, then re-run until all four cases behave as designed.
11. **Write the README** covering: problem statement, architecture diagram (textual, from Section 1), how to run a demo end-to-end, and an explicit "Privacy & Security" subsection stating that no ticket or CRM data ever leaves the local filesystem.
12. **Final pass:** re-read all four tickets and the CRM file as a sanity check that nothing in the synthetic data accidentally matches real people/companies, since this will be a public Kaggle submission.

---

### Summary for the Capstone Judges (talking points to lift into your writeup)
- **Security/Privacy:** every data touchpoint is mediated by one local MCP server; no network calls; no paid APIs.
- **MCP Server:** five purpose-built tools with explicit schemas, not a generic "read any file" tool — demonstrating intentional, minimal-surface tool design.
- **Agentic reasoning:** the Risk Assessor explicitly reasons about interacting financial and emotional signals rather than applying a fixed if/then formula, and the system is designed to catch the case competitors' keyword-matching demos will miss — a calm, polite, high-value client who is quietly leaving.
