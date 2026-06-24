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
                
            # Phase 1: Draft Customer Acknowledgment
            from agents.llm_client import simulate_acknowledgment_generation
            print(f"[{ticket_id}] Generating customized customer acknowledgment...", file=sys.stderr)
            ack_json = simulate_acknowledgment_generation(
                sentiment_label=sentiment_verdict["sentiment_label"],
                frustration_score=sentiment_verdict["frustration_score"],
                company_name=crm_record["company_name"]
            )
            ack_data = json.loads(ack_json)
            ack_res = server.draft_customer_acknowledgment(
                ticket_id=ticket_id,
                customer_email=email,
                subject=ack_data["subject"],
                body=ack_data["body"]
            )
            if ack_res["success"]:
                print(f"[{ticket_id}] Customer acknowledgment drafted: {ack_res['file_path']}", file=sys.stderr)

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
                "processed_success": processed_success,
                "processed_path": new_ticket_path
            })
            
        # Phase 2: Process Manager Resolutions
        print("[Orchestrator] Checking for pending manager resolutions...", file=sys.stderr)
        pending_resolutions = server.read_pending_resolutions()
        resolutions_processed = 0
        if pending_resolutions:
            print(f"[Orchestrator] Found {len(pending_resolutions)} pending manager resolution(s).", file=sys.stderr)
            from agents.llm_client import simulate_resolution_generation
            for res in pending_resolutions:
                res_ticket_id = res["ticket_id"]
                res_notes = res["notes"]
                res_email = res["customer_email"]
                res_file = res["file_path"]
                
                # Query CRM for company name
                res_company_name = "Customer"
                if res_email:
                    crm_lookup = server.query_crm_by_email(res_email)
                    if crm_lookup["found"]:
                        res_company_name = crm_lookup["record"]["company_name"]
                
                print(f"[{res_ticket_id}] Translating manager notes to customer resolution email...", file=sys.stderr)
                translated_json = simulate_resolution_generation(res_notes, res_company_name)
                translated_data = json.loads(translated_json)
                
                res_res = server.draft_customer_resolution(
                    ticket_id=res_ticket_id,
                    customer_email=res_email or "customer@revenueprotector.com",
                    subject=translated_data["subject"],
                    body=translated_data["body"],
                    resolution_file_path=res_file
                )
                if res_res["success"]:
                    resolutions_processed += 1
                    print(f"[{res_ticket_id}] Resolution email drafted and manager file archived.", file=sys.stderr)
        else:
            print("[Orchestrator] No pending manager resolutions found.", file=sys.stderr)

        # 6. Save Run History
        os.makedirs(self.run_history_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        history_file = os.path.join(self.run_history_dir, f"run_{date_str}.json")
        
        daily_summary = None
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    if isinstance(raw_data, list):
                        consolidated_details = {}
                        for run_item in raw_data:
                            for det in run_item.get("details", []):
                                t_id = det.get("ticket_id")
                                if t_id:
                                    consolidated_details[t_id] = det
                        details_list = list(consolidated_details.values())
                        daily_summary = {
                            "run_at": datetime.now().isoformat(),
                            "tickets_processed": len(details_list),
                            "escalations_drafted": sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "CODE_RED"),
                            "watchlist_entries_logged": sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "WATCH"),
                            "low_risk_processed": sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "LOW"),
                            "details": details_list
                        }
                    else:
                        daily_summary = raw_data
            except Exception as e:
                print(f"Error loading existing run history: {e}", file=sys.stderr)
                daily_summary = None
                
        if daily_summary is None:
            daily_summary = {
                "run_at": datetime.now().isoformat(),
                "tickets_processed": len(tickets),
                "escalations_drafted": counts["escalations_drafted"],
                "watchlist_entries_logged": counts["watchlist_entries_logged"],
                "low_risk_processed": counts["low_risk_processed"],
                "resolutions_processed": resolutions_processed,
                "details": run_details
            }
        else:
            details_map = {det["ticket_id"]: det for det in daily_summary.get("details", [])}
            for det in run_details:
                details_map[det["ticket_id"]] = det
                
            details_list = list(details_map.values())
            daily_summary["run_at"] = datetime.now().isoformat()
            daily_summary["details"] = details_list
            daily_summary["tickets_processed"] = len(details_list)
            daily_summary["escalations_drafted"] = sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "CODE_RED")
            daily_summary["watchlist_entries_logged"] = sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "WATCH")
            daily_summary["low_risk_processed"] = sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "LOW")
            daily_summary["resolutions_processed"] = daily_summary.get("resolutions_processed", 0) + resolutions_processed
            
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(daily_summary, f, indent=2)
            print(f"\n[Orchestrator] Run history saved to: {history_file}", file=sys.stderr)
        except Exception as e:
            print(f"\n[Orchestrator] Error saving run history: {e}", file=sys.stderr)
            
        return daily_summary
