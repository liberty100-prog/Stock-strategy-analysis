

Stock Strategy Evaluator

A Python command-line tool that analyzes historical stock market data and evaluates whether a stock satisfies different investment strategies using financial indicators such as momentum, volatility, and moving averages.

The tool fetches stock data using yfinance, calculates several financial metrics using pandas, and scores a selected strategy based on predefined rules.


Features
	•	Fetches historical stock data using yfinance
	•	Calculates important financial indicators:
	•	Daily returns
	•	Volatility
	•	Momentum
	•	Moving averages
	•	Supports multiple investment strategies
	•	Allows custom time frame analysis
	•	Provides strategy score and latest metrics



Available Strategies

Momentum

Focuses on stocks with strong recent performance and positive trends.

Rules:
	•	60-day momentum > 5%
	•	20-day moving average > 50-day moving average
	•	Positive daily return


Low Volatility

Prefers stocks with stable price movement and lower risk.

Rules:
	•	Volatility < 30%
	•	Daily return within ±2%
	•	Stable trend (MA20 ≥ MA50)



Value

Targets stocks trading below their historical average price.

Rules:
	•	Current price < average price
	•	Volatility < 35%
	•	Momentum not strongly negative



Balanced

A mix of return, trend strength, and risk control.

Rules:
	•	Positive momentum
	•	Volatility < 35%
	•	MA20 > MA50



Technologies Used
	•	Python
	•	pandas – data analysis
	•	yfinance – financial market data
	•	datetime – time handling

Installation

Clone the repository:

git clone https://github.com/yourusername/stock-strategy-evaluator.git

Move into the project folder:

cd stock-strategy-evaluator

Install dependencies:

pip install pandas yfinance


Usage

Run the script:

python stock_strategy_evaluator.py

You will be prompted to:
	1.	Select an investment strategy
	2.	Enter a stock ticker (example: AAPL, TSLA, MSFT)
	3.	Choose whether to specify a custom time frame

Example interaction:

Welcome to the Stock Advisor tool

Available strategies:
1. momentum
2. low_volatility
3. value
4. balanced

Select strategy: momentum
Enter preferred stock ticker: AAPL
Is a custom time frame needed? no

Output example:

Strategy score: 2/3
Result: AAPL fulfills the 'momentum' strategy.

Latest calculated metrics:
Close   Returns   Volatility   Momentum   MA20   MA50




Example Metrics Calculated

Metric	Description
Returns	Daily percentage price change
Volatility	Annualized standard deviation of returns
Momentum	60-day percentage return
MA20	20-day moving average
MA50	50-day moving average


Possible Improvements

Future enhancements could include:
	•	Visualization of stock price trends
	•	Ranking multiple stocks by strategy score
	•	Portfolio recommendation system
	•	Backtesting strategies
	•	Web dashboard interface



License

This project is open source and available under the MIT License.
