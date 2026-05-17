# config/educational_dictionary.py

EDUCATIONAL_DICTIONARY = {
    "beta": {
        "title": "Beta (Volatility)",
        "def": "Measures the asset's volatility in relation to the overall market.",
        "interp": "Beta > 1 means higher volatility than the market. Beta < 1 means lower volatility. Useful for assessing systemic risk."
    },
    "alpha": {
        "title": "Alpha (Excess Return)",
        "def": "Measures the active return on an investment compared to a market index or benchmark.",
        "interp": "Positive Alpha means the stock outperformed the market after adjusting for volatility. Negative indicates underperformance."
    },
    "sharpe": {
        "title": "Sharpe Ratio",
        "def": "Measures the performance of an investment compared to a risk-free asset, after adjusting for its risk.",
        "interp": "Higher is better (> 1.0 is considered good). Indicates how much excess return you receive for the extra volatility endured."
    },
    "add_metric": {
        "title": "Additional Custom Metric",
        "def": "A proprietary quantitative metric calculated by the fundamental engine.",
        "interp": "Refer to specific institutional model parameters for interpretation."
    },
    "roe": {
        "title": "Return on Equity (ROE)",
        "def": "Calculates how efficiently a company generates profits using shareholders' equity.",
        "interp": "15-20% is generally excellent. Indicates strong management efficiency in deploying capital."
    },
    "margins": {
        "title": "Net Profit Margin",
        "def": "The percentage of revenue left as profit after all expenses are deducted.",
        "interp": "Higher margins indicate strong pricing power and cost control. Best evaluated against sector peers."
    },
    "roic": {
        "title": "Return on Invested Capital (ROIC)",
        "def": "Assesses efficiency at allocating capital to profitable investments.",
        "interp": "Consistently high ROIC (above the cost of capital) is a hallmark of a strong competitive moat."
    },
    "de_ratio": {
        "title": "Debt-to-Equity Ratio",
        "def": "Evaluates financial leverage by dividing total liabilities by shareholder equity.",
        "interp": "Ratios > 2.0 signal heavy reliance on debt, increasing risk. < 1.0 indicates a safer, equity-financed operation."
    },
    "current_ratio": {
        "title": "Current Ratio (Liquidity)",
        "def": "Measures the ability to pay short-term obligations within one year.",
        "interp": "Ratio > 1.0 means sufficient assets to cover short-term liabilities. < 1.0 flags potential liquidity risk."
    },
    "sma": {
        "title": "Simple Moving Avg (SMA)",
        "def": "The unweighted average of the stock's closing price over a specific period.",
        "interp": "Price crossing above the SMA is typically a bullish trend signal; crossing below is bearish."
    },
    "ema": {
        "title": "Exponential Moving Avg (EMA)",
        "def": "A moving average placing greater weight and significance on the most recent data points.",
        "interp": "Reacts faster to recent price changes than SMA. Ideal for shorter-term trend identification."
    },
    "rsi": {
        "title": "Relative Strength Index (RSI)",
        "def": "A momentum oscillator measuring the speed and change of price movements (0 to 100).",
        "interp": "RSI > 70 suggests overbought conditions (potential pullback). RSI < 30 suggests oversold conditions."
    },
    "macd": {
        "title": "MACD",
        "def": "Moving Average Convergence Divergence; a trend-following momentum indicator.",
        "interp": "MACD line crossing above the signal line is a bullish trigger. Crossing below is a bearish trigger."
    },
    "pe_ratio": {
        "title": "P/E Ratio (Valuation)",
        "def": "Measures current share price relative to its per-share earnings.",
        "interp": "Lower usually indicates undervaluation. Must be compared against sector averages to avoid 'value traps'."
    },
    "pb_ratio": {
        "title": "Price-to-Book (P/B)",
        "def": "Compares a firm's market capitalization to its book value.",
        "interp": "A ratio under 1.0 can mean the stock is undervalued, or that something is fundamentally wrong with the operations."
    },
    "ev_ebitda_ratio": {
        "title": "EV/EBITDA",
        "def": "Compares Enterprise Value to Earnings Before Interest, Taxes, Depreciation, and Amortization.",
        "interp": "Often considered superior to P/E. Lower values (< 10) frequently highlight undervalued companies."
    },
    "fcf": {
        "title": "Free Cash Flow (FCF)",
        "def": "The cash a company generates after accounting for outflows to support operations and maintain capital assets.",
        "interp": "Positive, growing FCF is a pristine health indicator, allowing for dividends, debt reduction, or reinvestment."
    }
}

def get_educational_context(key):
    """Strictly matches database columns to precise financial definitions."""
    return EDUCATIONAL_DICTIONARY.get(key.lower())