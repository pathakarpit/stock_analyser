import os
import json
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text
from google import genai
from dotenv import load_dotenv

# Load database engine from your core module
from app.core.database import engine

load_dotenv()

# --- CONFIGURATION ---
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = os.getenv("MODEL_2", "gemini-2.5-flash")

if not API_KEY:
    exit(1)

client = genai.Client(api_key=API_KEY)

# ==========================================
# 1. DATABASE DATA RETRIEVAL
# ==========================================

def get_db_latest_record(table_name, stock_id):
    """Fetches the latest technical or fundamental score from PostgreSQL."""
    query = text(f"""
        SELECT * FROM {table_name} 
        WHERE stock_id = :stock 
        ORDER BY date DESC LIMIT 1
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"stock": stock_id}).mappings().fetchone()
            if result:
                data = dict(result)
                today = datetime.now(timezone.utc).date()
                # Handle date parsing
                d = data['date']
                if isinstance(d, str):
                    d = datetime.strptime(d, '%Y-%m-%d').date()
                days_old = max(0, (today - d).days)
                return data, days_old
    except Exception as e:
        print(f"   [!] DB Error ({table_name}): {e}")
    return None, 0

# ==========================================
# 2. LOCAL CSV DATA RETRIEVAL
# ==========================================

def get_csv_latest_record(file_path):
    """Fetches the latest sentiment data from your local CSV files."""
    if not os.path.exists(file_path):
        return None, 0
    try:
        df = pd.read_csv(file_path)
        if df.empty: return None, 0
        latest = df.iloc[-1].to_dict()
        
        # Calculate Age
        date_col = next((c for c in ['news_date', 'capture_date', 'date'] if c in latest), None)
        days_old = 0
        if date_col:
            today = datetime.now(timezone.utc).date()
            d = pd.to_datetime(latest[date_col]).date()
            days_old = max(0, (today - d).days)
        return latest, days_old
    except:
        return None, 0

# ==========================================
# 3. HYBRID SYNTHESIS ENGINE
# ==========================================

def generate_investment_thesis(stock_id, risk_tolerance, investment_horizon):
    print(f"🧠 Synthesizing Final Verdict for {stock_id} (Hybrid Data Mode)...")

    # PILLAR 1 & 2: Database Sourcing
    fund_data, fund_age = get_db_latest_record("fundamental_segment_score_store", stock_id)
    pat_data, pat_age = get_db_latest_record("pattern_score_store", stock_id)

    # PILLAR 3: CSV Sourcing
    news_path = os.path.join("data", stock_id, "news", "news_score.csv")
    news_data, news_age = get_csv_latest_record(news_path)
    
    sector_path = os.path.join("data", "sector_sentiment_score.csv")
    sector_data, _ = get_csv_latest_record(sector_path)

    # Construct the Comprehensive AI Payload
    context = f"""
    Asset: {stock_id} | User Risk: {risk_tolerance} | Horizon: {investment_horizon}

    [FUNDAMENTAL PILLAR]:
    Data: {fund_data if fund_data else "No Fundamental Scores found in DB"}
    Recency: {fund_age} days old

    [TECHNICAL PILLAR]:
    Data: {pat_data if pat_data else "No Technical Patterns found in DB"}
    Recency: {pat_age} days old

    [SENTIMENT PILLAR]:
    Latest News Score: {news_data.get('score') if news_data else 'N/A'} (Age: {news_age}d)
    Macro Sector Context: {sector_data if sector_data else 'N/A'}
    """

    try:
        prompt = f"""
        Act as a Senior Hedge Fund Manager. Synthesize this data into a JSON thesis.
        Logic: {risk_tolerance} risk and {investment_horizon} horizon.
        
        Respond ONLY with JSON:
        {{
          "final_actionable_score": <int 1-100>,
          "recommendation": "<BUY, HOLD, SELL>",
          "thesis": "Concise justification referencing scores and data recency."
        }}

        DATA FOR ANALYSIS:
        {context}
        """

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config={"temperature": 0.1}
        )
        
        # Clean potential markdown
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
        
    except Exception as e:
        return {
            "final_actionable_score": 0,
            "recommendation": "ERROR",
            "thesis": f"System Error: {str(e)}"
        }

if __name__ == "__main__":
    # Test script
    result = generate_investment_thesis("BHARTIARTL.NS", "Moderate", "Swing Trader")
    print(json.dumps(result, indent=2))