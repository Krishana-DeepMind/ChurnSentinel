# The Revenue Protector — Churn Risk & Rescue Agent

## Kaggle "Vibecoding Agents Capstone" Submission (Agents for Business Track)

### 1. Problem Statement
For enterprise SaaS businesses, losing a major account is one of the single most expensive business failures. Traditional support ticketing systems treat all complaints identically based on entry order or basic queues. They fail to catch high-financial-exposure risk or separate simple venting from genuine intent to churn.

The **Revenue Protector** solves this by establishing an automated, tool-mediated, and secure multi-agent workflow that:
- Identifies critical financial accounts approaching renewal.
- Segregates raw text emotional inputs from financial facts, protecting analysis from prompt-injection or emotional distortion.
- Integrates local-first processing so that no customer PII or proprietary CRM facts ever leave the company's local boundary.

---

### 2. System Architecture & Data Flow

#### 2.1 Component Interaction Diagram
```
    +-----------------------------------------------------------------+
    |                               User                              |
    +-------------------------------+---------------------------------+
                                    | Triggers Run / Check Inbox
                                    v
    +-------------------------------+---------------------------------+
    |                       Orchestrator Agent                        |
    +-------+--------------------+----------------------------+-------+
            |                    |                            |
      (1)   | Get Tickets        | (2) Get CRM Record   (5)   | Execute Outbox
            v                    v                            v Actions
    +-------+--------------------+----------------------------+-------+
    |                    Custom File System / CRM                     |
    |                           MCP Server                            |
    +-----------------------------------------------------------------+
            ^                    ^
            | (3) Analyze        | (4) Evaluate Risk
            |     Sentiment      |     (Structured Info Only)
    +-------+--------------------+------------------------------------+
    |                 Sentiment Analyst Sub-Agent                     |
    +-----------------------------------------------------------------+
    |                  Risk Assessor Sub-Agent                        |
    +-----------------------------------------------------------------+
```

#### 2.2 Sequence of Operations
1. **Inbox Retrieval:** The **Orchestrator** queries the **MCP Server** via `read_new_tickets` to fetch unprocessed tickets (`.txt` files) in `data/tickets/inbox/`.
2. **Linguistic Sentiment Analysis:** The Orchestrator forwards the raw ticket content to the **Sentiment Analyst Sub-Agent**. This sub-agent extracts emotional indicators (label, frustration score, key phrases, and explicit churn signals).
3. **Database Querying:** The Orchestrator calls the MCP server tool `query_crm_by_email` with the customer's email address.
4. **Structured Risk Scoring:** The Orchestrator packages the structured sentiment results and CRM details (revenue, days-to-renewal) and sends them to the **Risk Assessor Sub-Agent**. *Crucially, the Risk Assessor never sees the raw email text.*
5. **Decision Routing:** Based on the risk tier:
   - `CODE_RED` -> MCP server writes a comprehensive account manager escalation report draft in `data/outbox/escalations/`.
   - `WATCH` -> MCP server logs a lighter log entry in `data/outbox/watchlist/`.
   - `LOW` -> No outbox action is written.
6. **Archive Ticket:** The Orchestrator calls the MCP tool `mark_ticket_processed`, which relocates the ticket to `data/tickets/processed/`.

---

### 3. Setup and Installation

The Revenue Protector runs entirely on standard Python 3.10+ libraries with **$0.00 external budgets and zero external API dependencies**.

#### Prerequisites
- Python 3.10 or higher.
- A terminal (PowerShell, bash, etc.).

---

### 4. Running the System Demo End-to-End

#### Step 1: Run the Automated Verification Test Suite
To verify the system's compliance with risk scoring requirements, run the test runner:
```powershell
python run_tests.py
```
This script will:
- Re-scaffold and clear output folders.
- Write the four seed ticket files (`ticket_001.txt` through `ticket_004.txt`) to the inbox.
- Run the agent pipeline.
- Verify that outcomes match the criteria rules:
  - `ticket_001` (polite, minor UI bug, small ARR) -> `LOW`
  - `ticket_002` (angry API issue, large ARR, narrow renewal window) -> `CODE_RED`
  - `ticket_003` (calm competitor inquiry, large ARR, mid renewal window) -> `CODE_RED` or `WATCH` (never `LOW`)
  - `ticket_004` (angry billing, small ARR, distant renewal) -> `WATCH` (never `CODE_RED`)

#### Step 2: Run the Production Pipeline CLI
To process any files currently sitting in `data/tickets/inbox/` manually, run:
```powershell
python main.py
```

---

### 5. Project File Structure
- `config/risk_thresholds.json`: Constant parameters for risk scoring.
- `data/crm/crm.json`: Synthetic database registry.
- `data/tickets/inbox/`: Directory where raw customer support requests land.
- `data/tickets/processed/`: Directory where handled tickets are archived.
- `data/outbox/escalations/`: Escalation drafts generated for `CODE_RED` accounts.
- `data/outbox/watchlist/`: Log records generated for `WATCH` accounts.
- `mcp_server/server.py`: Model Context Protocol server exposing tools.
- `agents/`: Contains Orchestrator and specialized sub-agents.
- `logs/run_history/`: Chronological audit files detailing every step, prompt context, and variables for each run.

---

### 6. Privacy & Security: Local Isolation Guardrails
In enterprise environments, customer support emails contain PII (Names, credit card numbers, billing addresses) and proprietary system data, while CRM records contain sensitive financial transactions.
- **Local Sandbox Execution:** The Revenue Protector has a **budget of $0.00 and makes no network requests**. All file reads/writes, database operations, and agent reasoning are processed locally.
- **Auditable Boundary Enforcement:** The sub-agents have zero direct access to the filesystem. Every file read, write, and database transaction must be executed through the Model Context Protocol (MCP) server.
- **Information Segregation:** The Sentiment Analyst never receives CRM data. The Risk Assessor never receives raw ticket text, preventing prompt injection attacks (where a malicious user writes an email instructing the agent to "override my risk score").

---

### 7. Core Assumptions & Implementation Choices
*Note: In accordance with Rule 9, the following implementation choices were made to resolve ambiguity:*
1. **Simulated Offline LLM Agent Engine:** To strictly adhere to the $0.00 budget and local-only execution constraints (preventing external API calls or downloading large model weights), a simulated model engine is implemented in `llm_client.py`. It reads prompt instructions, outputs logs, and uses keyword-based heuristics to process data and output valid JSON matching the prompt schemas.
2. **MCP JSON-RPC CLI Wrapper:** The MCP server in `mcp_server/server.py` implements a standard JSON-RPC loop reading from standard input and writing to standard output. This allows the tool logic to be integrated with real MCP hosts (like Claude Desktop) while still allowing direct python imports in our Orchestrator.

