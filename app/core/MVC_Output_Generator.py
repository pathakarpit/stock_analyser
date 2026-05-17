# app/core/MVC_Output_Generator.py
import os
import sys
import pandas as pd
import streamlit as st  # <--- Add this line right here
from sqlalchemy import text
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the centralized database engine
try:
    from app.core.database import engine 
except ImportError as e:
    print(f"Error loading database engine: {e}")
    sys.exit(1)

# --- 24-HOUR CACHED FUNCTIONS (Model/Data Access Layer) ---

@st.cache_data(ttl=86400) 
def fetch_market_sentiment_model():
    """Reads the sector CSV and averages the latest scores for the Market Metric."""
    csv_path = os.path.join(".", "data", "sector_sentiment_score.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            latest_date = df['date'].max()
            latest_df = df[df['date'] == latest_date]
            # Output rounded to single decimal
            return round(latest_df['sentiment_score'].mean(), 1)
        except Exception:
            return None
    return None

@st.cache_data(ttl=86400)
def fetch_landing_page_model():
    """Compiles the master dataframe for the landing page. Ripped clean of logic."""
    with engine.connect() as conn:
        # Using CTEs (Common Table Expressions) for professional, database-level compute.
        query = text("""
            WITH latest_fundamentals AS (
                SELECT stock_id, fundamental_score, 
                       ROW_NUMBER() OVER(PARTITION BY stock_id ORDER BY date DESC) as rn
                FROM fundamental_overall_score_store
            ),
            latest_patterns AS (
                SELECT stock_id, score, 
                       ROW_NUMBER() OVER(PARTITION BY stock_id ORDER BY date DESC) as rn
                FROM pattern_score_store
            ),
            -- LIVE PRICE PERFORMANCE CTE: No Mocking!
            price_calc AS (
                SELECT 
                    stock_id, 
                    close,
                    LAG(close) OVER (PARTITION BY stock_id ORDER BY date ASC) AS prev_close,
                    ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) as rn
                FROM stock_price_data
            )
            SELECT 
                p.stock_id AS "Stock",
                p.sector AS "Sector", -- Added Sector for better front-page context
                -- Standardized decimals at the DB level (Kills 3.70000)
                ROUND(f.fundamental_score, 1) AS "Fundamental Score",
                ROUND(pat.score, 1) AS "Pattern Score",
                ROUND(pr.close, 2) AS "Last Price (₹)",
                -- Calculate percentage change, handling divide-by-zero.
                ROUND(((pr.close - pr.prev_close) / NULLIF(pr.prev_close, 0)) * 100, 2) AS "Daily Change (Pct)"
            FROM company_profile_static_store p
            LEFT JOIN latest_fundamentals f ON p.stock_id = f.stock_id AND f.rn = 1
            LEFT JOIN latest_patterns pat ON p.stock_id = pat.stock_id AND pat.rn = 1
            LEFT JOIN price_calc pr ON p.stock_id = pr.stock_id AND pr.rn = 1
        """)
        df = pd.read_sql(query, conn)
        return df

# --- ON-DEMAND FUNCTIONS (Deep Dive Data) ---

def fetch_static_profile_model(stock_id):
    """Fetches static company info."""
    with engine.connect() as conn:
        query = text("SELECT * FROM company_profile_static_store WHERE stock_id = :stock")
        result = conn.execute(query, {"stock": stock_id}).mappings().fetchone()
        return dict(result) if result else None

def fetch_fundamental_segments_model(stock_id):
    """Fetches granular fundamental scores for the detail page."""
    with engine.connect() as conn:
        query = text("""
            SELECT * FROM fundamental_segment_score_store 
            WHERE stock_id = :stock ORDER BY date DESC LIMIT 1
        """)
        result = conn.execute(query, {"stock": stock_id}).mappings().fetchone()
        return dict(result) if result else None

def fetch_calculated_fundamentals_model(stock_id):
    """Fetches raw calculated financial metrics (P/E, ROE, Debt/Equity, etc.)."""
    with engine.connect() as conn:
        query = text("""
            SELECT * FROM calculated_fundamental_store 
            WHERE stock_id = :stock ORDER BY date DESC LIMIT 1
        """)
        result = conn.execute(query, {"stock": stock_id}).mappings().fetchone()
        return dict(result) if result else None

def fetch_relevant_news_model(stock_id):
    """Fetches the latest sentiment score and relevant localized news."""
    sentiment_score = None
    
    # 1. Try to get official score from database
    with engine.connect() as conn:
        query = text("""
            SELECT sentiment_score FROM aggregated_sentiment_score_store 
            WHERE stock_id = :stock ORDER BY date DESC LIMIT 1
        """)
        result = conn.execute(query, {"stock": stock_id}).scalar()
        if result is not None:
            sentiment_score = float(result)

    # 2. Fetch local CSV
    news_df = pd.DataFrame()
    csv_path = os.path.join(".", "data", stock_id, "news", "news_score.csv")
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            # Smart Parser: Aggressively hunt for news text (headline, news, summary, article, content, description)
            possible_text_columns = ['news', 'summary', 'headline', 'article', 'content', 'description']
            target_col = None
            for col in possible_text_columns:
                if col in df.columns:
                    target_col = col
                    break # Stop at first match
            
            if target_col and 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values(by='date', ascending=False)
                
                # Output standard 'date' and the dynamically found 'news_text' column
                news_df = df.head(10)[['date', target_col]].copy()
                news_df.rename(columns={target_col: 'news_text'}, inplace=True)
                
                # If DB sentiment missing, use CSV average fail-safe
                if sentiment_score is None and 'sentiment_score' in df.columns:
                    sentiment_score = round(df['sentiment_score'].mean(), 1)
        except Exception:
            pass
            
    return sentiment_score, news_df

# --- THE FINANCIAL EDUCATIONAL DATABASE (The 'Click' Modal Data) ---
# This dictionary maps raw DB keys to human-readable educational modules.
@st.cache_data(ttl=86400)
def generate_educational_db_model():
    """Generates a highly specific educational financial metrics database."""
    return {
        "p_e_ratio": {
            "title": "P/E Ratio (Price-to-Earnings)",
            "definition": "A primary quantitative metric measuring a company's share price relative to its per-share earnings. Shows what the market is willing to pay for a company's profits.",
            "formula": "$$ P/E = \\frac{Current Share Price}{Earnings Per Share (EPS)} $$",
            "interpretation": {
                "Low (< 15)": "The asset may be undervalued. You purchase profits cheaply.",
                "High (> 25)": "Overvalued, or the market is priced for extremely high future growth.",
                "Sector Average": "CRITICAL: You *must* compare this specific P/E ratio to the sector average provided above to make a valid judgment."
            }
        },
        "roe": {
            "title": "ROE (Return on Equity)",
            "definition": "Measures profitability relative to the shareholders' equity. High ROE indicates excellent capital efficiency.",
            "formula": "$$ ROE = \\frac{Net Income}{Shareholder Equity} \\cdot 100\\% $$",
            "interpretation": {
                "Healthy (15-20%)": "Management is efficiently using shareholders' investment to generate growth.",
                "Flag (< 10%)": "A potential indicator of operational or capital inefficiency.",
                "Highly Bullish ( > 25%)": "Outstanding profitability, or dangerous extreme leverage."
            }
        },
        # (Debt-to-Equity, EPS, Current Ratio, and P/B will follow this exact rich template)
    }