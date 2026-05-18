import pandas as pd
import numpy as np
import time
import concurrent.futures
from datetime import datetime, timezone
from app.core.database import engine
from app.core.db_utils import postgres_upsert
from app.core.utils import load_target_stocks

# ==========================================
# 1. DATA SANITIZATION
# ==========================================
def sanitize_float(val):
    if val is None: return None
    try:
        f_val = float(val)
        if np.isnan(f_val) or np.isinf(f_val): return None
        return f_val
    except (ValueError, TypeError):
        return None

# ==========================================
# 2. PATTERN MATH MODELS
# ==========================================
def calculate_trend_score(close, sma, ema):
    close, sma, ema = sanitize_float(close), sanitize_float(sma), sanitize_float(ema)
    if None in [close, sma, ema] or sma == 0: return 5.0

    price_to_sma = (close - sma) / sma 
    k_steepness = 40
    base_score = 1 + (9 / (1 + np.exp(-k_steepness * price_to_sma)))

    if ema > sma: base_score += 1.0
    else: base_score -= 1.0

    return round(max(1.0, min(10.0, float(base_score))), 2)

def calculate_technical_momentum(rsi, macd):
    rsi, macd = sanitize_float(rsi), sanitize_float(macd)
    if rsi is None: return 5.0
    
    if rsi < 30: score = 9.0
    elif rsi <= 45: score = 7.0
    elif rsi <= 60: score = 6.0
    elif rsi <= 75: score = 4.0
    else: score = 2.0 
    
    if macd is not None:
        if macd > 0: score += 1.5 
        elif macd < 0: score -= 1.5 
        
    return round(max(1.0, min(10.0, float(score))), 2)

# ==========================================
# 3. DETERMINISTIC TEXT BUILDER
# ==========================================
def generate_pattern_brief(close, sma, rsi, macd):
    close, sma, rsi, macd = sanitize_float(close), sanitize_float(sma), sanitize_float(rsi), sanitize_float(macd)
    
    if None in [close, sma, rsi, macd]:
        return "Insufficient technical data available."

    if close > sma:
        trend_text = "Trading above its 50-day moving average, indicating a prevailing uptrend."
    else:
        trend_text = "Trading below its 50-day moving average, suggesting bearish pressure."
        
    if rsi < 30: rsi_text = "The RSI is oversold, hinting at a potential bounce."
    elif rsi > 70: rsi_text = "However, the RSI is overbought, raising the risk of a near-term pullback."
    else: rsi_text = "RSI sits in neutral territory."
        
    if macd > 0: macd_text = "Momentum is supported by a positive MACD."
    else: macd_text = "Momentum is currently dragging with a negative MACD."

    return f"{trend_text} {rsi_text} {macd_text}"

# ==========================================
# 4. MULTIPROCESSING WORKER
# ==========================================
def process_pattern(row, today_date):
    ticker = row['stock_id']
    t_start = time.perf_counter()

    trend_score = calculate_trend_score(row.get('close'), row.get('sma'), row.get('ema'))
    mom_score = calculate_technical_momentum(row.get('rsi'), row.get('macd'))
    
    # Calculate single unified score (60% Trend, 40% Momentum)
    total_score = (trend_score * 0.60) + (mom_score * 0.40)
    
    brief_text = generate_pattern_brief(row.get('close'), row.get('sma'), row.get('rsi'), row.get('macd'))

    # Perfectly mapped to your SQL schema
    record = {
        'stock_id': ticker,
        'date': today_date,
        'score': round(total_score, 2),
        'brief': brief_text
    }
    
    t_total = (time.perf_counter() - t_start) * 1000
    return record, {'stock_id': ticker, 't_pattern_ms': t_total}

# ==========================================
# 5. MAIN ORCHESTRATOR
# ==========================================
def execute_pattern_engine(tickers):
    master_start_time = time.perf_counter()
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print(f"\n🚀 Booting Pattern Analyst Engine for {today_date}...")
    ticker_list = "','".join(tickers)
    
    # FIX: Use a CTE and ROW_NUMBER() to grab the most recent data point for each stock,
    # safely bypassing weekends and market holidays.
    query = f"""
        WITH LatestFundamentals AS (
            SELECT stock_id, sma, ema, rsi, macd, date,
                   ROW_NUMBER() OVER(PARTITION BY stock_id ORDER BY date DESC) as rn
            FROM calculated_fundamental_store
            WHERE stock_id IN ('{ticker_list}')
        ),
        LatestPrices AS (
            SELECT stock_id, close, date,
                   ROW_NUMBER() OVER(PARTITION BY stock_id ORDER BY date DESC) as rn
            FROM stock_price_data
            WHERE stock_id IN ('{ticker_list}')
        )
        SELECT 
            f.stock_id, f.sma, f.ema, f.rsi, f.macd, 
            p.close, p.date as price_date, f.date as math_date
        FROM LatestFundamentals f
        LEFT JOIN LatestPrices p ON f.stock_id = p.stock_id
        WHERE f.rn = 1 AND p.rn = 1
    """
    
    try:
        df_raw = pd.read_sql(query, engine)
        if df_raw.empty:
            print("   [!] No historical data found to process.")
            return

        rows_to_process = df_raw.to_dict('records')
        scored_records = []
        timing_records = []

        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            # We still pass 'today_date' to process_pattern so the score is saved with today's run date
            futures = [executor.submit(process_pattern, row, today_date) for row in rows_to_process]
            for future in concurrent.futures.as_completed(futures):
                try:
                    record, timings = future.result()
                    scored_records.append(record)
                    timing_records.append(timings)
                except Exception as exc:
                    print(f"   [!] Worker exception: {exc}")

        # Push to PostgreSQL
        if scored_records:
            df_scores = pd.DataFrame(scored_records)
            df_scores.to_sql(
                name='pattern_score_store', 
                con=engine, 
                if_exists='append', 
                index=False, 
                method=postgres_upsert
            )
            print(f"✅ SUCCESS: Stored {len(df_scores)} single-score technical briefs.")

    except Exception as e:
        print(f"CRITICAL ERROR in Pattern Engine: {e}")

    master_end_time = time.perf_counter()
    print(f"\n🏁 PATTERN BATCH COMPLETE. Time: {master_end_time - master_start_time:.4f} seconds.\n")

if __name__ == "__main__":
    INDIAN_TICKERS = load_target_stocks()
    if INDIAN_TICKERS:
        execute_pattern_engine(INDIAN_TICKERS)