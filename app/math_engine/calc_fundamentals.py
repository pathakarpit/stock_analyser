import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone
import ta
from app.core.database import engine
from app.core.db_utils import postgres_upsert
from app.core.utils import load_target_stocks

# Global Indian Risk-Free Rate (Approx 7% for 10-Year Govt Bond)
RISK_FREE_RATE = 0.07

def get_market_return():
    """Fetches the Nifty 50 1-Year return to act as the benchmark for Alpha."""
    try:
        nifty = yf.Ticker('^NSEI')
        hist = nifty.history(period="1y")
        if len(hist) > 0:
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            return (end_price - start_price) / start_price
    except Exception as e:
        print(f"   [!] Failed to fetch Nifty 50. Defaulting to 12% market return. {e}")
    return 0.12 # Standard fallback for Indian equities

def patch_missing_fundamentals(ticker, base_data, save_dir):
    """Fallback to calculate missing static metrics from raw CSVs."""
    fin_dir = os.path.join(".", "data", ticker, "financials")
    if base_data.get('roe') is None:
        try:
            inc_stmt = pd.read_csv(os.path.join(fin_dir, "income_statement.csv"), index_col=0)
            bal_sheet = pd.read_csv(os.path.join(fin_dir, "balance_sheet.csv"), index_col=0)
            net_income = inc_stmt.loc['Net Income'].iloc[0]
            try:
                equity = bal_sheet.loc['Total Stockholder Equity'].iloc[0]
            except KeyError:
                equity = bal_sheet.loc['Stockholders Equity'].iloc[0]
            base_data['roe'] = round(net_income / equity, 4)
        except Exception:
            pass
    return base_data

def calculate_technicals_and_risk(ticker, beta, market_return):
    """
    Pulls prices, calculates SMA/RSI/MACD, plus Advanced Risk Metrics (Sharpe, Alpha, ADD).
    """
    # Upgraded Query to include high, low, and volume for the ADD metric
    query = f"""
        SELECT date, close, high, low, volume 
        FROM stock_price_data 
        WHERE stock_id = '{ticker}' 
        ORDER BY date ASC 
        LIMIT 252 
    """ # Expanding to 252 days (1 trading year) for accurate volatility math
    
    try:
        df_prices = pd.read_sql(query, engine)
        if len(df_prices) < 50:
            print(f"   [!] Insufficient price history for {ticker}. Need 50+ days.")
            return None
            
        # 1. Standard Technicals
        df_prices['sma'] = ta.trend.sma_indicator(df_prices['close'], window=50)
        df_prices['ema'] = ta.trend.ema_indicator(df_prices['close'], window=20)
        df_prices['rsi'] = ta.momentum.rsi(df_prices['close'], window=14)
        df_prices['macd'] = ta.trend.macd(df_prices['close'])
        
        # 2. ADD Metric (Accumulation/Distribution Line)
        df_prices['add_metric'] = ta.volume.acc_dist_index(
            df_prices['high'], df_prices['low'], df_prices['close'], df_prices['volume']
        )
        
        # 3. Risk & Performance Metrics (Sharpe & Alpha)
        # Calculate daily returns
        df_prices['daily_return'] = df_prices['close'].pct_change()
        
        # Annualize the returns and volatility (252 trading days in a year)
        annual_return = df_prices['daily_return'].mean() * 252
        annual_volatility = df_prices['daily_return'].std() * np.sqrt(252)
        
        # Sharpe Ratio
        if annual_volatility > 0:
            sharpe_ratio = (annual_return - RISK_FREE_RATE) / annual_volatility
        else:
            sharpe_ratio = 0.0
            
        # Jensen's Alpha (CAPM)
        # Needs Beta. If Beta is missing from base data, assume 1.0 (market average)
        safe_beta = beta if beta is not None else 1.0
        expected_return = RISK_FREE_RATE + safe_beta * (market_return - RISK_FREE_RATE)
        alpha = annual_return - expected_return

        latest = df_prices.iloc[-1]
        
        return {
            'sma': latest['sma'],
            'ema': latest['ema'],
            'rsi': latest['rsi'],
            'macd': latest['macd'],
            'add_metric': latest['add_metric'],
            'sharpe': round(sharpe_ratio, 4),
            'alpha': round(alpha, 4)
        }
    except Exception as e:
        print(f"   [!] Math Engine Error for {ticker}: {e}")
        return None

def execute_math_engine(tickers):
    print(f"Executing ADVANCED MATH & LOGIC ENGINE for {len(tickers)} tickers...")
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    final_records = []

    # Fetch Nifty 50 once for the whole batch
    print("Fetching Nifty 50 Benchmark Returns...")
    market_return = get_market_return()
    print(f"Current Nifty 50 1-Year Return: {market_return * 100:.2f}%\n")

    for ticker in tickers:
        print(f"Processing calculations for {ticker}...")
        
        save_dir = os.path.join(".", "data", ticker, "fundamentals")
        base_file = os.path.join(save_dir, f"fundament_fetched_{today_date}.json")
        
        if not os.path.exists(base_file):
            print(f"   [!] Missing fetched data for {ticker}. Skipping.")
            continue
            
        with open(base_file, 'r', encoding='utf-8') as f:
            base_data = json.load(f)
            
        patched_data = patch_missing_fundamentals(ticker, base_data, save_dir)
        
        # Pass beta and market_return into the technical calculator
        tech_data = calculate_technicals_and_risk(
            ticker, 
            beta=patched_data.get('beta'), 
            market_return=market_return
        )
        
        if not tech_data:
            continue
            
        final_row = {**patched_data, **tech_data}
        final_records.append(final_row)
        
        calc_file = os.path.join(save_dir, f"fundament_calculated_{today_date}.json")
        with open(calc_file, 'w', encoding='utf-8') as f:
            json.dump(final_row, f, indent=4)
            
        print(f"   SUCCESS: Merged and calculated advanced metrics for {ticker}.")

    if final_records:
        df_final = pd.DataFrame(final_records)
        # Ensure 'date' is a proper datetime object or string for SQL insertion
        try:
            df_final.to_sql(
                name='calculated_fundamental_store', 
                con=engine, 
                if_exists='append', 
                index=False, 
                method=postgres_upsert
            )
            print(f"\nSUCCESS: Engine pushed {len(df_final)} fully calculated rows to PostgreSQL.")
        except Exception as e:
            print(f"\nCRITICAL ERROR: Database insertion failed. {e}")

if __name__ == "__main__":
    INDIAN_TICKERS = load_target_stocks()
    if INDIAN_TICKERS:
        execute_math_engine(INDIAN_TICKERS)