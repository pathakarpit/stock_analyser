import os
import sys
import csv
import json
import time
import argparse
from google import genai
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. AI CONFIGURATION
# ==========================================
api_key = os.getenv("GEMINI_API_KEY")
model_id = os.getenv("MODEL_1", "gemini-2.5-flash") 

if not api_key:
    raise EnvironmentError("CRITICAL: GEMINI_API_KEY missing. Pipeline halted.")

client = genai.Client(api_key=api_key)

# ==========================================
# 2. SENTIMENT LOGIC
# ==========================================
def get_sentiment_score(ticker, headline, max_retries=3, delay=10):
    """Hits the AI for a single news item score with retry logic."""
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
                print(f"      ❌ Max retries reached. Skipping.")
                return None

# ==========================================
# 3. FILE PROCESSING (WITH DEDUPLICATION)
# ==========================================
def process_targeted_news(ticker):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
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

    # --- SMART DEDUPLICATION ---
    # Find which headlines have already been scored today so we don't waste AI tokens
    already_processed_headlines = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('capture_date') == today:
                    already_processed_headlines.add(row.get('overview', '').strip())

    processed_count = 0
    skipped_count = 0
    already_done_count = 0

    with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
            writer.writerow(['stock', 'sector', 'news_date', 'capture_date', 'overview', 'score'])

        for item in news_data:
            headline = item.get('news', '').strip()
            sector = item.get('sector', 'General')
            news_date = item.get('date', today) 

            if not headline:
                continue

            overview = headline.replace(',', '')

            # Check if we already scored this exact headline today
            if overview in already_processed_headlines:
                already_done_count += 1
                continue

            score = get_sentiment_score(ticker, headline)
            
            if score is None:
                skipped_count += 1
                continue
            
            writer.writerow([ticker, sector, news_date, today, overview, score])
            processed_count += 1
            
    status = f"✓ {ticker}: Processed {processed_count} NEW items."
    if already_done_count > 0:
        status += f" (Ignored {already_done_count} already scored)"
    if skipped_count > 0:
        status += f" (Skipped {skipped_count} due to API errors)"
        
    return status

# ==========================================
# 4. TARGETED ORCHESTRATOR
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Targeted AI News Sentiment Retry Logic")
    parser.add_argument(
        'tickers', 
        metavar='T', 
        type=str, 
        nargs='+', 
        help='List of specific stock tickers to retry (e.g., TCS.NS INFY.NS)'
    )
    args = parser.parse_args()

    # Convert to uppercase to ensure match with directories/database
    target_tickers = [t.upper() for t in args.tickers]

    print(f"\n🚀 Running TARGETED Sentiment Engine for: {', '.join(target_tickers)}")

    for ticker in target_tickers:
        try:
            status = process_targeted_news(ticker)
            print(status)
        except Exception as e:
            print(f"\n[!!!] CRITICAL ERROR processing {ticker}: {e}")

    print("\n🏁 Targeted Retry Complete.")