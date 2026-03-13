"""
Stock Strategy Evaluator

This script fetches historical stock data using yfinance and evaluates
a selected investment strategy based on calculated financial metrics.

Strategies available:
- Momentum
- Low Volatility
- Value
- Balanced


"""

import yfinance as yf
import pandas as pd
from datetime import date


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

# Each strategy contains 3 rules
TOTAL_RULES_PER_STRATEGY = 3


# ---------------------------------------------------------
# METRIC CALCULATION
# ---------------------------------------------------------

def calculate_metrics(hist: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate financial indicators required for strategy evaluation.

    Parameters
    ----------
    hist : pandas DataFrame
        Historical stock price data returned by yfinance.

    Returns
    -------
    pandas DataFrame
        DataFrame with additional calculated columns.
    """

    # Create a copy so we don't modify original data
    hist = hist.copy()

    # -----------------------------------------------------
    # Daily Returns
    # -----------------------------------------------------
    # pct_change() calculates percentage change between rows
    # Example: (today_close - yesterday_close) / yesterday_close
    hist["Returns"] = hist["Close"].pct_change()

    # -----------------------------------------------------
    # Volatility
    # -----------------------------------------------------
    # rolling(20) calculates statistics over last 20 days
    # std() calculates standard deviation
    # multiplied by sqrt(252) to annualize volatility
    hist["Volatility"] = hist["Returns"].rolling(20).std() * (252 ** 0.5)

    # -----------------------------------------------------
    # Momentum
    # -----------------------------------------------------
    # 60 day percentage return
    # measures medium-term trend strength
    hist["Momentum"] = hist["Close"].pct_change(60)

    # -----------------------------------------------------
    # Moving Averages
    # -----------------------------------------------------
    # Short-term trend
    hist["MA20"] = hist["Close"].rolling(20).mean()

    # Medium-term trend
    hist["MA50"] = hist["Close"].rolling(50).mean()

    # -----------------------------------------------------
    # Average Price (entire dataset)
    # -----------------------------------------------------
    hist["AvgPrice"] = hist["Close"].mean()

    return hist


# ---------------------------------------------------------
# STRATEGY SCORING
# ---------------------------------------------------------

def score_strategies(hist: pd.DataFrame, strategy: str) -> int:
    """
    Evaluate the selected strategy and return its score.

    Parameters
    ----------
    hist : pandas DataFrame
        DataFrame containing calculated metrics.

    strategy : str
        Strategy selected by user.

    Returns
    -------
    int
        Strategy score (0–3).
    """

    # Use latest available data
    latest = hist.iloc[-1]

    # Score counter
    score = 0

    # -----------------------------------------------------
    # MOMENTUM STRATEGY
    # -----------------------------------------------------
    if strategy == "momentum":

        # Strong 60 day return
        if latest["Momentum"] > 0.05:
            score += 1

        # Short term trend above medium trend
        if latest["MA20"] > latest["MA50"]:
            score += 1

        # Positive daily return
        if latest["Returns"] > 0:
            score += 1

    # -----------------------------------------------------
    # LOW VOLATILITY STRATEGY
    # -----------------------------------------------------
    elif strategy == "low_volatility":

        # Annual volatility below 30%
        if latest["Volatility"] < 0.30:
            score += 1

        # Daily movement within +/-2%
        if abs(latest["Returns"]) < 0.02:
            score += 1

        # Stable trend
        if latest["MA20"] >= latest["MA50"]:
            score += 1

    # -----------------------------------------------------
    # VALUE STRATEGY
    # -----------------------------------------------------
    elif strategy == "value":

        avg_price = hist["Close"].mean()

        # Current price below average price
        if latest["Close"] < avg_price:
            score += 1

        # Reasonable volatility
        if latest["Volatility"] < 0.35:
            score += 1

        # Avoid strongly negative momentum
        if latest["Momentum"] > -0.05:
            score += 1

    # -----------------------------------------------------
    # BALANCED STRATEGY
    # -----------------------------------------------------
    elif strategy == "balanced":

        if latest["Momentum"] > 0:
            score += 1

        if latest["Volatility"] < 0.35:
            score += 1

        if latest["MA20"] > latest["MA50"]:
            score += 1

    return score


# ---------------------------------------------------------
# STRATEGY DESCRIPTIONS
# ---------------------------------------------------------

STRATEGY_DESCRIPTIONS = {
    "momentum": "Favors stronger recent returns and trend strength.",
    "low_volatility": "Prefers lower volatility and steadier names.",
    "value": "Tilts toward lower price relative to average.",
    "balanced": "Mix of return, momentum, and risk control.",
}


# ---------------------------------------------------------
# STRATEGY SELECTION
# ---------------------------------------------------------

def choose_strategy() -> str:
    """
    Allow user to select a strategy.
    """

    strategy_names = list(STRATEGY_DESCRIPTIONS.keys())

    print("\nAvailable strategies:")

    for i, name in enumerate(strategy_names, start=1):
        print(f"{i}. {name} - {STRATEGY_DESCRIPTIONS[name]}")

    selected = input(
        "Select strategy by number or name (default: balanced): "
    ).strip().lower()

    if not selected:
        return "balanced"

    if selected.isdigit():

        idx = int(selected) - 1

        if 0 <= idx < len(strategy_names):
            return strategy_names[idx]

        print("Invalid number. Using default: balanced.")
        return "balanced"

    if selected in STRATEGY_DESCRIPTIONS:
        return selected

    print("Invalid strategy. Using default: balanced.")
    return "balanced"


# ---------------------------------------------------------
# MAIN PROGRAM
# ---------------------------------------------------------

print("Welcome to the Stock Advisor tool")

# User selects strategy
strategy = choose_strategy()

# User enters stock ticker
choice = input("Enter preferred stock ticker (example: AAPL): ").strip()

# Ask if timeframe is needed
c = input("Is a custom time frame needed? (yes/no): ").strip().lower()

start_date = None
end_date = str(date.today())

if c == "yes":

    start_date = input("Enter start date (yyyy-mm-dd): ").strip()

    e = input(
        "Enter end date (leave blank for current date): "
    ).strip()

    if e:
        end_date = e


print(f"\nSelected strategy: {strategy}")
print(f"Selected stock: {choice}")

if start_date:
    print(f"Time frame: {start_date} to {end_date}")
else:
    print("Time frame: default (last 1 year)")

print("\nFetching data and analyzing...")


# ---------------------------------------------------------
# DATA FETCHING AND ANALYSIS
# ---------------------------------------------------------

try:

    ticker = yf.Ticker(choice)

    # Fetch historical data
    hist = (
        ticker.history(start=start_date, end=end_date)
        if start_date
        else ticker.history(period="1y")
    )

    if hist.empty:

        print("No data found for the specified stock.")

    else:

        print(
            f"Data fetched from {hist.index[0].date()} "
            f"to {hist.index[-1].date()}"
        )

        # Calculate financial indicators
        hist = calculate_metrics(hist)

        # Remove rows with NaN values
        valid_hist = hist.dropna(
            subset=["Returns", "Volatility", "Momentum", "MA20", "MA50"]
        )

        if valid_hist.empty:

            print("Not enough data to evaluate strategy.")

        else:

            # Score the selected strategy
            selected_score = score_strategies(valid_hist, strategy)

            # Check if strategy conditions are satisfied
            fulfilled = selected_score >= 2

            print(f"\nStrategy score: {selected_score}/3")

            if fulfilled:
                print(
                    f"Result: {choice} fulfills "
                    f"the '{strategy}' strategy."
                )
            else:
                print(
                    f"Result: {choice} does NOT fulfill "
                    f"the '{strategy}' strategy."
                )

            # Show latest calculated metrics
            print("\nLatest calculated metrics:")

            print(
                valid_hist[
                    ["Close", "Returns", "Volatility", "Momentum", "MA20", "MA50"]
                ].tail(1).to_string()
            )

except Exception as e:

    print(f"Error fetching data for {choice}: {e}")
