# app/config/segment_dictionary.py

SEGMENT_DICTIONARY = {
    "valuation": {
        "theory": "Evaluates if the asset is cheap or expensive relative to its fundamentals. Because lower valuation ratios are preferred, the engine actively penalizes high multiples.",
        "formula": r"Score_{val} = \left( 1 + 9e^{-0.07 \cdot PE} \right) \times e^{-0.2 \cdot (PB - 2)}",
        "math_details": "Calculated using an exponential decay function for the P/E ratio, establishing a base score that rapidly drops as P/E rises. This is scaled by a Price-to-Book modifier centered around a 2.0 baseline."
    },
    "profitability": {
        "theory": "Measures the company's sheer ability to generate profit from equity and revenue, independent of its market price.",
        "formula": r"Score_{prof} = \left( 1 + \frac{9}{1 + e^{-30 \cdot (ROE - 0.15)}} \right) + 10(Margin - 0.10)",
        "math_details": "Employs a logistic sigmoid function with a steepness factor of 30 and an inflection point at a 15% ROE. Net margins above 10% apply a linear scaling bonus to the base curve."
    },
    "solvency": {
        "theory": "Assesses financial survival health. It measures the ability to meet long-term debts and short-term liquidity obligations.",
        "formula": r"Score_{solv} = \left( 1 + 9e^{-1.2 \cdot DE} \right) + \ln(CurrentRatio)",
        "math_details": "Uses an aggressive exponential decay (k=1.2) on the Debt-to-Equity ratio to heavily penalize leverage. The Current Ratio adds a logarithmic bonus, rewarding liquidity with diminishing returns."
    },
    "momentum": {
        "theory": "Evaluates current price trend strength while strictly avoiding overbought conditions to prevent catching 'falling knives' or buying at the peak.",
        "formula": r"Score_{mom} = \left( 1 + \frac{9}{1 + e^{0.15 \cdot (RSI - 50)}} \right) + 0.5 \cdot \text{sign}(MACD)",
        "math_details": "Uses an inverted logistic function centered at an RSI of 50 to aggressively penalize overbought territory. A discrete \pm 0.5 point adjustment is applied based on the MACD signal direction."
    },
    "capital_efficiency": {
        "theory": "Measures operational agility and effectiveness in allocating invested capital into profitable returns.",
        "formula": r"Score_{eff} = 1 + \frac{9}{1 + e^{-35 \cdot (ROIC - 0.12)}}",
        "math_details": "A pure logistic sigmoid curve evaluating Return on Invested Capital (ROIC). The inflection point is strictly set at a 12% baseline cost of capital, with a steep curve (k=35) rapidly rewarding outperformance."
    }
}

def get_segment_context(key):
    """Retrieves the exact quantitative math and theory behind the 1-10 segment scores."""
    return SEGMENT_DICTIONARY.get(key.lower(), {
        "theory": "Error: Segment key not recognized by the backend configuration.",
        "formula": r"\text{Undefined mathematical parameter}",
        "math_details": f"System Alert: The UI attempted to request data for an unmapped key: '{key}'."
    })