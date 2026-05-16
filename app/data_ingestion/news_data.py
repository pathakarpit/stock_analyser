import os
import sys
import json
import time
from datetime import datetime, timezone
import yfinance as yf

# Attempt to load the utility function, fail gracefully if missing
try:
    from app.core.utils import load_target_stocks
except ImportError:
    print("Pipeline aborted: No stocks found. Exiting.")
    sys.exit(0)

# --- UPDATE 1: Add 'sector' as a required argument here ---
def stockwire_formatter(ticker, sector, raw_news_list):
    """
    The 'Stockwire' sorting block.
    Transforms raw API news into the strict schema:
    [stock, sector, news_date, capture_date, news]
    """
    formatted_news = []
    capture_date = datetime.now(timezone.utc).isoformat()

    for item in raw_news_list:
        content = item.get('content', {})
        
        headline = content.get('title', '')
        summary = content.get('summary', '') 
        
        news_text = f"{headline}. {summary}".strip()
        
        pub_date_str = content.get('pubDate')
        provider_pub_time = item.get('providerPublishTime')
        
        if pub_date_str:
            news_date = pub_date_str 
        elif provider_pub_time:
            news_date = datetime.fromtimestamp(provider_pub_time, timezone.utc).isoformat()
        else:
            news_date = capture_date

        if news_text and len(news_text) > 10 and news_text != ". ":
            formatted_news.append({
                "stock": ticker,
                "sector": sector, # Now uses the dynamically fetched sector
                "news_date": news_date,
                "capture_date": capture_date,
                "news": news_text
            })
    
    return formatted_news

def execute_news_ingestion(tickers):
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"\n📰 Booting News Ingestion Engine (Agent 1) for {today_date}...")
    
    for ticker in tickers:
        print(f"   Fetching news for {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            raw_news = stock.news
            
            # --- UPDATE 2: Fetch the sector dynamically from yfinance ---
            # Using .get() ensures it defaults gracefully if yfinance doesn't have the sector
            stock_info = stock.info
            dynamic_sector = stock_info.get('sector', 'Unknown')
            
            if not raw_news:
                print(f"      [-] No news found for {ticker} today.")
                continue
            
            # --- UPDATE 3: Pass the dynamic_sector to the formatter ---
            structured_news = stockwire_formatter(ticker, dynamic_sector, raw_news)
            
            if not structured_news:
                print(f"      [!] 0 articles successfully formatted for {ticker}. API schema may have changed.")
                continue

            save_dir = os.path.join(".", "data", ticker, "news")
            os.makedirs(save_dir, exist_ok=True)
            
            file_path = os.path.join(save_dir, f"news_{today_date}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(structured_news, f, indent=4, ensure_ascii=False)
                
            print(f"      [+] SUCCESS: Saved {len(structured_news)} articles to {file_path} (Sector: {dynamic_sector})")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"      [!] ERROR fetching news for {ticker}: {e}")

if __name__ == "__main__":
    TARGET_TICKERS = load_target_stocks()
    
    if not TARGET_TICKERS:
        print("Pipeline aborted: No stocks found. Exiting.")
        sys.exit(0)
        
    execute_news_ingestion(TARGET_TICKERS)