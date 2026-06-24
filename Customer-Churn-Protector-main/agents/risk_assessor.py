import os
import json
from agents.llm_client import simulate_risk_assessment

class RiskAssessorAgent:
    """
    Sub-agent that only receives structured fields (sentiment verdict and CRM record).
    Has no access to raw ticket text. Returns risk score, tier, rationale, and action.
    """
    def __init__(self):
        self.prompt_path = os.path.join(os.path.dirname(__file__), "risk_assessor", "system_prompt.md")
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self):
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"You are the Risk Assessor. Combine sentiment metrics and CRM data. Details: {e}"

    def assess_risk(self, sentiment_verdict, crm_record):
        """
        Calculates churn risk.
        sentiment_verdict: Dict from SentimentAnalystAgent
        crm_record: Dict from crm.json lookup
        Returns: Dict containing keys: churn_risk_score, risk_tier, rationale, recommended_action
        """
        sentiment_json = json.dumps(sentiment_verdict)
        crm_json = json.dumps(crm_record)
        
        response_json = simulate_risk_assessment(self.system_prompt, sentiment_json, crm_json)
        return json.loads(response_json)
