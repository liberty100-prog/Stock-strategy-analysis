import yfinance as yf
from datetime import date


TOTAL_RULES_PER_STRATEGY = 3


def calculate_metrics(hist):
    hist = hist.copy()

    # Daily returns
    hist["Returns"] = hist["Close"].pct_change()

    # Rolling volatility (annualized)
    hist["Volatility"] = hist["Returns"].rolling(20).std() * (252 ** 0.5)

    # Momentum (60-day return)
    hist["Momentum"] = hist["Close"].pct_change(60)

    # Moving averages
    hist["MA20"] = hist["Close"].rolling(20).mean()
    hist["MA50"] = hist["Close"].rolling(50).mean()

    # Average price (constant column)
    hist["AvgPrice"] = hist["Close"].mean()

    return hist


def score_strategies(hist):
    latest = hist.iloc[-1]

    scores = {
        "momentum": 0,
        "low_volatility": 0,
        "value": 0,
        "balanced": 0,
    }

    # MOMENTUM STRATEGY
    if latest["Momentum"] > 0.05:
        scores["momentum"] += 1
    if latest["MA20"] > latest["MA50"]:
        scores["momentum"] += 1
    if latest["Returns"] > 0:
        scores["momentum"] += 1

    # LOW VOLATILITY STRATEGY
    if latest["Volatility"] < 0.30:
        scores["low_volatility"] += 1
    if abs(latest["Returns"]) < 0.02:
        scores["low_volatility"] += 1
    if latest["MA20"] >= latest["MA50"]:
        scores["low_volatility"] += 1

    # VALUE STRATEGY
    avg_price = hist["Close"].mean()
    if latest["Close"] < avg_price:
        scores["value"] += 1
    if latest["Volatility"] < 0.35:
        scores["value"] += 1
    if latest["Momentum"] > -0.05:
        scores["value"] += 1

    # BALANCED STRATEGY
    if latest["Momentum"] > 0:
        scores["balanced"] += 1
    if latest["Volatility"] < 0.35:
        scores["balanced"] += 1
    if latest["MA20"] > latest["MA50"]:
        scores["balanced"] += 1

    return scores


STRATEGY_DESCRIPTIONS = {
    "momentum": "Favors stronger recent returns and trend strength.",
    "low_volatility": "Prefers lower volatility and steadier names.",
    "value": "Tilts toward lower price and dividend-supporting picks.",
    "balanced": "Mix of return, momentum, and risk control.",
}


def choose_strategy() -> str:
    strategy_names = list(STRATEGY_DESCRIPTIONS.keys())
    print("\nAvailable strategies:")
    for i, name in enumerate(strategy_names, start=1):
        print(f"{i}. {name} - {STRATEGY_DESCRIPTIONS[name]}")

    selected = input("Select strategy by number or name (default: balanced): ").strip().lower()
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


def evaluate_selected_strategy(scores, selected_strategy):
    selected_score = scores[selected_strategy]
    is_fulfilled = selected_score >= 2
    return selected_score, is_fulfilled


print("Welcome to the Stock Advisor tool")
strategy = choose_strategy()

choice = input("enter prefered stock name: ").strip()
c = input("is time frame needed? (yes/no): ").strip().lower()

start_date = None
end_date = str(date.today())
if c == "yes":
    start_date = input("enter start date in yyyy-mm-dd format: ").strip()
    e = input("enter end date in yyyy-mm-dd format (leave blank for current date): ").strip()
    if e:
        end_date = e

print(f"\nSelected strategy: {strategy}")
print(f"Selected stock: {choice}")
if start_date:
    print(f"Time frame: {start_date} to {end_date}")
else:
    print("Time frame: default (last 1 year)")

print("\nFetching data and analyzing...")

try:
    ticker = yf.Ticker(choice)
    hist = ticker.history(start=start_date, end=end_date) if start_date else ticker.history(period="1y")

    if hist.empty:
        print("No data found for the specified stock and time frame.")
    else:
        print(f"Data fetched for {choice} from {hist.index[0].date()} to {hist.index[-1].date()}.")
        hist = calculate_metrics(hist)

        valid_hist = hist.dropna(subset=["Returns", "Volatility", "Momentum", "MA20", "MA50"])
        if valid_hist.empty:
            print("Not enough data to evaluate strategies after calculating metrics.")
        else:
            
            selected_score, fulfilled = evaluate_selected_strategy(scores, strategy)

            

            print(f"\nSelected strategy score: {selected_score}/3")
            if fulfilled:
                print(f"Result: {choice} fulfills the '{strategy}' strategy.")
            else:
                print(f"Result: {choice} does NOT fulfill the '{strategy}' strategy.")

           

            print("\nLatest calculated metrics:")
            print(valid_hist[["Close", "Returns", "Volatility", "Momentum", "MA20", "MA50"]].tail(1).to_string())

except Exception as e:
    print(f"Error fetching data for {choice}: {e}")
