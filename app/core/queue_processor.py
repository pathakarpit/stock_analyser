import os
import json
import re
import yfinance as yf
from dotenv import load_dotenv

# Import existing modularized functions exactly as defined in your files
try:
    from app.data_ingestion.market_historical_data import fetch_historical_prices
    from app.data_ingestion.static_company_profiles import fetch_static_profiles
    from app.data_ingestion.deep_financials import fetch_deep_financials
except ImportError as e:
    print(f"CRITICAL: Linkage to ingestion modules failed: {e}")

load_dotenv()

# Path Configuration
PROJECT_DIR = "/home/sunny/workspace/project_stock_analyser"
TARGET_JSON = os.path.join(PROJECT_DIR, "app/config/target_stocks.json")
QUEUE_FILE = os.path.join(PROJECT_DIR, "data", "request_queue.txt")

def resolve_to_nse_ticker(query):
    """
    Finds the most accurate NSE ticker for a given query.
    Specifically handles aliases like 'Westside' -> 'TRENT.NS'
    """
    # Manual mapping for common brand names that differ from company names
    alias_map = {
        "westside": "TRENT.NS",
        "west side": "TRENT.NS",
        "jio": "JIOFIN.NS",
        "amarraja": "ARE&M.NS", # Amara Raja Energy & Mobility
        "pedilite": "PIDILITIND.NS"
    }
    
    clean_query = query.lower().strip()
    if clean_query in alias_map:
        return alias_map[clean_query]

    try:
        # Search specifically within the NSE context
        search = yf.Search(f"NSE: {query}", max_results=5)
        if search.quotes:
            for quote in search.quotes:
                symbol = str(quote.get('symbol', ''))
                # Strict requirement for .NS (NSE) symbols to ensure DB compatibility
                if symbol.endswith(".NS"):
                    return symbol
            
            # Fallback: Check if top result is a BSE ticker (.BO) and convert it
            top_symbol = search.quotes[0]['symbol']
            if ".BO" in top_symbol:
                return top_symbol.replace(".BO", ".NS")
    except Exception:
        return None
    return None

def parse_messy_request_queue():
    """Handles commas, newlines, and duplicate/messy inputs."""
    if not os.path.exists(QUEUE_FILE) or os.path.getsize(QUEUE_FILE) == 0:
        return set()

    with open(QUEUE_FILE, "r") as f:
        content = f.read()

    # Split by commas OR newlines
    raw_list = re.split(r'[,\n\r]+', content)
    # Deduplicate and strip
    cleaned_requests = {item.strip().lower() for item in raw_list if item.strip()}
    
    # Clear the file immediately to acknowledge receipt
    open(QUEUE_FILE, 'w').close()
    return cleaned_requests

def execute_backfill_pipeline():
    print("\n--- 🔄 Stock Expansion & Backfill Engine ---")

    # 1. Parse raw requests
    requests = parse_messy_request_queue()
    if not requests:
        print("Queue is empty.")
        return

    # 2. Load existing target_stocks.json
    if not os.path.exists(TARGET_JSON):
        print(f"ERROR: {TARGET_JSON} not found.")
        return

    with open(TARGET_JSON, "r") as f:
        config = json.load(f)

    # 3. Handle 'default_portfolio' strictly
    # If the JSON is a simple list, we treat it as the portfolio
    if isinstance(config, list):
        portfolio = config
    else:
        portfolio = config.get("default_portfolio", [])

    existing_tickers = set(portfolio)
    new_tickers_to_backfill = []

    # 4. Resolve and Validate
    print(f"Resolving {len(requests)} unique requests...")
    for query in requests:
        ticker = resolve_to_nse_ticker(query)
        
        if ticker and ticker not in existing_tickers:
            print(f"✅ Resolved: '{query}' -> {ticker}")
            portfolio.append(ticker)
            existing_tickers.add(ticker)
            new_tickers_to_backfill.append(ticker)
        elif ticker in existing_tickers:
            print(f"ℹ️ {ticker} already in default_portfolio. Skipping.")

    if not new_tickers_to_backfill:
        print("No new valid NSE tickers found to process.")
        return

    # 5. Save back to target_stocks.json (Compatible Update)
    if isinstance(config, list):
        config = portfolio
    else:
        config["default_portfolio"] = portfolio

    with open(TARGET_JSON, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Master target list updated.")

    # 6. Targeted Data Backfill
    print(f"🚀 Initializing Backfill for: {new_tickers_to_backfill}")
    try:
        # These functions now only process the NEW stocks
        fetch_static_profiles(new_tickers_to_backfill)
        fetch_historical_prices(new_tickers_to_backfill, period="1y")
        fetch_deep_financials(new_tickers_to_backfill)
        
        print("\n✅ Targeted Backfill Complete. Ready for next daily run.")
    except Exception as e:
        print(f"❌ Backfill failed: {e}")

if __name__ == "__main__":
    execute_backfill_pipeline()