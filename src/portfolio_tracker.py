import pandas as pd
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

# CONFIGURATION
LOG_FILE = "nifty_oracle_log.csv"
CAPITAL = 100000  # Virtual capital for tracking (₹1 Lakh)

def track_portfolio():
    print(f"\n📊 LOADING PORTFOLIO TRACKER (Capital Base: ₹{CAPITAL:,.0f})...")
    
    try:
        # 1. Read the Memory Log
        log_df = pd.read_csv(LOG_FILE)
        
        # Get the latest set of trades (Filter for the most recent date)
        latest_date = log_df['Date'].max()
        portfolio = log_df[log_df['Date'] == latest_date].copy()
        
        if portfolio.empty:
            print("❌ Log file is empty or invalid.")
            return
            
        print(f"   📅 Tracking Positions from: {latest_date}")
        
    except FileNotFoundError:
        print("❌ No trade log found. Run 'predict_daily.py' first.")
        return

    # 2. Fetch Live Prices
    tickers = portfolio['Ticker'].tolist()
    print(f"   🌍 Fetching live prices for: {', '.join(tickers)}...")
    
    # Download live data
    live_data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
    
    # Handle single-ticker result format difference
    if isinstance(live_data, pd.Series): 
        live_data = live_data.to_frame()
        # If the series name isn't the ticker, we might need to adjust, 
        # but yf usually handles single ticker downloads by returning a DataFrame if asked correctly.
        # Safer fallback:
        current_prices = {tickers[0]: live_data.iloc[-1].item()}
    else:
        # Get the very last price available (current market price)
        current_prices = live_data.iloc[-1].to_dict()

    # 3. Calculate P&L
    print("\n" + "="*95)
    print(f"{'SYMBOL':<15} | {'ENTRY (₹)':<10} | {'CURRENT (₹)':<11} | {'CHANGE %':<10} | {'VALUE (₹)':<12} | {'P&L (₹)':<10}")
    print("-" * 95)
    
    total_value = 0
    total_pl = 0
    
    for index, row in portfolio.iterrows():
        ticker = row['Ticker']
        entry_price = row['Entry_Price']
        weight = row['Weight']
        
        # Get Live Price (Handle Multi-Index columns if present)
        try:
            current_price = current_prices[ticker]
        except KeyError:
            # Fallback for Index or formatting mismatches
            current_price = entry_price # Assume flat if data fetch fails
            
        # Performance Math
        # How much capital was allocated?
        invested_amt = CAPITAL * weight
        
        # How many units did we buy?
        units = invested_amt / entry_price
        
        # What is it worth now?
        current_amt = units * current_price
        
        # P&L
        pl_amt = current_amt - invested_amt
        pl_pct = ((current_price - entry_price) / entry_price) * 100
        
        total_value += current_amt
        total_pl += pl_amt
        
        # Color coding for terminal (Optional, simplified here)
        print(f"{ticker:<15} | {entry_price:<10.2f} | {current_price:<11.2f} | {pl_pct:>7.2f}%  | ₹{current_amt:<11,.2f} | {pl_amt:>+9.2f}")

    print("-" * 95)
    
    # Total Portfolio Stats
    total_return_pct = (total_pl / CAPITAL) * 100
    print(f"💰 TOTAL PORTFOLIO VALUE: ₹{total_value:,.2f}")
    print(f"📈 TOTAL P&L:             ₹{total_pl:,.2f} ({total_return_pct:+.2f}%)")
    print("=" * 95)

if __name__ == "__main__":
    track_portfolio()