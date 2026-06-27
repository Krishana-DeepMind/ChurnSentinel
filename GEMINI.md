# Revenue Protector — Project Memory

## Project Context
The **Revenue Protector** is a local-only multi-agent system built for the Kaggle Vibecoding Agents Capstone (Agents for Business Track). The system evaluates incoming customer tickets, queries a local synthetic CRM, computes risk scores with a semantic Risk Assessor, and routes decisions (escalate, watchlist, mark processed) via a local MCP server.

## Current State
- **Workspace folders scaffolded**: Completed directory setup.
- **GEMINI.md initialized**: Tracking project context.
- **Repository restructuring**: Cleaned up duplicate nested directory, migrated files to root level.
- **Multi-agent pipeline**: Implemented Orchestrator, Sentiment Analyst, and Risk Assessor.
- **Dashboard interface**: Completed FastAPI web dashboard running on `http://127.0.0.1:8000/`.
- **Test suite passing**: Verified all test cases and validations successfully.

## Next steps
- Monitor system execution, refine LLM client prompt templates, or prepare final Capstone submission.

## Key Rules & Constraints
1. **$0 Budget & 100% Local**: No external network requests or paid APIs.
2. **MCP Tool Contracts**: Expose exactly five tools (`read_new_tickets`, `query_crm_by_email`, `draft_account_manager_escalation`, `log_watchlist_entry`, `mark_ticket_processed`).
3. **Agent Separation**: Sentiment Analyst receives raw text only. Risk Assessor receives structured data only.
4. **Processing Sequence**: Routing decisions must execute exactly as defined (CODE_RED -> escalation, WATCH -> watchlist, LOW -> none), with `mark_ticket_processed` called last.
5. **Expected Seed Ticket Outputs**:
   - `ticket_001` -> `LOW`
   - `ticket_002` -> `CODE_RED`
   - `ticket_003` -> `CODE_RED` or `WATCH` (never `LOW`)
   - `ticket_004` -> `WATCH` or `LOW` (never `CODE_RED`)
