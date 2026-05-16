import os
import sys
import math
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- IMPORT CENTRALIZED RESOURCES ---
# Attempt to load target stocks and the centralized database engine
try:
    from app.core.utils import load_target_stocks
    from app.core.database import engine 
except ImportError as e:
    print(f"Pipeline aborted: Core modules not found. Error: {e}")
    sys.exit(0)

# Decay constant (0.1 = approx 7 day half-life)
DECAY_CONSTANT = 0.1 

def calculate_time_decayed_score(df):
    """
    Applies exponential time decay and urgency multipliers 
    to calculate a single weighted average sentiment score.
    """
    today = pd.to_datetime(datetime.now(timezone.utc).date())
    
    total_weighted_score = 0
    total_weight = 0
    
    for _, row in df.iterrows():
        try:
            # Parse the date and calculate delta t (days old)
            news_date = pd.to_datetime(row['news_date']).tz_localize(None).date()
            days_old = (today.date() - news_date).days
            
            # Prevent negative days if there's a timezone overlap mismatch
            days_old = max(0, days_old)
            
            # 1. Base Exponential Decay Weight
            base_weight = math.exp(-DECAY_CONSTANT * days_old)
            
            # 2. Urgency/Relevance Multiplier from LLM Overview
            overview_text = str(row['overview']).lower()
            multiplier = 1.0
            
            # Apply multipliers based on LLM extraction
            if "urgency: high" in overview_text or "relevance: high" in overview_text:
                multiplier = 1.5
            elif "urgency: low" in overview_text or "relevance: low" in overview_text:
                multiplier = 0.5
                
            final_weight = base_weight * multiplier
            
            # 3. Add to accumulators
            score = float(row['score'])
            total_weighted_score += (score * final_weight)
            total_weight += final_weight
            
        except Exception as e:
            continue # Skip malformed rows
            
    # Calculate the final weighted average
    if total_weight == 0:
        return 50.0 # Default neutral if math fails or no valid data
        
    return round(total_weighted_score / total_weight, 2)

def execute_agent_4(tickers):
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"\n🧮 Booting Agent 4 (Time-Decay Aggregator) for {today_date}...")

    # We use the imported 'engine' object directly
    with engine.begin() as conn:
        for ticker in tickers:
            news_dir = os.path.join(".", "data", ticker, "news")
            csv_file = os.path.join(news_dir, "news_score.csv")
            
            if not os.path.exists(csv_file):
                print(f"   [-] No scored news history found for {ticker}. Skipping.")
                continue
            
            # Read the historical data lake
            try:
                df = pd.read_csv(csv_file)
            except Exception as e:
                print(f"   [!] Error reading CSV for {ticker}: {e}")
                continue
                
            if df.empty:
                continue
                
            # Filter to only look at the last 30 days of news to optimize math
            df['news_date'] = pd.to_datetime(df['news_date'], errors='coerce')
            
            # Ensure safe timezone handling for filtering
            df['naive_date'] = df['news_date'].dt.tz_localize(None)
            cutoff_date = pd.to_datetime(today_date).tz_localize(None) - pd.Timedelta(days=30)
            
            recent_df = df[df['naive_date'] >= cutoff_date]
            
            if recent_df.empty:
                print(f"   [-] No recent news within 30 days for {ticker}.")
                continue
            
            print(f"   Calculating aggregate score for {ticker} using {len(recent_df)} historical articles...")
            
            final_score = calculate_time_decayed_score(recent_df)
            sector = recent_df.iloc[0].get('sector', 'Unknown')
            
            # Insert into PostgreSQL using standard Upsert targeting your exact schema
            upsert_query = text("""
                INSERT INTO aggregated_sentiment_score_store (stock_id, sector, date, sentiment_score)
                VALUES (:stock_id, :sector, :date, :sentiment_score)
                ON CONFLICT (stock_id, date) 
                DO UPDATE SET sentiment_score = EXCLUDED.sentiment_score, sector = EXCLUDED.sector;
            """)
            
            conn.execute(upsert_query, {
                "stock_id": ticker,
                "sector": sector,
                "date": today_date,
                "sentiment_score": final_score
            })
            
            print(f"      [+] Final Aggregate Sentiment for {ticker}: {final_score}/100")

if __name__ == "__main__":
    TARGET_TICKERS = load_target_stocks()
    if not TARGET_TICKERS:
        print("Pipeline aborted: No stocks found. Exiting.")
        sys.exit(0)
        
    execute_agent_4(TARGET_TICKERS)