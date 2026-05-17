import yfinance as yf
import pandas as pd
from app.core.database import engine
from app.core.db_utils import postgres_upsert
from app.core.utils import load_target_stocks

def fetch_daily_prices(tickers):
    """
    Fetches the most recent End-of-Day (EoD) data for a list of tickers.
    Designed to be run daily by a cron job or Airflow.
    """
    print(f"Executing DAILY (1d) market data fetch for {len(tickers)} tickers...")
    
    for ticker in tickers:
        try:
            print(f"Fetching latest close for {ticker}...")
            stock = yf.Ticker(ticker)
            # Pull only the last 1 day of data
            df = stock.history(period="1d")
            
            if df.empty:
                print(f"WARNING: No daily data found for {ticker}. Market might be closed.")
                continue
                
            # Clean and format the dataframe
            df = df.reset_index()
            
            # Ensure the date is strictly YYYY-MM-DD
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            # Rename columns to match the 'stock_price_data' SQL schema
            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'Close': 'close',
                'High': 'high',
                'Low': 'low',
                'Volume': 'volume'
            })
            
            df['stock_id'] = ticker
            
            # Select strictly the columns we need
            df_clean = df[['stock_id', 'date', 'open', 'close', 'high', 'low', 'volume']]
            
            # Push to PostgreSQL using the custom upsert method
            df_clean.to_sql(
                name='stock_price_data', 
                con=engine, 
                if_exists='append', 
                index=False, 
                method=postgres_upsert
            )
            print(f"SUCCESS: Updated daily price for {ticker}. latest date: {df_clean['date'].iloc[0]} close: {df_clean['close'].iloc[0]} ")
            
        except Exception as e:
            print(f"ERROR: Failed daily update for {ticker}. Reason: {e}")

if __name__ == "__main__":
    # Dynamically load the Indian stocks from the centralized config file
    INDIAN_TICKERS = load_target_stocks()
    
    if INDIAN_TICKERS:
        fetch_daily_prices(INDIAN_TICKERS)
        print("Daily price update complete!")
    else:
        print("Pipeline aborted: No tickers loaded from configuration.")