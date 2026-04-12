"""Stock Advisor Application - Multi-Strategy Stock Analysis & Backtesting Tool

This application provides:
- Technical analysis metrics (volatility, momentum, moving averages)
- 5 different investment strategies (momentum, low_volatility, growth, value, balanced)
- Single stock backtest vs Buy-and-Hold comparison
- Portfolio backtesting across multiple strategies
"""

from matplotlib.pyplot import hist
import yfinance as yf
import pandas as pd
from datetime import date
import numpy as np

TOTAL_RULES_PER_STRATEGY = 3

# ===== DATA INITIALIZATION =====
# Load stock master data and normalize column names
st = pd.read_csv("stocks_master.csv")
st.columns = st.columns.str.strip().str.lower()

# ===== TECHNICAL METRICS CALCULATION =====
def calculate_metrics(hist: pd.DataFrame) -> pd.DataFrame:
    """Calculate key technical indicators for stock analysis.
    
    Metrics computed:
    - Returns: Daily percentage price change
    - Volatility: Annualized 20-day rolling standard deviation
    - Momentum: 60-day price momentum (60-day return %)
    - MA20: 20-day simple moving average
    - MA50: 50-day simple moving average
    - AvgPrice: Mean price over entire period
    """
    hist = hist.copy()
    
    # Calculate daily returns
    hist["Returns"] = hist["Close"].pct_change()
    print("Daily Returns (first 5 days):")
    print(hist["Returns"].head())
    
    # Annualized volatility: roll 20-day std * sqrt(252 trading days)
    hist["Volatility"] = hist["Returns"].rolling(20).std() * (252 ** 0.5)
    print("\nAnnualized Volatility (first 5 days):")
    print(hist["Volatility"].head())
    
    # 60-day momentum captures medium-term trend
    hist["Momentum"] = hist["Close"].pct_change(60)
    
    # Moving averages for trend detection
    hist["MA20"] = hist["Close"].rolling(20).mean()
    hist["MA50"] = hist["Close"].rolling(50).mean()
    
    # Reference price for value strategy
    hist["AvgPrice"] = hist["Close"].mean()
    
    return hist


# ===== STRATEGY SCORING ENGINE =====
def score_strategies(hist: pd.DataFrame, strategy: str) -> float:
    """Score a stock based on selected strategy (0-3 scale).
    
    Each strategy uses 3 key metrics, each contributing 0-1 point max.
    Scoring reflects strength of signal, not just threshold crossing.
    """
    if hist.empty:
        return 0.0

    latest = hist.iloc[-1]
    score = 0.0

    if strategy == "momentum":
        # Momentum strength: 0 at -5%, 1 at +15%
        score += max(0, min((latest["Momentum"] + 0.05) / 0.20, 1))
        # Trend: 0.5 for MA20<MA50, 1 for MA20>MA50
        score += 0.5 + (0.5 if latest["MA20"] > latest["MA50"] else 0)
        # Recent daily return: 0-1 based on magnitude
        score += max(0, min(latest["Returns"] / 0.03, 1))

    elif strategy == "low_volatility":
        # Inverse volatility: 1 at 0%, 0 at 50%+
        score += max(0, 1 - latest["Volatility"] / 0.50)
        # Stable returns: 1 at 0%, 0 at 5%+
        score += max(0, 1 - abs(latest["Returns"]) / 0.05)
        # Trend: 1 for uptrend, 0.3 for downtrend
        score += 1.0 if latest["MA20"] >= latest["MA50"] else 0.3

    elif strategy == "growth":
        # Momentum strength: 0 at 0%, 1 at 20%+
        score += max(0, min(latest["Momentum"] / 0.20, 1))
        # Price vs MA50: how much above
        score += max(0, min((latest["Close"] - latest["MA50"]) / latest["MA50"] / 0.05, 1))
        # Price vs historical average: normalized discount/premium
        score += max(0, min((latest["Close"] - hist["Close"].mean()) / hist["Close"].mean() / 0.10, 1))

    elif strategy == "value":
        # Discount to average: 0 at 0%, 1 at 20%+ discount
        score += max(0, min((hist["Close"].mean() - latest["Close"]) / hist["Close"].mean() / 0.20, 1))
        # Inverse volatility (stable is better for value)
        score += max(0, 1 - latest["Volatility"] / 0.50)
        # Momentum not too negative: 1 at 0%, 0 at -20%
        score += max(0, 1 - max(0, -latest["Momentum"] / 0.20))

    elif strategy == "balanced":
        # Moderate momentum: 1 at 5%, 0 below -5%
        score += max(0, min((latest["Momentum"] + 0.05) / 0.10, 1))
        # Moderate volatility: 1 below 30%, 0 above 50%
        score += max(0, 1 - latest["Volatility"] / 0.50)
        # Trend signal: 1 for up, 0.5 for neutral/down
        score += 1.0 if latest["MA20"] > latest["MA50"] else 0.5

    return min(score, 3.0)


def evaluate_stock(row: pd.Series, strategy: str):
    """Evaluate a single stock against the selected strategy.
    
    Returns: Dictionary with ticker, company name, strategy score, and key metrics.
    Returns None if data is unavailable or insufficient.
    """
    ticker_symbol = row["ticker"]

    try:
        # Fetch 1-year historical data
        hist = yf.Ticker(ticker_symbol).history(period="1y")
    except Exception as e:
        print(f"  Error fetching {ticker_symbol}: {e}")
        return None

    # Validate data availability
    if hist.empty:
        print(f"  {ticker_symbol}: No data available")
        return None

    # Calculate technical metrics and remove NaN values (from rolling calculations)
    metrics = calculate_metrics(hist).dropna()
    if metrics.empty:
        return None

    # Get most recent day's metrics
    latest = metrics.iloc[-1]

    return {
        "ticker": ticker_symbol,
        "company": row.get("company", row.get("name", "N/A")),
        "Score": score_strategies(metrics, strategy),
        "Close": round(latest["Close"], 2),
        "Returns": round(latest["Returns"] * 100, 2),
        "Momentum": round(latest["Momentum"] * 100, 2),
        "Volatility": round(latest["Volatility"] * 100, 2),
    }


# ===== TRADING SIGNAL GENERATION =====
def generate_signal(hist: pd.DataFrame, strategy: str) -> pd.Series:
    """Generate buy/hold signals based on strategy scores over time.
    
    Signal logic:
    - 0-60 days: No signal (insufficient data for 60-day momentum)
    - After day 60: BUY signal (1) if score >= 2.0, HOLD (0) otherwise
    
    Returns: Series of binary signals (0/1) aligned with price history.
    """
    signals = []

    for i in range(len(hist)):
        # Warm-up period: need 60 days for momentum calculation
        if i < 60:
            signals.append(0)
            continue

        # Score based on data up to current day
        window = hist.iloc[:i+1]
        score = score_strategies(window, strategy)
        
        # Buy signal if score exceeds threshold (2.0 out of 3.0 max)
        signals.append(1 if score >= 2.0 else 0)

    return pd.Series(signals, index=hist.index)


# ===== SINGLE STOCK BACKTEST =====
def backtest_single(hist: pd.DataFrame, strategy: str):
    """Backtest strategy on single stock vs buy-and-hold approach.
    
    Compares:
    - Market Return: Buy and hold entire period
    - Strategy Return: Trade based on generated signals
    
    Returns: DataFrame with cumulative returns for comparison.
    """
    # Calculate all technical metrics
    hist = calculate_metrics(hist).dropna()

    # Generate trading signals based on strategy
    hist["Signal"] = generate_signal(hist, strategy)
    
    # Calculate daily returns (what market delivered)
    hist["Market_Return"] = hist["Close"].pct_change()
    
    # Strategy return: only earn returns on days signal=1, lagged by 1 day
    # (realistically, trade executes next day after signal)
    hist["Strategy_Return"] = hist["Signal"].shift(1) * hist["Market_Return"]

    # Cumulative returns: show how $1 would grow over time
    hist["Cumulative_Market"] = (1 + hist["Market_Return"]).cumprod()
    hist["Cumulative_Strategy"] = (1 + hist["Strategy_Return"]).cumprod()

    return hist


# ===== PORTFOLIO BACKTEST =====
def backtest_portfolio(stock_list, strategy):
    """Backtest dynamic portfolio: rebalance daily to top 5 scoring stocks.
    
    Process:
    1. Fetch 1-year history for all stocks
    2. Each trading day, score all stocks using strategy
    3. Select top 5 highest-scoring stocks
    4. Calculate equal-weighted portfolio return
    5. Show cumulative performance over time
    
    Args: stock_list - tickers to evaluate, strategy - scoring strategy name
    Returns: Cumulative portfolio returns series, or None if insufficient data
    """
    all_data = {}

    print("\nFetching data for portfolio backtest...") 

    # Data collection phase
    for ticker in stock_list:
        try:
            hist = yf.Ticker(ticker).history(period="1y")
            if not hist.empty:
                hist = calculate_metrics(hist).dropna() 
                # Require minimum 60 days for momentum calculation
                if len(hist) > 60:
                    all_data[ticker] = hist
        except:
            continue

    if not all_data:
        print("No valid data available.")
        return None

    # Find common trading dates across all stocks
    common_dates = sorted(set.intersection(*(set(df.index) for df in all_data.values())))
    print(f"Backtesting {len(all_data)} stocks over {len(common_dates)} trading days...")

    portfolio_returns = []

    # Daily rebalancing loop
    for i in range(60, len(common_dates)):
        day = common_dates[i]
        scores = []

        # Score each stock based on data available up to this day
        for ticker, df in all_data.items():
            df_slice = df[df.index <= day]
            if len(df_slice) < 60:
                continue

            score = score_strategies(df_slice, strategy)
            scores.append((ticker, score))

        # Select top 5 highest-scoring stocks for today's portfolio
        top_stocks = sorted(scores, key=lambda x: x[1], reverse=True)[:5]
        daily_returns = []

        # Calculate return for each selected stock today
        for ticker, _ in top_stocks:
            df = all_data[ticker]
            if day in df.index:
                prev_idx = df.index.get_loc(day) - 1
                if prev_idx >= 0:
                    prev_day = df.index[prev_idx]
                    # Calculate 1-day return
                    ret = df.loc[day]["Close"] / df.loc[prev_day]["Close"] - 1
                    daily_returns.append(ret)

        # Portfolio return = equal-weighted average of top 5 stocks
        if daily_returns:
            portfolio_returns.append(sum(daily_returns) / len(daily_returns))
        else:
            portfolio_returns.append(0)

    # Calculate cumulative returns from daily returns
    portfolio_series = pd.Series(portfolio_returns)
    cumulative = (1 + portfolio_series).cumprod()

    return cumulative


# ===== USER INPUT HANDLERS =====
def choose_mode():
    """Prompt user to choose analysis mode.
    
    Modes:
    - 'single': Analyze and backtest one stock
    - 'best': Scan all stocks, find top performers, backtest portfolio
    """
    selected = input("Enter 'single' or 'best': ").strip().lower()
    return selected if selected in {"single", "best"} else "single"


def choose_strategy():
    """Prompt user to select investment strategy.
    
    Available strategies:
    - momentum: Trending stocks with positive momentum
    - low_volatility: Stable stocks with predictable returns
    - growth: High-growth stocks outperforming averages
    - value: Undervalued stocks trading below historical average
    - balanced: Moderate growth with stability
    """
    strategies = ["momentum", "low_volatility", "growth", "value", "balanced"]
    print("\nAvailable Strategies:")
    for i, strat in enumerate(strategies, 1):
        print(f"  {i}. {strat}")
    print(f"  Strategies: {', '.join(strategies)}")
    s = input("Choose strategy: ").strip().lower()
    return s if s in strategies else "balanced"


# ===== MAIN APPLICATION FLOW =====
print("="*60)
print("Welcome to Stock Advisor - Multi-Strategy Analysis Tool")
print("="*60)
print("This application analyzes stocks based on different strategies")
print("and provides backtest results comparing strategy vs buy-and-hold.")
print("="*60)

mode = choose_mode()
strategy = choose_strategy()


# ===== SINGLE STOCK MODE =====
if mode == "single":
    print("\n" + "-"*60)
    print("SINGLE STOCK ANALYSIS MODE")
    print("-"*60)
    ticker_symbol = input("Enter ticker symbol (e.g., AAPL, MSFT): ").strip().upper()

    print(f"Fetching 1-year historical data for {ticker_symbol}...")
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="1y")

    if hist.empty:
        print(f"❌ No data found for ticker: {ticker_symbol}")
    else:
        print(f"✓ Successfully loaded {len(hist)} trading days of data")
        
        # Run backtest
        print(f"\nRunning {strategy.upper()} strategy backtest...")
        bt = backtest_single(hist, strategy)

        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        market_return = (bt['Cumulative_Market'].iloc[-1] - 1) * 100
        strategy_return = (bt['Cumulative_Strategy'].iloc[-1] - 1) * 100
        outperformance = strategy_return - market_return
        
        print(f"Buy & Hold Return:    {market_return:>8.2f}%")
        print(f"Strategy Return:      {strategy_return:>8.2f}%")
        print(f"Outperformance:       {outperformance:>8.2f}%")
        print("-"*60)
        
        # Determine winner
        if outperformance > 1:
            print(f"✓ Strategy BEAT buy-and-hold by {outperformance:.2f}%")
        elif outperformance < -1:
            print(f"✗ Strategy UNDERPERFORMED buy-and-hold by {abs(outperformance):.2f}%")
        else:
            print(f"≈ Strategy MATCHED buy-and-hold performance")


# ===== BEST PERFORMERS MODE (PORTFOLIO) =====
else:
    print("\n" + "-"*60)
    print("PORTFOLIO ANALYSIS MODE - Finding Best Performers")
    print("-"*60)
    print(f"Evaluating all stocks using {strategy.upper()} strategy...")
    print("This may take a few moments...\n")

    # Load all stocks from master data
    filtered_stocks = st.dropna(subset=["ticker"]).copy()
    evaluated_stocks = []

    # Score each stock
    for idx, (_, row) in enumerate(filtered_stocks.iterrows()):
        if idx % 10 == 0:
            print(f"  Evaluated {idx}/{len(filtered_stocks)} stocks...", end="\r")
        stock_data = evaluate_stock(row, strategy)
        if stock_data is not None:
            evaluated_stocks.append(stock_data)

    if not evaluated_stocks:
        print("❌ No valid stock data found.")
        best_stocks = pd.DataFrame(columns=["ticker", "company", "Score", "Close", "Returns", "Momentum", "Volatility"])
    else:
        print(f"✓ Successfully evaluated {len(evaluated_stocks)} stocks          ")
        
        # Sort by strategy score, then by momentum for tie-breaking
        scored_stocks = pd.DataFrame(evaluated_stocks)
        best_stocks = scored_stocks.sort_values(
            by=["Score", "Momentum"],
            ascending=[False, False]
        ).head(10)

    print("\n" + "="*60)
    print("TOP 10 STOCKS BY STRATEGY SCORE")
    print("="*60)
    print(
        best_stocks[
            ["ticker", "company", "Score", "Close", "Returns", "Momentum", "Volatility"]
        ].to_string(index=False)
    )
    print("="*60)

    # Optional portfolio backtesting
    if not best_stocks.empty and input("\nBacktest top performers as dynamic portfolio? (y/n): ").lower() == "y":
        print("\n" + "-"*60)
        print("PORTFOLIO BACKTEST")
        print("-"*60)
        
        tickers = best_stocks["ticker"].tolist()
        result = backtest_portfolio(tickers, strategy)

        if result is not None:
            print("\n" + "="*60)
            print("PORTFOLIO BACKTEST RESULTS")
            print("="*60)
            portfolio_return = (result.iloc[-1] - 1) * 100
            print(f"Portfolio Return (Equal-Weighted Top 5, Daily Rebalance):")
            print(f"  {portfolio_return:.2f}% over 1 year")
            print("="*60)
