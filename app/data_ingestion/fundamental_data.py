import os
import json
import yfinance as yf
from datetime import datetime, timezone
from app.core.utils import load_target_stocks

def fetch_fundamental_data_locally(tickers):
    """
    PURE INGESTION: Fetches core static financial ratios using yfinance 
    and saves them locally. No calculations, no SQL insertion.
    """
    print(f"Executing STATIC FUNDAMENTALS local fetch for {len(tickers)} tickers...")
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    for ticker in tickers:
        print(f"Fetching base fundamentals for {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info or 'symbol' not in info:
                print(f"   WARNING: Incomplete data for {ticker}. Skipping.")
                continue
                
            record = {
                'stock_id': ticker,
                'date': today_date,
                'beta': info.get('beta'),
                'roe': info.get('returnOnEquity'),
                'margins': info.get('profitMargins'), 
                'roic': info.get('returnOnAssets'), 
                'de_ratio': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'pe_ratio': info.get('trailingPE', info.get('forwardPE')),
                'pb_ratio': info.get('priceToBook'),
                'ev_ebitda_ratio': info.get('enterpriseToEbitda'),
                'fcf': info.get('freeCashflow'), 
            }
            
            save_dir = os.path.join(".", "data", ticker, "fundamentals")
            os.makedirs(save_dir, exist_ok=True)
            
            file_path = os.path.join(save_dir, f"fundament_fetched_{today_date}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(record, f, indent=4, ensure_ascii=False)
                
            print(f"   SUCCESS: Saved base fundamentals to {file_path}")
            
        except Exception as e:
            print(f"ERROR: Failed fetching yfinance data for {ticker}. Reason: {e}")

if __name__ == "__main__":
    INDIAN_TICKERS = load_target_stocks()
    if INDIAN_TICKERS:
        fetch_fundamental_data_locally(INDIAN_TICKERS)
    else:
        print("Pipeline aborted: No tickers loaded.")