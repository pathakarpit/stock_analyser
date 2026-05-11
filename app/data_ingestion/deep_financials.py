import os
import yfinance as yf
from app.core.utils import load_target_stocks

def fetch_deep_financials(tickers):
    """
    Fetches raw Income Statements, Balance Sheets, Cash Flows, and Corporate Actions
    and saves them locally as CSV files. These act as a fallback for calculating 
    missing ratios later.
    """
    print(f"Executing DEEP FINANCIALS fetch for {len(tickers)} tickers...")

    for ticker in tickers:
        print(f"Pulling raw accounting statements for {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            
            # Create the directory structure: ./data/{stock_id}/financials/
            save_dir = os.path.join(".", "data", ticker, "financials")
            os.makedirs(save_dir, exist_ok=True)
            
            # 1. Income Statement (Profit & Loss)
            income_stmt = stock.financials
            if not income_stmt.empty:
                income_stmt.to_csv(os.path.join(save_dir, "income_statement.csv"))
            
            # 2. Balance Sheet (Assets & Liabilities)
            balance_sheet = stock.balance_sheet
            if not balance_sheet.empty:
                balance_sheet.to_csv(os.path.join(save_dir, "balance_sheet.csv"))
                
            # 3. Cash Flow Statement
            cash_flow = stock.cashflow
            if not cash_flow.empty:
                cash_flow.to_csv(os.path.join(save_dir, "cash_flow.csv"))
                
            # 4. Corporate Actions (Dividends & Stock Splits)
            actions = stock.actions
            if not actions.empty:
                # Remove timezone data to make it compatible with standard CSV formats
                actions.index = actions.index.tz_localize(None)
                actions.to_csv(os.path.join(save_dir, "corporate_actions.csv"))
                
            print(f"   SUCCESS: Saved statements and actions to {save_dir}/")
            
        except Exception as e:
            print(f"ERROR: Failed fetching deep financials for {ticker}. Reason: {e}")

if __name__ == "__main__":
    INDIAN_TICKERS = load_target_stocks()
    if INDIAN_TICKERS:
        fetch_deep_financials(INDIAN_TICKERS)
    else:
        print("Pipeline aborted: No tickers loaded.")