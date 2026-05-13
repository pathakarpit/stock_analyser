import pandas as pd
import time
from datetime import datetime, timezone
from app.core.database import engine
from app.core.db_utils import postgres_upsert
from app.core.utils import load_target_stocks

# ==========================================
# DEFAULT INSTITUTIONAL WEIGHTS
# ==========================================
# These sum to 1.0 (100%). By keeping them in a dictionary, 
# you can easily turn this into a function parameter later 
# when users submit custom weights from your frontend UI.
DEFAULT_WEIGHTS = {
    'profitability_score': 0.20,
    'valuation_score': 0.20,
    'capital_efficiency_score': 0.15,
    'risk_performance_score': 0.15,
    'pattern_score': 0.15,       # From pattern_score_store
    'solvency_score': 0.10,
    'momentum_score': 0.05       # Fundamental momentum
}

def execute_overall_score_generator(tickers, weights=DEFAULT_WEIGHTS):
    master_start_time = time.perf_counter()
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print(f"\n🎯 Booting Overall Score Aggregator for {today_date}...")
    ticker_list = "','".join(tickers)
    
    # INNER JOIN the fundamental segments with the technical pattern score
    query = f"""
        SELECT 
            f.stock_id, 
            f.date,
            f.valuation_score, 
            f.profitability_score, 
            f.solvency_score, 
            f.momentum_score, 
            f.capital_efficiency_score, 
            f.risk_performance_score,
            p.score AS pattern_score
        FROM fundamental_segment_score_store f
        INNER JOIN pattern_score_store p 
            ON f.stock_id = p.stock_id AND f.date = p.date
        WHERE f.stock_id IN ('{ticker_list}')
        AND f.date = '{today_date}'
    """
    
    try:
        df_raw = pd.read_sql(query, engine)
        if df_raw.empty:
            print(f"   [!] No joined segment/pattern data found for TODAY ({today_date}).")
            return

        print(f"   [+] Aggregating Master Scores for {len(df_raw)} stocks using vectorized math...")
        
        # Calculate the weighted sum using Pandas vectorized operations (Lightning Fast)
        df_raw['fundamental_score'] = (
            (df_raw['valuation_score'] * weights['valuation_score']) +
            (df_raw['profitability_score'] * weights['profitability_score']) +
            (df_raw['solvency_score'] * weights['solvency_score']) +
            (df_raw['momentum_score'] * weights['momentum_score']) +
            (df_raw['capital_efficiency_score'] * weights['capital_efficiency_score']) +
            (df_raw['risk_performance_score'] * weights['risk_performance_score']) +
            (df_raw['pattern_score'] * weights['pattern_score'])
        )
        
        # Round to 2 decimal places for a clean 1-10 score
        df_raw['fundamental_score'] = df_raw['fundamental_score'].round(2)
        
        # Filter down strictly to the columns needed for the fundamental_overall_score_store table
        df_final = df_raw[['stock_id', 'date', 'fundamental_score']]
        print(df_final)
        # Push to PostgreSQL
        '''df_final.to_sql(
            name='fundamental_overall_score_store', 
            con=engine, 
            if_exists='append', 
            index=False, 
            method=postgres_upsert
        )'''
        print(f"✅ SUCCESS: Stored final Master Scores for {len(df_final)} stocks.")

    except Exception as e:
        print(f"CRITICAL ERROR in Overall Score Generator: {e}")

    master_end_time = time.perf_counter()
    print(f"\n🏁 AGGREGATION COMPLETE. Time: {master_end_time - master_start_time:.4f} seconds.\n")

if __name__ == "__main__":
    INDIAN_TICKERS = load_target_stocks()
    if INDIAN_TICKERS:
        execute_overall_score_generator(INDIAN_TICKERS)