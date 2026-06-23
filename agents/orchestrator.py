import os
import json
import sys
from datetime import datetime

# Direct imports of MCP tool functions to simulate tool calls
from mcp_server import server
from agents.sentiment_analyst import SentimentAnalystAgent
from agents.risk_assessor import RiskAssessorAgent

class OrchestratorAgent:
    """
    Workflow state machine that processes tickets, runs analysis,
    queries CRM, scores risk, drafts outbox events, logs run history.
    """
    def __init__(self):
        self.prompt_path = os.path.join(os.path.dirname(__file__), "orchestrator", "system_prompt.md")
        self.system_prompt = self._load_system_prompt()
        self.sentiment_analyst = SentimentAnalystAgent()
        self.risk_assessor = RiskAssessorAgent()
        self.run_history_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "run_history")

    def _load_system_prompt(self):
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"You are the Orchestrator. Coordinate workflow. Details: {e}"

    def run_pipeline(self):
        """Runs the entire revenue protection pipeline on all inbox tickets."""
        print("[Orchestrator] Starting Churn Risk Pipeline Run...", file=sys.stderr)
        
        # 1. Fetch tickets from MCP Server
        tickets = server.read_new_tickets()
        if not tickets:
            print("[Orchestrator] No unprocessed tickets found in inbox.", file=sys.stderr)
            return {
                "summary": "No new tickets found.",
                "tickets_processed": 0,
                "escalations_drafted": 0,
                "watchlist_entries_logged": 0,
                "low_risk_processed": 0,
                "details": []
            }
            
        print(f"[Orchestrator] Found {len(tickets)} unprocessed ticket(s).", file=sys.stderr)
        
        run_details = []
        counts = {
            "escalations_drafted": 0,
            "watchlist_entries_logged": 0,
            "low_risk_processed": 0
        }
        
        for ticket in tickets:
            ticket_id = ticket["ticket_id"]
            email = ticket["sender_email"]
            raw_text = ticket["raw_text"]
            
            print(f"\n--- Processing Ticket: {ticket_id} (Sender: {email}) ---", file=sys.stderr)
            
            # Step 1: Sentiment Analysis on raw text only (no CRM data)
            print(f"[{ticket_id}] Sending raw text to Sentiment Analyst...", file=sys.stderr)
            sentiment_verdict = self.sentiment_analyst.analyze(raw_text)
            print(f"[{ticket_id}] Sentiment Verdict: Label={sentiment_verdict['sentiment_label']}, Frustration={sentiment_verdict['frustration_score']}", file=sys.stderr)
            
            # Step 2: Query CRM by email using MCP server tool
            print(f"[{ticket_id}] Querying CRM by email: {email}...", file=sys.stderr)
            crm_lookup = server.query_crm_by_email(email)
            
            crm_record = None
            if crm_lookup["found"]:
                crm_record = crm_lookup["record"]
                print(f"[{ticket_id}] CRM Record Found: Company={crm_record['company_name']}, ARR=${crm_record['annual_revenue']:,}, Renewal={crm_record['days_until_renewal']} days", file=sys.stderr)
            else:
                # Handle unknown customer gracefully
                print(f"[{ticket_id}] WARNING: Sender email '{email}' not found in CRM.", file=sys.stderr)
                crm_record = {
                    "email": email,
                    "company_name": "Unknown Entity",
                    "annual_revenue": 0,
                    "days_until_renewal": 999,
                    "account_manager_email": "support@revenueprotector.com",
                    "account_manager_name": "Unassigned Support Staff",
                    "tier": "Unknown"
                }
                
            # Step 3: Risk Assessment on structured fields only (NEVER raw text)
            print(f"[{ticket_id}] Invoking Risk Assessor with structured fields...", file=sys.stderr)
            risk_verdict = self.risk_assessor.assess_risk(sentiment_verdict, crm_record)
            print(f"[{ticket_id}] Risk Verdict: Tier={risk_verdict['risk_tier']}, Score={risk_verdict['churn_risk_score']}", file=sys.stderr)
            
            # Step 4: Decision Routing & Execution
            outbox_action = "none"
            outbox_file_path = ""
            
            tier = risk_verdict["risk_tier"]
            if tier == "CODE_RED":
                print(f"[{ticket_id}] CODE RED DETECTED. Drafting Account Manager escalation...", file=sys.stderr)
                escalation_res = server.draft_account_manager_escalation(
                    ticket_id=ticket_id,
                    company_name=crm_record["company_name"],
                    annual_revenue=crm_record["annual_revenue"],
                    days_until_renewal=crm_record["days_until_renewal"],
                    account_manager_email=crm_record["account_manager_email"],
                    churn_risk_score=risk_verdict["churn_risk_score"],
                    rationale=risk_verdict["rationale"],
                    recommended_action=risk_verdict["recommended_action"]
                )
                if escalation_res["success"]:
                    outbox_action = "draft_account_manager_escalation"
                    outbox_file_path = escalation_res["file_path"]
                    counts["escalations_drafted"] += 1
                    print(f"[{ticket_id}] Escalation drafted: {outbox_file_path}", file=sys.stderr)
                    
            elif tier == "WATCH":
                print(f"[{ticket_id}] WATCH tier detected. Logging watchlist entry...", file=sys.stderr)
                watchlist_res = server.log_watchlist_entry(
                    ticket_id=ticket_id,
                    company_name=crm_record["company_name"],
                    churn_risk_score=risk_verdict["churn_risk_score"],
                    rationale=risk_verdict["rationale"]
                )
                if watchlist_res["success"]:
                    outbox_action = "log_watchlist_entry"
                    outbox_file_path = watchlist_res["file_path"]
                    counts["watchlist_entries_logged"] += 1
                    print(f"[{ticket_id}] Watchlist entry logged: {outbox_file_path}", file=sys.stderr)
                    
            else:
                print(f"[{ticket_id}] LOW risk tier. No outbox action taken.", file=sys.stderr)
                counts["low_risk_processed"] += 1
                
            # Step 5: Mark processed LAST in all cases
            print(f"[{ticket_id}] Relocating processed ticket to archive...", file=sys.stderr)
            processed_res = server.mark_ticket_processed(ticket_id)
            processed_success = processed_res["success"]
            new_ticket_path = processed_res["new_path"]
            
            # Store complete audit trail for this ticket
            run_details.append({
                "ticket_id": ticket_id,
                "sender_email": email,
                "sentiment_verdict": sentiment_verdict,
                "crm_record": crm_record,
                "risk_verdict": risk_verdict,
                "outbox_action": outbox_action,
                "outbox_file_path": outbox_file_path,
                "processed_success": processed_success,
                "processed_path": new_ticket_path
            })
            
        # 6. Save Run History
        os.makedirs(self.run_history_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = os.path.join(self.run_history_dir, f"run_{timestamp}.json")
        
        run_summary = {
            "run_at": datetime.now().isoformat(),
            "tickets_processed": len(tickets),
            "escalations_drafted": counts["escalations_drafted"],
            "watchlist_entries_logged": counts["watchlist_entries_logged"],
            "low_risk_processed": counts["low_risk_processed"],
            "details": run_details
        }
        
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(run_summary, f, indent=2)
            print(f"\n[Orchestrator] Run history saved to: {history_file}", file=sys.stderr)
        except Exception as e:
            print(f"\n[Orchestrator] Error saving run history: {e}", file=sys.stderr)
            
        return run_summary
