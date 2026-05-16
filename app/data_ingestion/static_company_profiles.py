import os
import json
import yfinance as yf
from datetime import datetime, timezone
from sqlalchemy import text
from app.core.database import engine
from app.core.utils import load_target_stocks

def fetch_static_profiles(tickers):
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"\n🏢 Booting Static Profile Ingestion for {len(tickers)} companies...")
    
    profiles = []

    for ticker in tickers:
        print(f"   Fetching identity data for {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # If the API returns nothing, skip gracefully
            if not info or 'longBusinessSummary' not in info:
                print(f"      [!] Insufficient static data for {ticker}. Skipping.")
                continue

            record = {
                'stock_id': ticker,
                'company_name': info.get('longName', 'Unknown'),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'description': info.get('longBusinessSummary', 'No description available.'),
                'website': info.get('website', 'N/A'),
                'last_updated': today_date
            }
            
            # --- LOCAL DATA LAKE BACKUP ---
            save_dir = os.path.join(".", "data", ticker, "profile")
            os.makedirs(save_dir, exist_ok=True)
            
            file_path = os.path.join(save_dir, "static_profile.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(record, f, indent=4, ensure_ascii=False)
                
            profiles.append(record)

        except Exception as e:
            print(f"      [!] ERROR fetching {ticker}: {e}")

    # --- PUSH TO POSTGRESQL ---
    if profiles:
        print(f"\nPushing {len(profiles)} static profiles to PostgreSQL...")
        try:
            with engine.begin() as conn:
                for p in profiles:
                    upsert_query = text("""
                        INSERT INTO company_profile_static_store (
                            stock_id, company_name, sector, industry, description, website, last_updated
                        ) VALUES (
                            :stock_id, :company_name, :sector, :industry, :description, :website, :last_updated
                        )
                        ON CONFLICT (stock_id) DO UPDATE SET
                            company_name = EXCLUDED.company_name,
                            sector = EXCLUDED.sector,
                            industry = EXCLUDED.industry,
                            description = EXCLUDED.description,
                            website = EXCLUDED.website,
                            last_updated = EXCLUDED.last_updated;
                    """)
                    conn.execute(upsert_query, p)
            print("✅ SUCCESS: Static Company Profiles are perfectly synced.")
        except Exception as e:
            print(f"CRITICAL ERROR in DB Insert: {e}")

if __name__ == "__main__":
    INDIAN_TICKERS = load_target_stocks()
    if INDIAN_TICKERS:
        fetch_static_profiles(INDIAN_TICKERS)
    else:
        print("Pipeline aborted: No tickers loaded from target_stocks.json.")