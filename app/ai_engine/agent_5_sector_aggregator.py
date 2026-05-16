import os
import sys
import json
import csv
import time
from datetime import datetime, timezone
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Attempt to load target stocks
try:
    from app.core.utils import load_target_stocks
except ImportError:
    print("Pipeline aborted: No stocks found. Exiting.")
    sys.exit(0)

# --- CONFIGURATION ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("CRITICAL: GEMINI_API_KEY environment variable not set. Exiting.")
    sys.exit(1)

# Initialize the GenAI Client
client = genai.Client()
MODEL_ID = 'gemini-2.5-flash'

SYSTEM_PROMPT = """
You are a Macroeconomic Quantitative Analyst. 
You are provided with a complete daily compilation of raw financial news events for a specific market sector.
Your job is to read through this raw noise, synthesize the individual company events, and evaluate the collective macroeconomic sentiment for the entire sector.

You must respond ONLY with a valid JSON object matching this exact schema:
{
  "sector_sentiment_score": <integer>
}

Scoring Rules (1-100):
* 1-30: Bearish (Systemic risks, widespread earnings misses, harsh regulatory crackdowns, macro headwinds).
* 31-60: Neutral (Mixed earnings, routine operational updates, localized company issues not affecting the broader sector).
* 61-100: Bullish (Favorable macro policies, sector-wide earnings beats, major technological breakthroughs).
"""

def execute_agent_5(tickers):
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"\n🌐 Booting Agent 5 (Sector Macro Aggregator) for {today_date}...")
    print("   [i] Sourcing from RAW news files to capture full macro context.")
    
    # 1. Gather and Group Raw Data by Sector
    sector_buckets = {}
    
    for ticker in tickers:
        news_dir = os.path.join(".", "data", ticker, "news")
        # Pointing directly to Agent 1's raw output
        json_file = os.path.join(news_dir, f"news_{today_date}.json")
        
        if not os.path.exists(json_file):
            continue
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                daily_raw_news = json.load(f)
                
            if not daily_raw_news:
                continue
                
            # Agent 1 formats each item as a dict containing 'sector' and 'news'
            for item in daily_raw_news:
                sector = item.get('sector', 'Unknown')
                news_text = item.get('news', '').strip()
                
                if sector == "Unknown" or not news_text:
                    continue # Skip unknown sectors to avoid noisy macro scores
                    
                if sector not in sector_buckets:
                    sector_buckets[sector] = []
                    
                # Append the ticker name to give the LLM context of which company did what
                sector_buckets[sector].append(f"[{ticker}]: {news_text}")
                    
        except Exception as e:
            print(f"   [!] Error reading raw news JSON for {ticker}: {e}")
            continue

    if not sector_buckets:
        print("   [-] No raw sector data available to aggregate today. Exiting.")
        return

    print(f"   Compiled raw news for {len(sector_buckets)} distinct sectors. Requesting Macro Analysis...")
    
    # 2. Setup output file
    output_dir = os.path.join(".", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "sector_sentiment_score.csv")
    file_exists = os.path.isfile(output_file)
    
    # 3. Analyze each sector and append to CSV
    with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        if not file_exists:
            writer.writerow(['sector', 'sentiment_score', 'date'])
            
        for sector, raw_news_list in sector_buckets.items():
            # Join all raw daily headlines/summaries into a single text block
            combined_news = "\n".join(raw_news_list)
            prompt = f"{SYSTEM_PROMPT}\n\nAnalyze the following raw daily events for the {sector} sector:\n{combined_news}"
            
            try:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                ai_output = json.loads(response.text)
                score = ai_output.get("sector_sentiment_score", 50)
                
                writer.writerow([sector, score, today_date])
                print(f"      [+] Sector: {sector} | Processed {len(raw_news_list)} raw events | Macro Score: {score}/100")
                
                time.sleep(4) # Respect free tier rate limits
                
            except Exception as e:
                print(f"      [!] AI Processing Error for {sector} sector: {e}")

    print(f"=====================================================")
    print(f"🏁 AGENT 5 COMPLETE: Sector macro scores saved locally.")
    print(f"=====================================================")

if __name__ == "__main__":
    TARGET_TICKERS = load_target_stocks()
    if not TARGET_TICKERS:
        print("Pipeline aborted: No stocks found. Exiting.")
        sys.exit(0)
        
    execute_agent_5(TARGET_TICKERS)