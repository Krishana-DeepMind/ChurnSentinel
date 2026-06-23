import os
import shutil
import json
import sys
from agents.orchestrator import OrchestratorAgent

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(BASE_DIR, "data", "tickets", "inbox")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "tickets", "processed")
ESCALATIONS_DIR = os.path.join(BASE_DIR, "data", "outbox", "escalations")
WATCHLIST_DIR = os.path.join(BASE_DIR, "data", "outbox", "watchlist")
HISTORY_DIR = os.path.join(BASE_DIR, "logs", "run_history")

# Ticket contents for restoring the demo/test environment
TICKETS_SEED = {
    "ticket_001.txt": """Subject: Small layout issue on dashboard
From: Alice Smith <alice.smith@acme-micro.com>
Date: Mon, 22 Jun 2026 14:22:10 -0400

Hi Support Team,

Hope you're having a good week. I just wanted to report a minor thing we noticed on our company dashboard. The "Export CSV" button appears to be slightly misaligned on mobile screens, overlapping with the date picker.

It's not blocking our work or anything, but it looks a bit messy. Could you please pass this on to your design or engineering team to take a look when they have a moment?

Thanks,
Alice Smith
Acme Micro
Email: alice.smith@acme-micro.com""",

    "ticket_002.txt": """Subject: CRITICAL: Unresolved downtime and serious platform issues
From: Bob Jones <bob.jones@megacorp.com>
Date: Tue, 23 Jun 2026 09:15:44 -0400
Importance: High

To: Senior Management / Escalations Team

I am writing this out of sheer frustration. This is the THIRD time in two weeks that our API sync has failed during business hours, causing major operational delays for MegaCorp. We have submitted tickets through your standard channel but keep getting template responses.

Frankly, this level of service is completely unacceptable. We are paying you guys a substantial amount of money, and with our contract renewal coming up next month, we are seriously evaluating other vendors. We cannot run our business on a platform that breaks this often. 

If this API downtime isn't permanently fixed and a manager doesn't call me today, I will block the renewal and we will migrate off your system immediately.

Bob Jones
Director of Operations, MegaCorp Inc.
bob.jones@megacorp.com""",

    "ticket_003.txt": """Subject: Inquiry regarding contract terms and offboarding process
From: Charlie Brown <charlie.brown@mediumbiz.org>
Date: Mon, 22 Jun 2026 16:30:15 -0400

Dear Customer Success Team,

I hope this email finds you well. 

As we approach our upcoming renewal window later this quarter, our management team is reviewing our software subscriptions. We have decided to evaluate alternative vendors in the space to see if they better align with our long-term system scaling plans.

Could you please provide the details of our current contract, specifically:
1. The notice period required for non-renewal.
2. The exact termination date if we opt out of the renewal.
3. The process for exporting all our historical company data.

We appreciate the support your team has provided, but we must ensure we are making the most cost-effective and scalable choice for MediumBiz LLC going forward.

Sincerely,
Charlie Brown
Procurement Lead
MediumBiz LLC
charlie.brown@mediumbiz.org""",

    "ticket_004.txt": """Subject: YOU OVERCHARGED ME!!! FIX THIS IMMEDIATELY!!!
From: David Miller <david.miller@microscale.net>
Date: Tue, 23 Jun 2026 11:05:00 -0400

I AM ABSOLUTELY FURIOUS. I JUST LOOKED AT MY CREDIT CARD STATEMENT AND YOU CHARGED ME $15.00 EXTRA THIS MONTH!!! 

THIS IS UNbelievable! I AM A CUSTOMER AND EXPECT ACCURATE BILLING. I WANT THIS REVERSED IMMEDIATELY OR I WILL DISPUTE THE CHARGE WITH MY BANK!!! 

WHY DID THIS HAPPEN? I DEMAND A WRITTEN EXPLANATION AND AN IMMEDIATE CREDIT REFUND FOR THE DISCREPANCY. THIS IS A HORRIBLE WAY TO RUN A COMPANY AND I WILL NOT TOLERATE BEING RIPPED OFF!!!

David Miller
MicroScale Net
david.miller@microscale.net"""
}

def clean_directory(path):
    """Removes all files from the specified directory."""
    if os.path.exists(path):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Error cleaning {item_path}: {e}", file=sys.stderr)

def setup_environment():
    """Restores the database to initial clean demo/test state."""
    print("[Test Runner] Resetting environment to clean state...", file=sys.stderr)
    
    # 1. Clean directories
    clean_directory(INBOX_DIR)
    clean_directory(PROCESSED_DIR)
    clean_directory(ESCALATIONS_DIR)
    clean_directory(WATCHLIST_DIR)
    
    # Ensure folders exist
    os.makedirs(INBOX_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(ESCALATIONS_DIR, exist_ok=True)
    os.makedirs(WATCHLIST_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    # 2. Write seed tickets into inbox
    for filename, content in TICKETS_SEED.items():
        file_path = os.path.join(INBOX_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
            
    print("[Test Runner] 4 seed tickets written to inbox.", file=sys.stderr)

def run_verifications():
    """Runs Orchestrator pipeline and validates output against rules."""
    agent = OrchestratorAgent()
    run_history = agent.run_pipeline()
    
    print("\n" + "="*50)
    print("           VERIFYING RISK SCORING OUTCOMES           ")
    print("="*50)
    
    success = True
    details = run_history["details"]
    
    # Map ticket ID to their processed details
    results_map = {item["ticket_id"]: item for item in details}
    
    # Constraint 1: ticket_001 = LOW
    t1 = results_map.get("ticket_001")
    if t1:
        tier = t1["risk_verdict"]["risk_tier"]
        score = t1["risk_verdict"]["churn_risk_score"]
        if tier == "LOW":
            print(f"[\033[92mPASS\033[0m] ticket_001 is LOW (Score: {score})")
        else:
            print(f"[\033[91mFAIL\033[0m] ticket_001 is {tier} (Expected: LOW, Score: {score})")
            success = False
    else:
        print("[\033[91mFAIL\033[0m] ticket_001 was not processed.")
        success = False
        
    # Constraint 2: ticket_002 = CODE_RED
    t2 = results_map.get("ticket_002")
    if t2:
        tier = t2["risk_verdict"]["risk_tier"]
        score = t2["risk_verdict"]["churn_risk_score"]
        if tier == "CODE_RED":
            print(f"[\033[92mPASS\033[0m] ticket_002 is CODE_RED (Score: {score})")
        else:
            print(f"[\033[91mFAIL\033[0m] ticket_002 is {tier} (Expected: CODE_RED, Score: {score})")
            success = False
    else:
        print("[\033[91mFAIL\033[0m] ticket_002 was not processed.")
        success = False
        
    # Constraint 3: ticket_003 = CODE_RED or WATCH but never LOW
    t3 = results_map.get("ticket_003")
    if t3:
        tier = t3["risk_verdict"]["risk_tier"]
        score = t3["risk_verdict"]["churn_risk_score"]
        if tier in ["CODE_RED", "WATCH"]:
            print(f"[\033[92mPASS\033[0m] ticket_003 is {tier} (Expected: CODE_RED/WATCH, Score: {score})")
        else:
            print(f"[\033[91mFAIL\033[0m] ticket_003 is {tier} (Expected: CODE_RED/WATCH, Score: {score})")
            success = False
    else:
        print("[\033[91mFAIL\033[0m] ticket_003 was not processed.")
        success = False
        
    # Constraint 4: ticket_004 = WATCH or LOW but never CODE_RED
    t4 = results_map.get("ticket_004")
    if t4:
        tier = t4["risk_verdict"]["risk_tier"]
        score = t4["risk_verdict"]["churn_risk_score"]
        if tier in ["WATCH", "LOW"]:
            print(f"[\033[92mPASS\033[0m] ticket_004 is {tier} (Expected: WATCH/LOW, Score: {score})")
        else:
            print(f"[\033[91mFAIL\033[0m] ticket_004 is {tier} (Expected: WATCH/LOW, Score: {score})")
            success = False
    else:
        print("[\033[91mFAIL\033[0m] ticket_004 was not processed.")
        success = False
        
    # Verify file structures
    # 1. Escalations written
    escalations = os.listdir(ESCALATIONS_DIR)
    print(f"\nDraft Escalations in Outbox: {len(escalations)}")
    for esc in escalations:
        print(f" - {esc}")
        
    # 2. Watchlist entries logged
    watchlist = os.listdir(WATCHLIST_DIR)
    print(f"Watchlist Log Entries: {len(watchlist)}")
    for wch in watchlist:
        print(f" - {wch}")
        
    # 3. Processed tickets relocated
    processed = os.listdir(PROCESSED_DIR)
    print(f"Processed Tickets Relocated: {len(processed)}")
    for prc in processed:
        print(f" - {prc}")
        
    print("="*50)
    if success:
        print("\033[92mALL TESTS PASSED SUCCESSFULLY!\033[0m")
        return 0
    else:
        print("\033[91mTEST SUITE ENCOUNTERED FAILURES.\033[0m")
        return 1

if __name__ == "__main__":
    setup_environment()
    exit_code = run_verifications()
    sys.exit(exit_code)
