import os
import sys
import json
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the centralized database engine
try:
    from app.core.database import engine 
except ImportError as e:
    print(f"Error loading database engine: {e}")
    sys.exit(1)

# --- CONFIGURATION ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("CRITICAL: GEMINI_API_KEY environment variable not set. Exiting.")
    sys.exit(1)

# Initialize the GenAI Client
client = genai.Client()
MODEL_ID = 'gemini-2.5-flash'

SYSTEM_PROMPT = """
You are the Master Quantitative & Qualitative Analyst (Agent 6) for an institutional hedge fund.
Your job is to synthesize distinct data streams into a final, actionable trading thesis.

You will be provided with:
1. Granular Fundamental Scores (1-10 scale) covering Valuation, Profitability, Solvency, Momentum, Capital Efficiency, and Risk.
2. Technical Pattern Score (1-100 scale) and a brief technical setup description.
3. Market Sentiment Score (1-100 scale) - Pay close attention to the AGE of this data. Old news should be discounted.
4. User Risk Tolerance (e.g., Conservative, Moderate, Aggressive).
5. User Investment Horizon (e.g., Day Trader, Swing Trader, Long-term).

Your task is to weigh these inputs based on the user's specific profile. 
- A Long-term Conservative investor should anchor heavily on Solvency/Profitability and ignore short-term Sentiment/Pattern noise. 
- A Swing/Day Trader should anchor heavily on Momentum, Pattern Scores, and recent Sentiment.

You must respond ONLY with a valid JSON object matching this exact schema:
{
  "final_actionable_score": <integer 1-100, representing the tailored confidence level of the asset for this specific user>,
  "recommendation": "<Strictly one of: BUY, HOLD, SELL>",
  "thesis": "A concise, 3-4 sentence explanation of exactly WHY this recommendation was made, explicitly referencing how the specific sub-scores, data age, and user profile factored into the decision."
}
"""

def get_latest_record(table_name, stock_id):
    """Fetches the most recent record from a table and calculates its age in days."""
    with engine.connect() as conn:
        query = text(f"""
            SELECT * FROM {table_name} 
            WHERE stock_id = :stock 
            ORDER BY date DESC LIMIT 1
        """)
        result = conn.execute(query, {"stock": stock_id}).mappings().fetchone()
        
        if result:
            today = datetime.now(timezone.utc).date()
            days_old = (today - result['date']).days
            return dict(result), max(0, days_old)
        return None, None

def get_sector_proxy_sentiment(sector):
    """Fetches the latest macro sector sentiment if individual stock sentiment is missing."""
    if not sector or sector == "Unknown":
        return "UNAVAILABLE (No sector identified)"
        
    csv_path = os.path.join(".", "data", "sector_sentiment_score.csv")
    if not os.path.exists(csv_path):
        return "UNAVAILABLE (No sector macro data found)"
        
    try:
        df = pd.read_csv(csv_path)
        sector_df = df[df['sector'] == sector].copy()
        if not sector_df.empty:
            sector_df['date'] = pd.to_datetime(sector_df['date'])
            latest_row = sector_df.sort_values(by='date', ascending=False).iloc[0]
            
            today = datetime.now(timezone.utc).date()
            days_old = (today - latest_row['date'].date()).days
            return f"{latest_row['sentiment_score']}/100 (Sector Proxy - {max(0, days_old)} days old)"
    except Exception:
        pass
        
    return "UNAVAILABLE"

def generate_investment_thesis(stock_id, risk_tolerance, investment_horizon):
    """The core Decision Engine execution function."""
    print(f"\n🧠 Executing Agent 6 (Decision Engine) for {stock_id}...")
    print(f"   [User Profile] Risk: {risk_tolerance} | Horizon: {investment_horizon}")

    # 1. Fetch Data (Tier 1: Lookback)
    fund_data, fund_age = get_latest_record("fundamental_segment_score_store", stock_id)
    pat_data, pat_age = get_latest_record("pattern_score_store", stock_id)
    sent_data, sent_age = get_latest_record("aggregated_sentiment_score_store", stock_id)

    # 2. Handle Missing Data (Tier 3: Hard Abort)
    if not fund_data:
        print("   [!] CRITICAL ABORT: Missing Fundamental Baseline. Bypassing LLM.")
        return {
            "final_actionable_score": 0,
            "recommendation": "INSUFFICIENT DATA",
            "thesis": "Cannot evaluate asset. Core fundamental and financial health data is completely missing from the database."
        }

    # Extract Sector for potential proxy use
    # Try to get it from sentiment data, otherwise default to Unknown
    sector = sent_data.get('sector', 'Unknown') if sent_data else 'Unknown'

    # 3. Format Fundamental Payload
    fund_payload = f"""
    - Data Age: {fund_age} days old
    - Total Overarching Score: {fund_data.get('total_score', 'N/A')} / 10
    - Valuation Score: {fund_data.get('valuation_score', 'N/A')} / 10
    - Profitability Score: {fund_data.get('profitability_score', 'N/A')} / 10
    - Solvency Score: {fund_data.get('solvency_score', 'N/A')} / 10
    - Momentum Score: {fund_data.get('momentum_score', 'N/A')} / 10
    - Capital Efficiency Score: {fund_data.get('capital_efficiency_score', 'N/A')} / 10
    - Risk Performance Score: {fund_data.get('risk_performance_score', 'N/A')} / 10
    """

    # 4. Format Pattern Payload
    if pat_data:
        pat_payload = f"Score: {pat_data.get('score', 'N/A')} / 100 | Setup: {pat_data.get('brief', 'None')} | Data Age: {pat_age} days old"
    else:
        pat_payload = "UNAVAILABLE"

    # 5. Format Sentiment Payload (Tier 2: Sector Proxy applied if needed)
    if sent_data:
        sent_payload = f"Score: {sent_data.get('sentiment_score', 'N/A')} / 100 | Data Age: {sent_age} days old"
    else:
        print("   [-] Stock-specific sentiment missing. Attempting Sector Proxy injection...")
        sent_payload = get_sector_proxy_sentiment(sector)

    # 6. Construct the Master Prompt
    prompt = f"""
    {SYSTEM_PROMPT}
    
    Analyze the following asset tailored to this specific user:
    - Asset: {stock_id}
    - User Risk Tolerance: {risk_tolerance}
    - User Investment Horizon: {investment_horizon}
    
    [FUNDAMENTAL DATA]
    {fund_payload}
    
    [TECHNICAL PATTERN DATA]
    {pat_payload}
    
    [MARKET SENTIMENT DATA]
    {sent_payload}
    """
    
    # 7. Call the Master AI
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2 # Low temperature for highly deterministic reasoning
            )
        )
        
        decision_output = json.loads(response.text)
        print(f"   [+] Decision Complete: {decision_output.get('recommendation')} (Score: {decision_output.get('final_actionable_score')})")
        
        return decision_output
        
    except Exception as e:
        print(f"   [!] AI Processing Error in Decision Engine for {stock_id}: {e}")
        return {
            "final_actionable_score": 0,
            "recommendation": "ERROR",
            "thesis": f"The Decision Engine failed to process the request due to an AI generation error: {e}"
        }

# --- For isolated testing ---
if __name__ == "__main__":
    # Example execution if run directly from terminal
    test_stock = "RELIANCE.NS"
    test_risk = "Moderate"
    test_horizon = "Swing Trader"
    
    result = generate_investment_thesis(test_stock, test_risk, test_horizon)
    print("\n--- FINAL JSON OUTPUT ---")
    print(json.dumps(result, indent=2))