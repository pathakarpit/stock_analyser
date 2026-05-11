import yfinance as yf
import pandas as pd
from app.core.database import engine
from app.core.db_utils import postgres_upsert
from app.core.utils import load_target_stocks

def fetch_historical_prices(tickers, period="6mo"):
    """
    Fetches historical data for a list of tickers and pushes it to PostgreSQL.
    Safely ignores dates that already exist in the database via upsert.
    """
    print(f"Executing {period} HISTORICAL market data fetch for {len(tickers)} tickers...")
    
    for ticker in tickers:
        try:
            print(f"Fetching historical data for {ticker}...")
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            
            if df.empty:
                print(f"WARNING: No data found for {ticker}. Skipping.")
                continue
                
            # Clean and format the dataframe
            df = df.reset_index()
            
            # Ensure the date is strictly YYYY-MM-DD
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            # Rename columns to match the 'stock_price_data' SQL schema perfectly
            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'Close': 'close',
                'High': 'high',
                'Low': 'low',
                'Volume': 'volume'
            })
            
            # Add our primary key identifier
            df['stock_id'] = ticker
            
            # Select strictly the columns we need
            df_clean = df[['stock_id', 'date', 'open', 'close', 'high', 'low', 'volume']]
            
            # Push to PostgreSQL using the custom upsert method from db_utils
            df_clean.to_sql(
                name='stock_price_data', 
                con=engine, 
                if_exists='append', 
                index=False, 
                method=postgres_upsert
            )
            print(f"SUCCESS: Inserted/Verified {len(df_clean)} rows for {ticker}.")
            
        except Exception as e:
            print(f"ERROR: Failed processing {ticker}. Reason: {e}")

if __name__ == "__main__":
    # Dynamically load the Indian stocks from the centralized config file
    INDIAN_TICKERS = load_target_stocks()
    
    if INDIAN_TICKERS:
        fetch_historical_prices(INDIAN_TICKERS, period="6mo")
        print("Historical bootstrap complete!")
    else:
        print("Pipeline aborted: No tickers loaded from configuration.")