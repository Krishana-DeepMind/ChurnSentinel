import os
import re
import json
import shutil
import sys
from datetime import datetime

# Base paths relative to this server file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INBOX_DIR = os.path.join(BASE_DIR, "data", "tickets", "inbox")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "tickets", "processed")
CRM_PATH = os.path.join(BASE_DIR, "data", "crm", "crm.json")
ESCALATION_DIR = os.path.join(BASE_DIR, "data", "outbox", "escalations")
WATCHLIST_DIR = os.path.join(BASE_DIR, "data", "outbox", "watchlist")

def extract_email(text):
    """
    Extracts the sender email address from the ticket text.
    First looks for standard email formats in headers, then falls back to any email pattern.
    """
    # Look for From: ... <email> or From: email
    match = re.search(r'From:\s*(?:[^<\n]*<)?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback to searching for the first email address in the body
    match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    if match:
        return match.group(1).strip()
    
    return ""

def read_new_tickets():
    """
    Tool 4.1: Scans data/tickets/inbox/ for .txt files not yet marked processed.
    Returns: list of structured ticket objects.
    """
    tickets = []
    if not os.path.exists(INBOX_DIR):
        return tickets
        
    for filename in sorted(os.listdir(INBOX_DIR)):
        if filename.endswith(".txt"):
            file_path = os.path.join(INBOX_DIR, filename)
            ticket_id = os.path.splitext(filename)[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                email = extract_email(content)
                tickets.append({
                    "ticket_id": ticket_id,
                    "sender_email": email,
                    "raw_text": content,
                    "file_path": file_path
                })
            except Exception as e:
                print(f"Error reading ticket {filename}: {e}", file=sys.stderr)
                
    return tickets

def query_crm_by_email(email):
    """
    Tool 4.2: Looks up a customer record in crm.json by exact email match.
    Returns: { "found": bool, "record": dict | None }
    """
    if not os.path.exists(CRM_PATH):
        return {"found": False, "record": None}
        
    try:
        with open(CRM_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
            
        for r in records:
            if r.get("email", "").strip().lower() == email.strip().lower():
                return {"found": True, "record": r}
    except Exception as e:
        print(f"Error reading CRM: {e}", file=sys.stderr)
        
    return {"found": False, "record": None}

def draft_account_manager_escalation(ticket_id, company_name, annual_revenue, days_until_renewal, 
                                    account_manager_email, churn_risk_score, rationale, recommended_action):
    """
    Tool 4.3: Writes a structured escalation file to data/outbox/escalations/.
    Returns: { "success": bool, "file_path": string }
    """
    if not os.path.exists(ESCALATION_DIR):
        os.makedirs(ESCALATION_DIR, exist_ok=True)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"escalation_{ticket_id}_{timestamp}.json"
    file_path = os.path.join(ESCALATION_DIR, filename)
    
    escalation_data = {
        "ticket_id": ticket_id,
        "company_name": company_name,
        "annual_revenue": annual_revenue,
        "days_until_renewal": days_until_renewal,
        "account_manager_email": account_manager_email,
        "churn_risk_score": churn_risk_score,
        "rationale": rationale,
        "recommended_action": recommended_action,
        "escalated_at": datetime.now().isoformat()
    }
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(escalation_data, f, indent=2)
        return {"success": True, "file_path": file_path}
    except Exception as e:
        print(f"Error drafting escalation: {e}", file=sys.stderr)
        return {"success": False, "file_path": ""}

def log_watchlist_entry(ticket_id, company_name, churn_risk_score, rationale):
    """
    Tool 4.4: Writes a lightweight watchlist record to data/outbox/watchlist/.
    Returns: { "success": bool, "file_path": string }
    """
    if not os.path.exists(WATCHLIST_DIR):
        os.makedirs(WATCHLIST_DIR, exist_ok=True)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"watchlist_{ticket_id}_{timestamp}.json"
    file_path = os.path.join(WATCHLIST_DIR, filename)
    
    watchlist_data = {
        "ticket_id": ticket_id,
        "company_name": company_name,
        "churn_risk_score": churn_risk_score,
        "rationale": rationale,
        "logged_at": datetime.now().isoformat()
    }
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(watchlist_data, f, indent=2)
        return {"success": True, "file_path": file_path}
    except Exception as e:
        print(f"Error logging watchlist entry: {e}", file=sys.stderr)
        return {"success": False, "file_path": ""}

def mark_ticket_processed(ticket_id):
    """
    Tool 4.5: Moves a ticket file from data/tickets/inbox/ to processed/.
    Returns: { "success": bool, "new_path": string }
    """
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR, exist_ok=True)
        
    src_path = os.path.join(INBOX_DIR, f"{ticket_id}.txt")
    dest_path = os.path.join(PROCESSED_DIR, f"{ticket_id}.txt")
    
    if not os.path.exists(src_path):
        # Perhaps already processed or ID incorrect
        return {"success": False, "new_path": ""}
        
    try:
        shutil.move(src_path, dest_path)
        return {"success": True, "new_path": dest_path}
    except Exception as e:
        print(f"Error marking ticket processed: {e}", file=sys.stderr)
        return {"success": False, "new_path": ""}

# New local directories for simulated customer outbox and resolutions
OUTBOX_CUSTOMER_DIR = os.path.join(BASE_DIR, "data", "outbox_to_customer")
MANAGER_RESOLUTIONS_DIR = os.path.join(BASE_DIR, "data", "manager_resolutions")
MANAGER_RESOLUTIONS_PROCESSED_DIR = os.path.join(MANAGER_RESOLUTIONS_DIR, "processed")

def draft_customer_acknowledgment(ticket_id, customer_email, subject, body):
    """
    Tool 4.6: Writes a customized acknowledgment email draft to data/outbox_to_customer/.
    Returns: { "success": bool, "file_path": string }
    """
    if not os.path.exists(OUTBOX_CUSTOMER_DIR):
        os.makedirs(OUTBOX_CUSTOMER_DIR, exist_ok=True)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"ack_{ticket_id}_{timestamp}.txt"
    file_path = os.path.join(OUTBOX_CUSTOMER_DIR, filename)
    
    content = f"To: {customer_email}\nSubject: {subject}\n\nBody:\n{body}\n"
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "file_path": file_path}
    except Exception as e:
        print(f"Error drafting customer acknowledgment: {e}", file=sys.stderr)
        return {"success": False, "file_path": ""}

def read_pending_resolutions():
    """
    Tool 4.7: Scans data/manager_resolutions/ for any .txt files.
    For each file, finds the ticket_id from the filename (e.g. resolution_ticket_002.txt),
    reads the notes, looks up the corresponding customer email from the processed/archived
    ticket file, and returns the metadata.
    Returns: list of dicts [{ "ticket_id": string, "notes": string, "customer_email": string, "file_path": string }]
    """
    resolutions = []
    if not os.path.exists(MANAGER_RESOLUTIONS_DIR):
        return resolutions
        
    for filename in sorted(os.listdir(MANAGER_RESOLUTIONS_DIR)):
        if filename.endswith(".txt"):
            file_path = os.path.join(MANAGER_RESOLUTIONS_DIR, filename)
            
            # Parse ticket ID, e.g. resolution_ticket_002.txt -> ticket_002
            match = re.search(r'(ticket_\d+)', filename)
            if not match:
                continue
            ticket_id = match.group(1)
            
            # Read manager notes
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    notes = f.read().strip()
            except Exception as e:
                print(f"Error reading resolution file {filename}: {e}", file=sys.stderr)
                continue
                
            # Find customer email from processed ticket or inbox ticket
            customer_email = ""
            ticket_src = os.path.join(PROCESSED_DIR, f"{ticket_id}.txt")
            if not os.path.exists(ticket_src):
                ticket_src = os.path.join(INBOX_DIR, f"{ticket_id}.txt")
                
            if os.path.exists(ticket_src):
                try:
                    with open(ticket_src, "r", encoding="utf-8") as f:
                        ticket_content = f.read()
                    customer_email = extract_email(ticket_content)
                except Exception as e:
                    print(f"Error extracting email for {ticket_id}: {e}", file=sys.stderr)
            
            resolutions.append({
                "ticket_id": ticket_id,
                "notes": notes,
                "customer_email": customer_email,
                "file_path": file_path
            })
            
    return resolutions

def draft_customer_resolution(ticket_id, customer_email, subject, body, resolution_file_path):
    """
    Tool 4.8: Writes a translated customer resolution email to data/outbox_to_customer/
    and moves the original manager resolution file to manager_resolutions/processed/.
    Returns: { "success": bool, "file_path": string }
    """
    if not os.path.exists(OUTBOX_CUSTOMER_DIR):
        os.makedirs(OUTBOX_CUSTOMER_DIR, exist_ok=True)
    if not os.path.exists(MANAGER_RESOLUTIONS_PROCESSED_DIR):
        os.makedirs(MANAGER_RESOLUTIONS_PROCESSED_DIR, exist_ok=True)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"resolution_{ticket_id}_{timestamp}.txt"
    file_path = os.path.join(OUTBOX_CUSTOMER_DIR, filename)
    
    content = f"To: {customer_email}\nSubject: {subject}\n\nBody:\n{body}\n"
    
    try:
        # Write outbox email
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Archive manager's resolution file
        if os.path.exists(resolution_file_path):
            base_name = os.path.basename(resolution_file_path)
            dest_name = f"{os.path.splitext(base_name)[0]}_{timestamp}.txt"
            dest_path = os.path.join(MANAGER_RESOLUTIONS_PROCESSED_DIR, dest_name)
            shutil.move(resolution_file_path, dest_path)
            
        return {"success": True, "file_path": file_path}
    except Exception as e:
        print(f"Error drafting customer resolution: {e}", file=sys.stderr)
        return {"success": False, "file_path": ""}

def run_jsonrpc_server():
    """
    Implements a simple JSON-RPC loop over stdin/stdout.
    This enables real MCP server execution when running the file directly.
    """
    sys.stderr.write("Revenue Protector MCP Server started (JSON-RPC over stdin/stdout).\n")
    sys.stderr.flush()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            req = json.loads(line)
            method = req.get("method")
            params = req.get("params", {})
            req_id = req.get("id")
            
            res_val = None
            error = None
            
            # Simple tools dispatching
            if method == "read_new_tickets":
                res_val = read_new_tickets()
            elif method == "query_crm_by_email":
                res_val = query_crm_by_email(params.get("email"))
            elif method == "draft_account_manager_escalation":
                res_val = draft_account_manager_escalation(
                    ticket_id=params.get("ticket_id"),
                    company_name=params.get("company_name"),
                    annual_revenue=params.get("annual_revenue"),
                    days_until_renewal=params.get("days_until_renewal"),
                    account_manager_email=params.get("account_manager_email"),
                    churn_risk_score=params.get("churn_risk_score"),
                    rationale=params.get("rationale"),
                    recommended_action=params.get("recommended_action")
                )
            elif method == "log_watchlist_entry":
                res_val = log_watchlist_entry(
                    ticket_id=params.get("ticket_id"),
                    company_name=params.get("company_name"),
                    churn_risk_score=params.get("churn_risk_score"),
                    rationale=params.get("rationale")
                )
            elif method == "mark_ticket_processed":
                res_val = mark_ticket_processed(params.get("ticket_id"))
            elif method == "draft_customer_acknowledgment":
                res_val = draft_customer_acknowledgment(
                    ticket_id=params.get("ticket_id"),
                    customer_email=params.get("customer_email"),
                    subject=params.get("subject"),
                    body=params.get("body")
                )
            elif method == "read_pending_resolutions":
                res_val = read_pending_resolutions()
            elif method == "draft_customer_resolution":
                res_val = draft_customer_resolution(
                    ticket_id=params.get("ticket_id"),
                    customer_email=params.get("customer_email"),
                    subject=params.get("subject"),
                    body=params.get("body"),
                    resolution_file_path=params.get("resolution_file_path")
                )
            else:
                error = {"code": -32601, "message": f"Method {method} not found"}
                
            res = {"jsonrpc": "2.0", "id": req_id}
            if error:
                res["error"] = error
            else:
                res["result"] = res_val
                
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            sys.stderr.write(f"Error handling request: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    run_jsonrpc_server()
