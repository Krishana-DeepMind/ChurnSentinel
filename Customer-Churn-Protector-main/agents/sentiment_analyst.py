import os
import json
from agents.llm_client import simulate_sentiment_analysis

class SentimentAnalystAgent:
    """
    Sub-agent that only receives raw ticket text and returns a structured emotional-risk verdict.
    Has no access to CRM.
    """
    def __init__(self):
        self.prompt_path = os.path.join(os.path.dirname(__file__), "sentiment_analyst", "system_prompt.md")
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self):
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"You are the Sentiment Analyst. Analyze support ticket text. Details: {e}"

    def analyze(self, raw_text):
        """
        Analyzes the ticket text.
        Returns: Dict containing keys: sentiment_label, frustration_score, churn_signals_detected, key_phrases
        """
        # Call simulated local model
        response_json = simulate_sentiment_analysis(self.system_prompt, raw_text)
        return json.loads(response_json)
