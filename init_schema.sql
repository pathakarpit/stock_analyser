-- ==========================================
-- 1. Market Data
-- ==========================================
CREATE TABLE IF NOT EXISTS stock_price_data (
    stock_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC,
    close NUMERIC,
    high NUMERIC,
    low NUMERIC,
    volume BIGINT,
    PRIMARY KEY (stock_id, date)
);

-- ==========================================
-- 2. Fundamental Analysis
-- ==========================================
CREATE TABLE IF NOT EXISTS calculated_fundamental_store (
    stock_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    beta NUMERIC,
    alpha NUMERIC,
    sharpe NUMERIC,
    add_metric NUMERIC, -- Renamed from ADD to avoid SQL keyword collision
    roe NUMERIC,
    margins NUMERIC,
    roic NUMERIC,
    de_ratio NUMERIC,
    current_ratio NUMERIC,
    sma NUMERIC,
    ema NUMERIC,
    rsi NUMERIC,
    macd NUMERIC,
    pe_ratio NUMERIC,
    pb_ratio NUMERIC,
    ev_ebitda_ratio NUMERIC,
    fcf NUMERIC,
    PRIMARY KEY (stock_id, date)
);

CREATE TABLE IF NOT EXISTS fundamental_segment_score_store (
    stock_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    valuation_score NUMERIC,
    profitability_score NUMERIC,
    solvency_score NUMERIC,
    momentum_score NUMERIC,
    capital_efficiency_score NUMERIC,
    risk_performance_score NUMERIC,
    PRIMARY KEY (stock_id, date)
);

CREATE TABLE IF NOT EXISTS fundamental_overall_score_store (
    stock_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    fundamental_score NUMERIC,
    PRIMARY KEY (stock_id, date)
);

-- ==========================================
-- 3. NLP & Sentiment Analysis
-- ==========================================
CREATE TABLE IF NOT EXISTS news_sentiment_score_store (
    news_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    stock_id VARCHAR(20) NOT NULL,
    sector VARCHAR(50),
    news_date TIMESTAMP,
    capture_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    overview TEXT,
    score INTEGER CHECK (score >= 1 AND score <= 100)
);

-- Index to dramatically speed up Agent 4's historical news queries
CREATE INDEX IF NOT EXISTS idx_news_sentiment_stock ON news_sentiment_score_store(stock_id);

CREATE TABLE IF NOT EXISTS aggregated_sentiment_score_store (
    stock_id VARCHAR(20) NOT NULL,
    sector VARCHAR(50),
    date DATE NOT NULL,
    sentiment_score NUMERIC,
    PRIMARY KEY (stock_id, date)
);

-- ==========================================
-- 4. Technical / Pattern Analysis
-- ==========================================
CREATE TABLE IF NOT EXISTS pattern_score_store (
    stock_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    score NUMERIC,
    brief TEXT,
    PRIMARY KEY (stock_id, date)
);

-- ==========================================
-- 5. User Management & State
-- ==========================================
CREATE TABLE IF NOT EXISTS profile_data (
    user_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL,
    email_id VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20),
    risk_tolerance VARCHAR(20) CHECK (risk_tolerance IN ('Conservative', 'Moderate', 'Aggressive')),
    investment_horizon VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS credentials_store (
    user_id UUID PRIMARY KEY REFERENCES profile_data(user_id) ON DELETE CASCADE,
    random_key VARCHAR(255) NOT NULL,
    secured_key VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS request_queue_table (
    user_id UUID REFERENCES profile_data(user_id) ON DELETE CASCADE,
    requested_stock_id VARCHAR(20) NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed')),
    PRIMARY KEY (user_id, requested_stock_id, date)
);

-- ==========================================
-- 6. Company Profile Data
-- ==========================================
CREATE TABLE IF NOT EXISTS company_profile_static_store (
    stock_id VARCHAR(20) PRIMARY KEY,
    company_name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    description TEXT,
    website VARCHAR(255),
    last_updated DATE DEFAULT CURRENT_DATE
);