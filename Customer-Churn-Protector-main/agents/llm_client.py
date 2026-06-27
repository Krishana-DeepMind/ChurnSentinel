import os
import re
import json
import requests

# Absolute paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
THRESHOLDS_PATH = os.path.join(BASE_DIR, "config", "risk_thresholds.json")

def load_thresholds():
    """Loads risk thresholds from config."""
    try:
        if os.path.exists(THRESHOLDS_PATH):
            with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # Fallbacks
    return {
        "code_red_cutoff": 75,
        "watch_cutoff": 40,
        "revenue_weight": 0.4,
        "renewal_weight": 0.3,
        "sentiment_weight": 0.3
    }

def simulate_sentiment_analysis(system_prompt, ticket_text):
    """
    Simulates Sentiment Analyst linguistic reasoning.
    Tone label, frustration score, churn signals, key phrases.
    """
    text_lower = ticket_text.lower()
    
    # 1. Detect churn signals (explicit migration / cancellation threats)
    churn_keywords = [
        "cancel", "termination", "non-renewal", "evaluate other", "evaluating other", 
        "alternative vendor", "migrate off", "migrating off", "offboarding", 
        "stop the renewal", "block the renewal", "look at alternatives", "other choices"
    ]
    churn_signals = any(kw in text_lower for kw in churn_keywords)
    
    # 2. Estimate frustration score and sentiment label
    frustration = 10
    
    # Check for all-caps words (excluding common small ones)
    words = re.findall(r'\b[A-Z]{4,}\b', ticket_text)
    if words:
        frustration += min(len(words) * 8, 25)
        
    # Check for exclamation marks
    excl_count = ticket_text.count("!")
    if excl_count > 0:
        frustration += min(excl_count * 5, 15)
        
    # Keywords frustration scoring
    frustrating_phrases = {
        "furious": 30,
        "unacceptable": 25,
        "sheer frustration": 25,
        "disaster": 20,
        "horrible": 20,
        "ripped off": 30,
        "overcharged": 20,
        "downtime": 15,
        "third time": 20,
        "broken": 15,
        "annoyed": 10,
        "minor": -10,
        "polite": -10,
        "hope you're having": -10
    }
    
    for phrase, score in frustrating_phrases.items():
        if phrase in text_lower:
            frustration += score
            
    # Cap frustration score
    frustration = max(0, min(frustration, 100))
    
    # Assign label based on frustration
    if frustration >= 80:
        label = "hostile" if "rip off" in text_lower or excl_count > 5 else "angry"
    elif frustration >= 40:
        label = "mildly_frustrated"
    else:
        label = "calm"
        
    # 3. Extract key phrases (sentences or clauses containing sentiment indicators)
    sentences = re.split(r'[.!?\n]+', ticket_text)
    key_phrases = []
    
    # Find matching indicator sentences
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        s_lower = s_clean.lower()
        
        # Check if this sentence contains any indicators
        has_indicator = False
        for kw in churn_keywords + list(frustrating_phrases.keys()) + ["!!!"]:
            if kw in s_lower:
                has_indicator = True
                break
        if has_indicator and len(s_clean) < 120 and s_clean not in key_phrases:
            key_phrases.append(s_clean)
            
    # Fallback key phrases if empty
    if not key_phrases:
        key_phrases = [s.strip() for s in sentences if s.strip()][:2]
    else:
        key_phrases = key_phrases[:3]
        
    # Construct response JSON
    response = {
        "sentiment_label": label,
        "frustration_score": frustration,
        "churn_signals_detected": churn_signals,
        "key_phrases": key_phrases
    }
    
    return json.dumps(response)

def simulate_risk_assessment(system_prompt, sentiment_verdict_json, crm_record_json):
    """
    Simulates Risk Assessor reasoning combining CRM facts with Sentiment Verdicts.
    Reasons about interaction effects, and maps to config-driven thresholds.
    """
    sentiment = json.loads(sentiment_verdict_json)
    crm = json.loads(crm_record_json)
    thresholds = load_thresholds()
    
    company = crm.get("company_name", "Unknown Company")
    revenue = crm.get("annual_revenue", 0)
    days_to_renewal = crm.get("days_until_renewal", 365)
    
    frustration = sentiment.get("frustration_score", 0)
    churn_signals = sentiment.get("churn_signals_detected", False)
    
    # 1. Base Score Calculations
    # ARR Exposure Score (0-100 scale: log-like mapping so Enterprise is high, small clients low)
    if revenue >= 200000:
        rev_score = 100
    elif revenue >= 100000:
        rev_score = 90
    elif revenue >= 40000:
        rev_score = 75
    elif revenue >= 10000:
        rev_score = 50
    else:
        rev_score = 10  # Very small ARR
        
    # Renewal Urgency Score (0-100 scale: closer renewal = higher score)
    if days_to_renewal <= 15:
        renewal_score = 100
    elif days_to_renewal <= 30:
        renewal_score = 90
    elif days_to_renewal <= 60:
        renewal_score = 75
    elif days_to_renewal <= 90:
        renewal_score = 60
    elif days_to_renewal <= 180:
        renewal_score = 35
    else:
        renewal_score = 10
        
    # Dissatisfaction Score
    dissat_score = frustration
    if churn_signals:
        dissat_score = max(dissat_score, 85)
        
    # Formula-based reference score
    w_rev = thresholds.get("revenue_weight", 0.4)
    w_ren = thresholds.get("renewal_weight", 0.3)
    w_sent = thresholds.get("sentiment_weight", 0.3)
    
    base_calc_score = (rev_score * w_rev) + (renewal_score * w_ren) + (dissat_score * w_sent)
    
    # 2. Semantic Interaction Rules (Agentic Judgement overriding rigid formula)
    final_score = base_calc_score
    rationale = ""
    recommended_action = ""
    
    # Scenario A: High revenue, imminent renewal, explicit or high dissatisfaction (CODE RED)
    if revenue >= 40000 and days_to_renewal <= 90 and (churn_signals or frustration >= 50):
        final_score = max(final_score, 85)
        rationale = f"High revenue account ({company}, ARR ${revenue:,}) is within imminent renewal window ({days_to_renewal} days) and exhibiting explicit dissatisfaction or churn indicators."
        recommended_action = f"Escalate immediately to Account Manager {crm.get('account_manager_name')} ({crm.get('account_manager_email')}). Conduct a wellness review and offer renewal concessions."
        
    # Scenario B: Calm but explicit cancellation threat from mid/high ARR (CODE RED)
    elif churn_signals and revenue >= 30000:
        final_score = max(final_score, 78)
        rationale = f"Client {company} (ARR ${revenue:,}) has explicitly asked about contract termination or is actively evaluating competitors, presenting an active churn risk despite a calm communication tone."
        recommended_action = f"Alert AM {crm.get('account_manager_name')} to reach out to the customer's procurement lead within 24 hours to address scaling/contract concerns."
        
    # Scenario C: Angry, high-frustration but low stakes/distant renewal (WATCH)
    elif frustration >= 70 and (revenue < 10000 or days_to_renewal > 120):
        final_score = max(min(final_score, 74), 45) # Keep in WATCH boundaries
        rationale = f"Client {company} displays a high level of frustration (score {frustration}/100), but has a smaller contract value (${revenue:,}) or a distant renewal date ({days_to_renewal} days)."
        recommended_action = "Assign to support queue with high priority. Log on watchlist and address the technical or billing complaint promptly to prevent escalation."
        
    # Scenario D: Calm/Mild issue, mid-value client, mid-renewal window (WATCH)
    elif frustration >= 35 and revenue >= 25000 and days_to_renewal <= 120:
        final_score = max(min(final_score, 74), 40)
        rationale = f"Mid-market account {company} is showing early signs of frustration (score {frustration}/100) within 4 months of renewal."
        recommended_action = "Add to watchlist. Account Manager should send a courtesy check-in email."
        
    # Scenario E: Low risk - polite small clients, or calm high-value far renewal
    else:
        final_score = min(final_score, 35)
        if revenue < 5000:
            rationale = f"Account {company} represents low financial exposure (ARR ${revenue:,}) and ticket contains standard support request with no churn threat."
        else:
            rationale = f"Enterprise client {company} has long-term contract stability ({days_to_renewal} days to renewal) and ticket tone is calm and constructive."
        recommended_action = "Handle ticket through standard customer support workflow. No escalation required."
        
    # 3. Apply configured cutoffs to determine final tier
    code_red_limit = thresholds.get("code_red_cutoff", 75)
    watch_limit = thresholds.get("watch_cutoff", 40)
    
    # Align score with the assigned tier boundaries
    if "imminent renewal" in rationale or "active churn risk" in rationale or final_score >= code_red_limit:
        tier = "CODE_RED"
        final_score = max(final_score, code_red_limit)
    elif "watchlist" in rationale or "watchlist" in recommended_action.lower() or final_score >= watch_limit:
        tier = "WATCH"
        # Make sure score is between watch and code_red limit
        final_score = max(watch_limit, min(final_score, code_red_limit - 1))
    else:
        tier = "LOW"
        final_score = min(final_score, watch_limit - 1)
        
    response = {
        "churn_risk_score": round(final_score, 1),
        "risk_tier": tier,
        "rationale": rationale,
        "recommended_action": recommended_action
    }
    
    return json.dumps(response)

def load_env():
    """Manually load env vars from .env in workspace root."""
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()

def call_gemini_api(prompt, system_instruction=None):
    """Calls Gemini API with json mode configuration."""
    load_env()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [
                {"text": system_instruction}
            ]
        }
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            res_json = response.json()
            candidates = res_json.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        else:
            print(f"[Gemini API] Request failed status={response.status_code}: {response.text}")
    except Exception as e:
        print(f"[Gemini API] Exception during request: {e}")
    return None

def simulate_acknowledgment_generation(sentiment_label, frustration_score, company_name):
    """
    Generates a customer acknowledgment email using Gemini API, with simulated fallback.
    """
    # 1. Try Gemini API
    prompt = (
        f"Generate a professional customer acknowledgment email.\n"
        f"Company Name: {company_name}\n"
        f"Customer Sentiment: {sentiment_label}\n"
        f"Frustration Score: {frustration_score}/100\n\n"
        f"Instructions:\n"
        f"- If the customer has high frustration (score >= 50 or sentiment is angry/hostile), "
        f"the email should apologize sincerely, acknowledge the urgency, and state that the ticket "
        f"is escalated to the dedicated Account Manager and senior engineering.\n"
        f"- Otherwise, it should be a polite receipt confirmation.\n"
        f"You must return a JSON object with the keys 'subject' and 'body' (and nothing else)."
    )
    
    gemini_response = call_gemini_api(prompt, "You are a customer success AI. Return only JSON.")
    if gemini_response:
        try:
            parsed = json.loads(gemini_response)
            if "subject" in parsed and "body" in parsed:
                return json.dumps(parsed)
        except Exception as e:
            print(f"[Gemini API] Parsing error for acknowledgment: {e}")

    # 2. Fallback to simulation
    is_high_risk = sentiment_label in ["angry", "hostile"] or frustration_score >= 50
    
    if is_high_risk:
        subject = f"URGENT: We have received your support request - {company_name}"
        body = (
            f"Dear {company_name} Team,\n\n"
            f"Thank you for contacting our support team. We sincerely apologize for the frustration "
            f"and difficulties this situation has caused. We completely understand the urgency and "
            f"seriousness of the issues you reported.\n\n"
            f"Please be assured that we have escalated this ticket directly to your dedicated Account Manager "
            f"and our senior technical engineering team for immediate, high-priority investigation. "
            f"We are actively working to resolve this as quickly as possible and will provide you with "
            f"a direct status update shortly.\n\n"
            f"Sincerely,\n"
            f"Customer Success & Escalation Team"
        )
    else:
        subject = f"Receipt Confirmation: Support Request Received - {company_name}"
        body = (
            f"Dear {company_name} Team,\n\n"
            f"Thank you for reaching out to us. We have received your support ticket regarding your recent query "
            f"and have added it to our technical queue.\n\n"
            f"Our standard support specialists are reviewing the details and will follow up with you as soon as "
            f"they have completed their initial assessment.\n\n"
            f"Best regards,\n"
            f"Customer Support Team"
        )
        
    return json.dumps({
        "subject": subject,
        "body": body
    })

def simulate_resolution_generation(manager_notes, company_name):
    """
    Translates technical manager resolution notes into a polite, warm, and professional customer email using Gemini API, with simulated fallback.
    """
    # 1. Try Gemini API
    prompt = (
        f"Translate these technical manager resolution notes into a polite, warm, and professional customer resolution email.\n"
        f"Company Name: {company_name}\n"
        f"Resolution Notes: {manager_notes}\n\n"
        f"You must return a JSON object with the keys 'subject' and 'body' (and nothing else)."
    )
    
    gemini_response = call_gemini_api(prompt, "You are a customer success AI. Return only JSON.")
    if gemini_response:
        try:
            parsed = json.loads(gemini_response)
            if "subject" in parsed and "body" in parsed:
                return json.dumps(parsed)
        except Exception as e:
            print(f"[Gemini API] Parsing error for resolution: {e}")

    # 2. Fallback to simulation
    subject = f"Resolved: Support Ticket Resolution - {company_name}"
    
    notes_formatted = manager_notes.strip()
    if notes_formatted:
        if not notes_formatted.endswith(('.', '!', '?')):
            notes_formatted += '.'
    else:
        notes_formatted = "The issue has been resolved by our engineering team."
        
    body = (
        f"Dear {company_name} Team,\n\n"
        f"We are writing to let you know that the issue you reported has been successfully resolved.\n\n"
        f"Resolution Details:\n"
        f"{notes_formatted}\n\n"
        f"We sincerely appreciate your patience and partnership as we worked through this. Please let us "
        f"know if there is anything else we can do to assist you or if you have any follow-up questions.\n\n"
        f"Warm regards,\n"
        f"Customer Support & Account Management"
    )
    
    return json.dumps({
        "subject": subject,
        "body": body
    })


