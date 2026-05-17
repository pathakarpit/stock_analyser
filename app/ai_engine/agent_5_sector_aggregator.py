import os
import csv
import json
import time
from datetime import datetime, timezone
from google import genai
from dotenv import load_dotenv

from app.core.utils import load_target_stocks

# Load environment variables
load_dotenv()

# ==========================================
# 1. AI CONFIGURATION (STRICT v1 CLIENT)
# ==========================================
api_key = os.getenv("GEMINI_API_KEY")
model_id = os.getenv("MODEL_1", "gemini-2.5-flash") 

if not api_key:
    print("CRITICAL: GEMINI_API_KEY missing. Exiting.")
    exit(1)

# Initialize the NEW v1 Client (replaces genai.configure)
client = genai.Client(api_key=api_key)

SYSTEM_PROMPT = """
You are a Macroeconomic Quantitative Analyst. 
Analyze the following daily financial news headlines for a specific market sector.
Synthesize the individual events and evaluate the collective macroeconomic sentiment.

Scoring Rubric (1-100):
- 80-100: Bullish (Favorable macro policies, sector-wide breakthroughs).
- 40-60: Neutral (Mixed updates, localized issues).
- 1-39: Bearish (Systemic risks, regulatory crackdowns).

Respond with ONLY a single integer score.
"""

# ==========================================
# 2. SECTOR AGGREGATION LOGIC
# ==========================================

def execute_agent_5():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    tickers = load_target_stocks()
    
    if not tickers:
        print("No tickers found.")
        return

    print(f"\n🌐 Booting Agent 5 (Sector Aggregator) for {today}...")

    # A. Group News by Sector
    sector_buckets = {}
    
    for ticker in tickers:
        json_path = os.path.join("data", ticker, "news", f"news_{today}.json")
        
        if not os.path.exists(json_path):
            continue
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
            
            for item in news_data:
                sector = item.get('sector', 'Unknown')
                news_text = item.get('news', '').strip()
                
                if sector == "Unknown" or not news_text:
                    continue
                    
                if sector not in sector_buckets:
                    sector_buckets[sector] = []
                
                sector_buckets[sector].append(f"[{ticker}]: {news_text}")
        except Exception as e:
            print(f"   [!] Error reading JSON for {ticker}: {e}")

    if not sector_buckets:
        print("   [-] No raw sector data found for today.")
        return

    # B. Generate Scores & Write to CSV
    output_file = os.path.join("data", "sector_sentiment_score.csv")
    file_exists = os.path.isfile(output_file)

    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(output_file) == 0:
            writer.writerow(['sector', 'sentiment_score', 'date'])
            
        for sector, news_list in sector_buckets.items():
            combined_news = "\n".join(news_list)
            prompt = f"{SYSTEM_PROMPT}\n\nAnalyze {sector} sector news:\n{combined_news}"
            
            try:
                # NEW v1 SDK Syntax
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config={"temperature": 0.1}
                )
                
                score_raw = response.text.strip()
                score = int(''.join(filter(str.isdigit, score_raw)))
                
                writer.writerow([sector, score, today])
                print(f"      ✓ {sector}: {score}/100")
                
                # Respect rate limits
                time.sleep(2)
                
            except Exception as e:
                print(f"\n[!!!] CRITICAL FAILURE for {sector}: {e}")
                exit(1) # Break the pipeline immediately to prevent data corruption

    print(f"\n🏁 AGENT 5 COMPLETE: Sector scores saved to data/sector_sentiment_score.csv")

if __name__ == "__main__":
    execute_agent_5()