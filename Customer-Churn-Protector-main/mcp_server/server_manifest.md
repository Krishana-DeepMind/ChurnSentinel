# Local File System / CRM MCP Server Manifest

This Model Context Protocol (MCP) server exposes a specialized set of five tools to read tickets, lookup CRM entries, log watchlist updates, draft account manager escalations, and mark tickets as processed.

## Tools Summary

| Tool Name | Description |
|---|---|
| [`read_new_tickets`](file:///C:/Users/krish/Desktop/Capstone%20Project%20Kaggle/mcp_server/tool_specs/read_new_tickets.md) | Scans `data/tickets/inbox/` for new `.txt` tickets and returns them. |
| [`query_crm_by_email`](file:///C:/Users/krish/Desktop/Capstone%20Project%20Kaggle/mcp_server/tool_specs/query_crm_by_email.md) | Queries `data/crm/crm.json` for a customer record by email. |
| [`draft_account_manager_escalation`](file:///C:/Users/krish/Desktop/Capstone%20Project%20Kaggle/mcp_server/tool_specs/draft_account_manager_escalation.md) | Drafts a detailed escalation report for high-risk accounts in `data/outbox/escalations/`. |
| [`log_watchlist_entry`](file:///C:/Users/krish/Desktop/Capstone%20Project%20Kaggle/mcp_server/tool_specs/log_watchlist_entry.md) | Logs a watchlisted account report in `data/outbox/watchlist/`. |
| [`mark_ticket_processed`](file:///C:/Users/krish/Desktop/Capstone%20Project%20Kaggle/mcp_server/tool_specs/mark_ticket_processed.md) | Moves the processed ticket from the inbox directory to the processed directory. |
