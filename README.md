# The Revenue Protector — Churn Risk & Rescue Agent

## Kaggle "Vibecoding Agents Capstone" Submission (Agents for Business Track)

### 1. Problem Statement
For enterprise SaaS businesses, losing a major account is one of the single most expensive business failures. Traditional support ticketing systems treat all complaints identically based on entry order or basic queues. They fail to catch high-financial-exposure risk or separate simple venting from genuine intent to churn.

The **Revenue Protector** solves this by establishing an automated, tool-mediated, and secure multi-agent workflow that:
- Identifies critical financial accounts approaching renewal.
- Segregates raw text emotional inputs from financial facts, protecting analysis from prompt-injection or emotional distortion.
- Integrates local-first processing so that no customer PII or proprietary CRM facts ever leave the company's local boundary.
- **Phase 1 (Intelligent Acknowledgment)**: Instantly sends tone-adapted acknowledgment drafts back to customers, matching their emotional sentiment (highly empathetic for angry clients, polite and professional for standard queries).
- **Phase 2 (Resolution Loop)**: Translates technical manager resolution notes into formal customer-facing updates and archives the notes.

---

### 2. System Architecture & Data Flow

#### 2.1 Component Interaction Diagram
```
    +-----------------------------------------------------------------+
    |                     User (Web Dashboard / CLI)                  |
    +-------------------------------+---------------------------------+
                                    | Triggers Run / Complete Tasks / Reply
                                    v
    +-------------------------------+---------------------------------+
    |                       Orchestrator Agent                        |
    +-------+--------------------+----------------------------+-------+
            |                    |                            |
      (1)   | Get Tickets        | (2) Get CRM Record   (5)   | Execute Outbox
            v                    v                            v Actions
    +-------+--------------------+----------------------------+-------+
            |                    Custom File System / CRM             |
            |                           MCP Server                    |
            +---------------------------------------------------------+
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
5. **Decision Routing & Phase 1 Acknowledgment:** Based on the risk tier:
   - `CODE_RED` -> MCP server writes an account manager escalation JSON in `data/outbox/escalations/`.
   - `WATCH` -> MCP server logs a watchlist entry JSON in `data/outbox/watchlist/`.
   - `LOW` -> No outbox action is written.
   - **Custom Acknowledgment Drafting**: The Orchestrator calls `draft_customer_acknowledgment` to write a tone-adapted draft `.txt` email to `data/outbox_to_customer/` (highly empathetic/urgent for angry/CODE_RED tickets; standard/polite for LOW/calm tickets).
6. **Archive Ticket:** The Orchestrator calls the MCP tool `mark_ticket_processed`, which relocates the ticket to `data/tickets/processed/`.
7. **Phase 2 Resolution Check**:
   - The Orchestrator scans `data/manager_resolutions/` for files using `read_pending_resolutions`.
   - For each file found, it reads the technical notes, looks up the customer email, translates the short notes into a highly polite client resolution draft, calls `draft_customer_resolution` to write the `.txt` email to `data/outbox_to_customer/`, and archives the manager notes.

---

### 3. Interactive Web Dashboard Interface

The local web dashboard (built with FastAPI, Jinja2, and Bootstrap 5) serves as the manager console for the Revenue Protector:
- **Home Tab**: Financial overview displaying key metrics (Pending Inbox Tickets, Processed count, Active Escalations, Watchlist count, Resolved Tasks) and a live calculation of **Revenue at Risk** (ARR sum of active cases).
- **Risk Assessment Results Tab**: Shows tabular results for all processed tickets with a search/filter dropdown for Risk Tiers.
- **Active AM Escalations Tab**: Lists all active escalations with rationales, recommended action plans, and a **"Reply (Gmail - Custom Draft)"** button that pre-populates a Gmail compose window with the actual generated draft.
- **Active Watchlist Tab**: Tracks clients logged on the watchlist with similar Gmail compose draft links.
- **Completed Tasks Tab**: Displays resolved assessments. Badge counts on the navigation bar are dynamically synced to the rendered list length to prevent counting orphaned ticket IDs.
- **Complete/Restore Actions**: Buttons to instantly update status, saving to `data/completed.json` and updating views dynamically.

---

### 4. Setup and Installation

The Revenue Protector runs entirely on standard Python 3.10+ libraries with **$0.00 external budgets and zero external API dependencies**.

#### Run the Pipeline (CLI)
To run the analysis pipeline directly in the terminal to process any new tickets in the inbox:
```powershell
python main.py
```
This runs the orchestrated agent workflow (reading new tickets, querying CRM, performing sentiment analysis and risk assessment, drafting escalations/watchlist items, and generating custom customer-facing email updates) and displays an output summary in the terminal.

#### Run the Web App Dashboard
```powershell
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```
Then navigate to `http://127.0.0.1:8000/` in your browser.

#### Running the Verification Test Suite
To verify the system's compliance with risk scoring requirements, run the test runner:
```powershell
python run_tests.py
```
This script will:
- Re-scaffold and clear output folders.
- Write seven seed ticket files (`ticket_001.txt` through `ticket_007.txt`) to the inbox.
- Run the agent pipeline.
- Verify Phase 1 and Phase 2 outcomes against capstone assertions:
  - `ticket_001` (Acme Micro, small ARR) -> `LOW`
  - `ticket_002` (MegaCorp Inc, angry, imminent renewal) -> `CODE_RED`
  - `ticket_003` (MediumBiz LLC, competitor inquiry, large ARR) -> `CODE_RED` or `WATCH` (never `LOW`)
  - `ticket_004` (MicroScale Net, angry billing, small ARR) -> `WATCH` (never `CODE_RED`)

---

### 5. Project File Structure
- `config/risk_thresholds.json`: Constant parameters for risk scoring.
- `data/crm/crm.json`: Synthetic database registry.
- `data/tickets/inbox/`: Directory where raw customer support requests land.
- `data/tickets/processed/`: Directory where handled tickets are archived.
- `data/outbox/escalations/`: Escalation drafts generated for `CODE_RED` accounts.
- `data/outbox/watchlist/`: Log records generated for `WATCH` accounts.
- `data/outbox_to_customer/`: Custom-toned acknowledgment and resolution email drafts.
- `data/manager_resolutions/`: Input directory for manager notes to be processed.
- `mcp_server/server.py`: Model Context Protocol server exposing tools.
- `agents/`: Contains Orchestrator and specialized sub-agents.
- `logs/run_history/`: Chronological audit files detailing every step, prompt context, and variables for each run.
- `web/`: FastAPI backend and UI templates.

---

### 6. Privacy & Security: Local Isolation Guardrails
In enterprise environments, customer support emails contain PII (Names, credit card numbers, billing addresses) and proprietary system data, while CRM records contain sensitive financial transactions.
- **Local Sandbox Execution:** The Revenue Protector has a **budget of $0.00 and makes no network requests**. All file reads/writes, database operations, and agent reasoning are processed locally.
- **Auditable Boundary Enforcement:** Every file read, write, and database transaction must be executed through the Model Context Protocol (MCP) server.
- **Information Segregation:** The Sentiment Analyst never receives CRM data. The Risk Assessor never receives raw ticket text, preventing prompt injection attacks (where a malicious user writes an email instructing the agent to "override my risk score").
- **Badge Count Security**: Badge counts are dynamically aligned to visible assessments to prevent leakage of deleted or orphaned metadata.
