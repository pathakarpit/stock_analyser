import json
import os

def load_target_stocks(filepath="app/config/target_stocks.json"):
    """
    Centralized utility to load target stocks from a JSON config file.
    """
    if not os.path.exists(filepath):
        print(f"CRITICAL ERROR: Configuration file not found at {filepath}")
        return []
        
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return data.get("default_portfolio", [])
    except json.JSONDecodeError:
        print(f"CRITICAL ERROR: Invalid JSON formatting in {filepath}")
        return []