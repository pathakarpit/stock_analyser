import os
import csv
import json
import time
import concurrent.futures
from google import genai
from datetime import datetime, timezone
from dotenv import load_dotenv

from app.core.utils import load_target_stocks

load_dotenv()

# ==========================================
# 1. AI CONFIGURATION (STRICT MODEL 1)
# ==========================================
api_key = os.getenv("GEMINI_API_KEY")
model_id = os.getenv("MODEL_1", "gemini-2.5-flash") 

if not api_key:
    raise EnvironmentError("CRITICAL: GEMINI_API_KEY missing. Pipeline halted.")

client = genai.Client(api_key=api_key)

# ==========================================
# 2. SENTIMENT LOGIC (AGENT 2 & 3)
# ==========================================

def get_sentiment_score(ticker, headline, max_retries=3, delay=10):
    """Hits the AI for a single news item score. Includes retry logic for API limits."""
    prompt = f"""
Act as a Senior Equity Analyst. Analyze the sentiment of the following news headline for {ticker}.
Headline: '{headline}'

Scoring Guidelines:
- 80-100 (Strong Bullish): Major earnings beats, high-value contract wins, or breakthrough product launches.
- 60-79 (Bullish): Positive analyst upgrades, routine dividend increases, or favorable macro tailwinds.
- 40-59 (Neutral): Routine operational updates, minor executive changes, or non-material news.
- 20-39 (Bearish): Earnings misses, minor legal disputes, or sector-wide slowdowns.
- 0-19 (Strong Bearish): Major fraud allegations, bankruptcy risks, or catastrophic regulatory crackdowns.

Constraint: Respond with ONLY a single integer between 0 and 100. Do not provide any text, reasoning, or punctuation.
"""
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config={"temperature": 0.1}
            )
            
            score_raw = response.text.strip()
            score = int(''.join(filter(str.isdigit, score_raw)))
            return max(0, min(100, score))
            
        except Exception as e:
            print(f"      [!] API Error on '{ticker}' (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"      ⏳ Sleeping for {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                print(f"      ❌ Max retries reached for headline. Skipping.")
                return None

# ==========================================
# 3. FILE PROCESSING
# ==========================================

def process_today_news(ticker):
    """Reads raw JSON capture and writes to news_score.csv."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Path to the raw capture from Agent 1
    news_dir = os.path.join("data", ticker, "news")
    json_path = os.path.join(news_dir, f"news_{today}.json")
    csv_path = os.path.join(news_dir, "news_score.csv")

    if not os.path.exists(json_path):
        return f"[-] {ticker}: No JSON news file found for today."

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            news_data = json.load(f)
    except Exception as e:
        return f"[-] {ticker}: Failed to read JSON. Error: {e}"

    if not news_data:
        return f"[-] {ticker}: JSON file is empty."

    # Prepare CSV writing
    processed_count = 0
    skipped_count = 0
    with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Check if we need to write the header
        if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
            writer.writerow(['stock', 'sector', 'news_date', 'capture_date', 'overview', 'score'])

        # Iterate through EVERY news item in the JSON
        for item in news_data:
            headline = item.get('news', '').strip()
            sector = item.get('sector', 'General')
            # Assuming Agent 1 stored the news date, otherwise use today
            news_date = item.get('date', today) 

            if not headline:
                continue

            # Generate score with built-in retry logic
            score = get_sentiment_score(ticker, headline)
            
            # If the score is None (API failed 3 times), skip appending to avoid corrupting data
            if score is None:
                skipped_count += 1
                continue
            
            # Overview is the headline with commas removed for CSV safety
            overview = headline.replace(',', '')
            
            writer.writerow([ticker, sector, news_date, today, overview, score])
            processed_count += 1
            
    skip_msg = f" (Skipped {skipped_count} due to API errors)" if skipped_count > 0 else ""
    return f"✓ {ticker}: Processed {processed_count} news items into news_score.csv{skip_msg}"

# ==========================================
# 4. ORCHESTRATOR
# ==========================================

def execute_sentiment_engine():
    tickers = load_target_stocks()
    if not tickers:
        print("No tickers found.")
        return

    print(f"🚀 Running Agents 2 & 3: Individual News Sentiment (Model: {model_id})")

    # Sequential processing
    for ticker in tickers:
        try:
            status = process_today_news(ticker)
            print(status)
        except Exception as e:
            # We log the error but NO LONGER exit(1). The pipeline will continue to the next stock.
            print(f"\n[!!!] LOCAL ERROR processing {ticker}: {e}")
            print(f"Continuing to the next ticker...")

    print("\n🏁 Agents 2 & 3 Complete.")

if __name__ == "__main__":
    execute_sentiment_engine()