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
    """Catches NaN, Infinity, None, or weird strings and safely neutralizes them."""
    if val is None:
        return None
    try:
        f_val = float(val)
        if np.isnan(f_val) or np.isinf(f_val):
            return None
        return f_val
    except (ValueError, TypeError):
        return None

# ==========================================
# 2. CONTINUOUS MATH FUNCTIONS
# ==========================================
def score_valuation_math(pe, pb):
    pe, pb = sanitize_float(pe), sanitize_float(pb)
    if pe is None: return 5.0
    if pe <= 0: return 1.0 
    
    decay_rate = 0.07 
    base_score = 1 + 9 * np.exp(-decay_rate * pe)
    
    if pb is not None and pb > 0:
        pb_modifier = np.exp(-0.2 * (pb - 2))
        base_score *= pb_modifier
        
    return round(max(1.0, min(10.0, float(base_score))), 2)

def score_profitability_math(roe, margins):
    roe, margins = sanitize_float(roe), sanitize_float(margins)
    if roe is None: return 5.0
    
    k_steepness = 30
    x_inflection = 0.15 
    base_score = 1 + (9 / (1 + np.exp(-k_steepness * (roe - x_inflection))))
    
    if margins is not None:
        base_score += (margins - 0.10) * 10
        
    return round(max(1.0, min(10.0, float(base_score))), 2)

def score_solvency_math(de_ratio, current_ratio):
    de_ratio, current_ratio = sanitize_float(de_ratio), sanitize_float(current_ratio)
    if de_ratio is None: return 5.0
    if de_ratio < 0: return 1.0
    
    decay_rate = 1.2 
    base_score = 1 + 9 * np.exp(-decay_rate * de_ratio)
    
    if current_ratio is not None and current_ratio > 0:
        base_score += np.log(current_ratio)
        
    return round(max(1.0, min(10.0, float(base_score))), 2)

def score_efficiency_math(roic):
    roic = sanitize_float(roic)
    if roic is None: return 5.0
    
    k_steepness = 35
    x_inflection = 0.12 
    score = 1 + (9 / (1 + np.exp(-k_steepness * (roic - x_inflection))))
    return round(max(1.0, min(10.0, float(score))), 2)

def score_momentum_math(rsi, macd):
    rsi, macd = sanitize_float(rsi), sanitize_float(macd)
    if rsi is None: return 5.0
    
    k_steepness = 0.15
    x_inflection = 50 
    base_score = 1 + (9 / (1 + np.exp(k_steepness * (rsi - x_inflection))))
    
    if macd is not None:
        base_score += np.sign(macd) * 0.5 
        
    return round(max(1.0, min(10.0, float(base_score))), 2)

def score_risk_performance_math(sharpe, alpha):
    """Logistic Sigmoid for Sharpe, linear bonus for Alpha."""
    sharpe, alpha = sanitize_float(sharpe), sanitize_float(alpha)
    if sharpe is None: return 5.0
    
    k_steepness = 3.0
    x_inflection = 0.5 
    base_score = 1 + (9 / (1 + np.exp(-k_steepness * (sharpe - x_inflection))))
    
    if alpha is not None:
        base_score += (alpha * 10) 
        
    return round(max(1.0, min(10.0, float(base_score))), 2)

# ==========================================
# 3. THE MULTIPROCESSING WORKER
# ==========================================
def process_stock(row, today_date):
    """Isolated worker function for parallel processing."""
    ticker = row['stock_id']
    timings = {'stock_id': ticker}
    t_stock_start = time.perf_counter()

    # Calculate individual segments
    t0 = time.perf_counter()
    val_score = score_valuation_math(row.get('pe_ratio'), row.get('pb_ratio'))
    timings['t_valuation_ms'] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    prof_score = score_profitability_math(row.get('roe'), row.get('margins'))
    timings['t_profitability_ms'] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    solv_score = score_solvency_math(row.get('de_ratio'), row.get('current_ratio'))
    timings['t_solvency_ms'] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    eff_score = score_efficiency_math(row.get('roic'))
    timings['t_efficiency_ms'] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    mom_score = score_momentum_math(row.get('rsi'), row.get('macd'))
    timings['t_momentum_ms'] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    risk_score = score_risk_performance_math(row.get('sharpe'), row.get('alpha'))
    timings['t_risk_ms'] = (time.perf_counter() - t0) * 1000

    # Calculate Master Weighted Score
    # Weights: Val(20%), Prof(20%), Solv(15%), Eff(15%), Risk(20%), Mom(10%)
    total_score = (
        (val_score * 0.20) +
        (prof_score * 0.20) +
        (solv_score * 0.15) +
        (eff_score * 0.15) +
        (risk_score * 0.20) +
        (mom_score * 0.10)
    )
    
    timings['t_total_ms'] = (time.perf_counter() - t_stock_start) * 1000

    record = {
        'stock_id': ticker,
        'date': today_date,
        'valuation_score': val_score,
        'profitability_score': prof_score,
        'solvency_score': solv_score,
        'momentum_score': mom_score,
        'capital_efficiency_score': eff_score,
        'risk_performance_score': risk_score,
        'total_score': round(total_score, 2)
    }
    
    return record, timings

# ==========================================
# 4. MAIN ORCHESTRATOR
# ==========================================
def execute_scoring_engine(tickers):
    master_start_time = time.perf_counter()
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print(f"\n🚀 Booting CPU Engine (10 Workers) for {len(tickers)} stocks. Date: {today_date}")
    
    ticker_list = "','".join(tickers)
    
    # STRICT QUERY: Only grab rows where date matches TODAY.
    query = f"""
        SELECT * FROM calculated_fundamental_store 
        WHERE stock_id IN ('{ticker_list}')
        AND date = '{today_date}'
    """
    
    try:
        df_raw = pd.read_sql(query, engine)
        if df_raw.empty:
            print(f"   [!] No raw data found for TODAY ({today_date}). Did the ingestion phase run?")
            return

        rows_to_process = df_raw.to_dict('records')
        scored_records = []
        timing_records = []

        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_stock, row, today_date) for row in rows_to_process]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    record, timings = future.result()
                    scored_records.append(record)
                    timing_records.append(timings)
                except Exception as exc:
                    print(f"   [!] Worker generated an exception: {exc}")

        # Push to PostgreSQL
        if scored_records:
            df_scores = pd.DataFrame(scored_records)
            df_scores.to_sql(
                name='fundamental_segment_score_store', 
                con=engine, 
                if_exists='append', 
                index=False, 
                method=postgres_upsert
            )
            print(f"✅ SUCCESS: Final calculated rows pushed to DB for {len(df_scores)} stocks.")
            
        # Build and Print the Profiling Report
        if timing_records:
            df_timing = pd.DataFrame(timing_records)
            df_timing = df_timing.sort_values(by='t_total_ms', ascending=False).reset_index(drop=True)
            
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            
            print("\n" + "="*80)
            print("🕒 EXECUTION TIMING PROFILER (Milliseconds)")
            print("="*80)
            print(df_timing.to_string(index=False, float_format="%.3f"))
            print("="*80)

    except Exception as e:
        print(f"CRITICAL ERROR in Scoring Engine: {e}")

    master_end_time = time.perf_counter()
    print(f"\n🏁 BATCH COMPLETE. Total Pipeline Execution Time: {master_end_time - master_start_time:.4f} seconds.\n")

if __name__ == "__main__":
    INDIAN_TICKERS = load_target_stocks()
    if INDIAN_TICKERS:
        execute_scoring_engine(INDIAN_TICKERS)