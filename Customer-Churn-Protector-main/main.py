import sys
from agents.orchestrator import OrchestratorAgent

def main():
    agent = OrchestratorAgent()
    run_history = agent.run_pipeline()
    
    # Generate user-facing summary report
    print("\n" + "="*80)
    print("                      REVENUE PROTECTOR SYSTEM RUN SUMMARY                      ")
    print("="*80)
    print(f"Run Executed At:       {run_history.get('run_at', 'N/A')}")
    print(f"Total Tickets Scanned: {run_history['tickets_processed']}")
    print(f"Escalations Raised:    {run_history['escalations_drafted']} (CODE_RED)")
    print(f"Watchlist Logs Written: {run_history['watchlist_entries_logged']} (WATCH)")
    print(f"Low-Risk Handled:      {run_history['low_risk_processed']} (LOW)")
    print("="*80)
    
    if not run_history["details"]:
        print("No new tickets were processed during this run.")
        print("="*80)
        return
        
    print(f"{'Ticket ID':<12} | {'Company Name':<18} | {'Score':<5} | {'Tier':<8} | {'Rationale / Action'}")
    print("-"*80)
    
    for item in run_history["details"]:
        ticket_id = item["ticket_id"]
        company = item["crm_record"]["company_name"]
        verdict = item["risk_verdict"]
        score = verdict["churn_risk_score"]
        tier = verdict["risk_tier"]
        
        # Color coding indicators for premium CLI styling
        tier_str = tier
        if tier == "CODE_RED":
            tier_str = "\033[91mCODE_RED\033[0m"
        elif tier == "WATCH":
            tier_str = "\033[93mWATCH\033[0m"
        elif tier == "LOW":
            tier_str = "\033[92mLOW\033[0m"
            
        rat = verdict["rationale"]
        # Trim rationale for visual alignment
        if len(rat) > 60:
            rat = rat[:57] + "..."
            
        print(f"{ticket_id:<12} | {company:<18} | {score:<5} | {tier_str:<18} | {rat}")
        
    print("="*80)
    print("Processing run completed successfully. View full audit trail logs in logs/run_history/.")
    print("="*80)

if __name__ == "__main__":
    main()
