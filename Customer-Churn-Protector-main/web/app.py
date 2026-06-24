import os
import json
import sys
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Adjust python path to allow importing from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_server import server
from agents.orchestrator import OrchestratorAgent

app = FastAPI(title="Revenue Protector Dashboard")

# Setup template directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_crm_revenue_map():
    crm_path = os.path.join(BASE_DIR, "data", "crm", "crm.json")
    crm_map = {}
    if os.path.exists(crm_path):
        try:
            with open(crm_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                for r in records:
                    company = r.get("company_name", "").strip()
                    revenue = r.get("annual_revenue", 0)
                    if company:
                        crm_map[company.lower()] = revenue
        except Exception as e:
            print(f"Error reading CRM: {e}", file=sys.stderr)
    return crm_map

def get_crm_email_map():
    crm_path = os.path.join(BASE_DIR, "data", "crm", "crm.json")
    crm_map = {}
    if os.path.exists(crm_path):
        try:
            with open(crm_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                for r in records:
                    company = r.get("company_name", "").strip()
                    email = r.get("email", "").strip()
                    if company and email:
                        crm_map[company.lower()] = email
        except Exception as e:
            print(f"Error reading CRM: {e}", file=sys.stderr)
    return crm_map

@app.post("/complete/{ticket_id}")
def complete_ticket(ticket_id: str):
    completed_path = os.path.join(BASE_DIR, "data", "completed.json")
    completed_ids = []
    if os.path.exists(completed_path):
        try:
            with open(completed_path, "r", encoding="utf-8") as f:
                completed_ids = json.load(f)
        except Exception:
            pass
    if ticket_id not in completed_ids:
        completed_ids.append(ticket_id)
        try:
            os.makedirs(os.path.dirname(completed_path), exist_ok=True)
            with open(completed_path, "w", encoding="utf-8") as f:
                json.dump(completed_ids, f, indent=2)
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    return JSONResponse({"status": "success"})

@app.post("/uncomplete/{ticket_id}")
def uncomplete_ticket(ticket_id: str):
    completed_path = os.path.join(BASE_DIR, "data", "completed.json")
    completed_ids = []
    if os.path.exists(completed_path):
        try:
            with open(completed_path, "r", encoding="utf-8") as f:
                completed_ids = json.load(f)
        except Exception:
            pass
    if ticket_id in completed_ids:
        completed_ids.remove(ticket_id)
        try:
            with open(completed_path, "w", encoding="utf-8") as f:
                json.dump(completed_ids, f, indent=2)
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    return JSONResponse({"status": "success"})

def get_customer_draft(ticket_id: str):
    outbox_dir = os.path.join(BASE_DIR, "data", "outbox_to_customer")
    if not os.path.exists(outbox_dir):
        return None
    try:
        files = os.listdir(outbox_dir)
    except Exception:
        return None
    
    # Match files like ack_ticket_002_... or resolution_ticket_002_...
    t_num = ticket_id.replace("ticket_", "")
    matching = [f for f in files if (f.startswith(f"ack_ticket_{t_num}_") or f.startswith(f"resolution_ticket_{t_num}_")) and f.endswith(".txt")]
    if not matching:
        return None
    
    # Sort: resolution takes precedence over ack, and pick the newest one
    matching.sort(key=lambda x: (1 if x.startswith("resolution_") else 0, x), reverse=True)
    filename = matching[0]
    file_path = os.path.join(outbox_dir, filename)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        headers = {}
        body_lines = []
        in_body = False
        for line in content.splitlines():
            if in_body:
                body_lines.append(line)
            elif not line.strip():
                continue
            elif line.startswith("To:"):
                headers["to"] = line[3:].strip()
            elif line.startswith("Subject:"):
                headers["subject"] = line[8:].strip()
            elif line.startswith("Body:"):
                in_body = True
            elif ":" in line:
                key, val = line.split(":", 1)
                headers[key.strip().lower()] = val.strip()
            else:
                in_body = True
                body_lines.append(line)
                
        return {
            "to": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "body": "\n".join(body_lines).strip(),
            "filename": filename
        }
    except Exception as e:
        print(f"Error parsing draft for {ticket_id}: {e}", file=sys.stderr)
        return None

@app.get("/", response_class=HTMLResponse)
def read_dashboard(request: Request, process: str = None):
    # Run the pipeline if requested
    if process == "true":
        agent = OrchestratorAgent()
        agent.run_pipeline()
        # If it is an AJAX request, return a JSON response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return JSONResponse({"status": "success", "message": "Pipeline run completed successfully"})
        return RedirectResponse(url="/", status_code=303)

    # 1. Fetch inbox tickets
    inbox_tickets = []
    try:
        inbox_tickets = server.read_new_tickets()
    except Exception as e:
        print(f"Error reading new tickets: {e}", file=sys.stderr)

    # 2. Count processed tickets
    processed_dir = os.path.join(BASE_DIR, "data", "tickets", "processed")
    processed_count = 0
    if os.path.exists(processed_dir):
        try:
            processed_count = len([f for f in os.listdir(processed_dir) if f.endswith(".txt")])
        except Exception as e:
            print(f"Error counting processed tickets: {e}", file=sys.stderr)

    # Load completed tickets list
    completed_path = os.path.join(BASE_DIR, "data", "completed.json")
    completed_set = set()
    if os.path.exists(completed_path):
        try:
            with open(completed_path, "r", encoding="utf-8") as f:
                completed_set = set(json.load(f))
        except Exception:
            pass

    # 3 & 4. Escalations and Watchlist are populated dynamically from consolidated risk assessments (see below)
    escalations = []
    completed_escalations = []
    watchlist = []
    completed_watchlist = []

    # 5. Revenue At Risk — computed after risk assessments are built (see below)

    # 6. Read audit logs & compile risk assessments
    history_dir = os.path.join(BASE_DIR, "logs", "run_history")
    all_runs = []
    
    if os.path.exists(history_dir):
        try:
            history_files = [f for f in os.listdir(history_dir) if f.endswith(".json")]
            for filename in history_files:
                file_path = os.path.join(history_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"Error loading log {filename}: {e}", file=sys.stderr)
                    continue
                
                if isinstance(data, list):
                    all_runs.extend(data)
                else:
                    all_runs.append(data)
        except Exception as e:
            print(f"Error loading run history logs: {e}", file=sys.stderr)

    # Sort all runs chronologically by run_at ascending
    all_runs.sort(key=lambda x: x.get("run_at", ""))

    # Group and consolidate by date (YYYY-MM-DD)
    audit_logs_by_date = {}
    risk_assessments_map = {} # Keep latest across all days

    for run_item in all_runs:
        run_time = run_item.get("run_at", "")
        if not run_time:
            continue
        run_date = run_time[:10] # YYYY-MM-DD
        
        if run_date not in audit_logs_by_date:
            audit_logs_by_date[run_date] = {
                "run_at": run_time,
                "details_map": {}
            }
        
        # Chronological ascending order: later runs overwrite earlier runs for the same day
        audit_logs_by_date[run_date]["run_at"] = run_time # Update to latest timestamp of the day
        for det in run_item.get("details", []):
            t_id = det.get("ticket_id")
            if t_id:
                audit_logs_by_date[run_date]["details_map"][t_id] = det
                
                # Keep latest assessment per ticket_id globally
                crm_rec = det.get("crm_record") or {}
                risk_v = det.get("risk_verdict") or {}
                sentiment_v = det.get("sentiment_verdict") or {}
                risk_assessments_map[t_id] = {
                    "ticket_id": t_id,
                    "customer": crm_rec.get("company_name", "Unknown"),
                    "company_name": crm_rec.get("company_name", "Unknown"),
                    "email": det.get("sender_email", ""),
                    "arr": crm_rec.get("annual_revenue", 0),
                    "annual_revenue": crm_rec.get("annual_revenue", 0),
                    "days_to_renewal": crm_rec.get("days_until_renewal", 0),
                    "days_until_renewal": crm_rec.get("days_until_renewal", 0),
                    "sentiment": sentiment_v.get("sentiment_label", "N/A"),
                    "risk_tier": risk_v.get("risk_tier", "LOW"),
                    "score": risk_v.get("churn_risk_score", 0),
                    "churn_risk_score": risk_v.get("churn_risk_score", 0),
                    "rationale": risk_v.get("rationale", ""),
                    "recommended_action": risk_v.get("recommended_action", ""),
                    "account_manager_email": crm_rec.get("account_manager_email", ""),
                    "account_manager_name": crm_rec.get("account_manager_name", ""),
                    "escalated_at": run_time,
                    "logged_at": run_time,
                    "run_time": run_time
                }
                draft = get_customer_draft(t_id)
                if draft:
                    risk_assessments_map[t_id]["customer_draft"] = draft

    # Build final audit logs list, sorted newest day first
    audit_logs = []
    for run_date in sorted(audit_logs_by_date.keys(), reverse=True):
        day_data = audit_logs_by_date[run_date]
        details_list = list(day_data["details_map"].values())
        audit_logs.append({
            "filename": f"run_{run_date.replace('-', '')}.json",
            "run_at": day_data["run_at"],
            "tickets_processed": len(details_list),
            "escalations_drafted": sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "CODE_RED"),
            "watchlist_entries_logged": sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "WATCH"),
            "low_risk_processed": sum(1 for d in details_list if d.get("risk_verdict", {}).get("risk_tier") == "LOW"),
            "details": details_list
        })

    # Convert map to sorted list (sorted by risk tier severity and score descending)
    tier_severity = {"CODE_RED": 3, "WATCH": 2, "LOW": 1}
    all_assessments = sorted(
        risk_assessments_map.values(),
        key=lambda x: (-tier_severity.get(x.get("risk_tier", "LOW"), 0), -x.get("score", 0), x.get("ticket_id", ""))
    )

    risk_assessments = []
    completed_assessments = []
    for item in all_assessments:
        t_id = item.get("ticket_id")
        if t_id in completed_set:
            completed_assessments.append(item)
        else:
            risk_assessments.append(item)

    # Populate escalations and watchlist from the latest consolidated risk assessments
    for item in risk_assessments:
        if item.get("risk_tier") == "CODE_RED":
            escalations.append(item)
        elif item.get("risk_tier") == "WATCH":
            watchlist.append(item)

    for item in completed_assessments:
        if item.get("risk_tier") == "CODE_RED":
            completed_escalations.append(item)
        elif item.get("risk_tier") == "WATCH":
            completed_watchlist.append(item)

    # 5. Compute Revenue At Risk — combines outbox files AND risk assessments
    crm_map = get_crm_revenue_map()
    at_risk_companies = {}

    # Source 1: Active escalations (have annual_revenue inline)
    for esc in escalations:
        company = esc.get("company_name", "").strip()
        if company:
            arr = esc.get("annual_revenue")
            if arr is None:
                arr = crm_map.get(company.lower(), 0)
            at_risk_companies[company.lower()] = max(at_risk_companies.get(company.lower(), 0), arr)

    # Source 2: Active watchlist (look up revenue from CRM)
    for wl in watchlist:
        company = wl.get("company_name", "").strip()
        if company:
            arr = crm_map.get(company.lower(), 0)
            at_risk_companies[company.lower()] = max(at_risk_companies.get(company.lower(), 0), arr)

    # Source 3: Active risk assessments with CODE_RED or WATCH tier
    for item in risk_assessments:
        tier = item.get("risk_tier", "LOW")
        if tier in ("CODE_RED", "WATCH"):
            customer = item.get("customer", "").strip()
            if customer:
                arr = item.get("arr", 0) or crm_map.get(customer.lower(), 0)
                at_risk_companies[customer.lower()] = max(at_risk_companies.get(customer.lower(), 0), arr)

    revenue_at_risk = sum(at_risk_companies.values())

    # Enhance inbox tickets with CRM lookup if they are in CRM
    enhanced_inbox_tickets = []
    for ticket in inbox_tickets:
        email = ticket.get("sender_email", "")
        crm_record = None
        if email:
            crm_res = server.query_crm_by_email(email)
            if crm_res.get("found"):
                crm_record = crm_res.get("record")
        enhanced_inbox_tickets.append({
            "ticket_id": ticket.get("ticket_id"),
            "sender_email": email,
            "raw_text": ticket.get("raw_text", ""),
            "company_name": crm_record.get("company_name") if crm_record else "Unknown Entity",
            "annual_revenue": crm_record.get("annual_revenue") if crm_record else 0,
            "days_until_renewal": crm_record.get("days_until_renewal") if crm_record else 999
        })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "inbox_count": len(inbox_tickets),
        "processed_count": processed_count,
        "escalations_count": len(escalations),
        "watchlist_count": len(watchlist),
        "completed_count": len(completed_assessments),
        "revenue_at_risk": revenue_at_risk,
        "inbox_tickets": enhanced_inbox_tickets,
        "risk_assessments": risk_assessments,
        "completed_assessments": completed_assessments,
        "escalations": escalations,
        "completed_escalations": completed_escalations,
        "watchlist": watchlist,
        "completed_watchlist": completed_watchlist,
        "audit_logs": audit_logs
    })
