import pandas as pd
import time
from sector_map import SECTOR_MAP
from valuation_logic import calculate_intrinsic_value

def scan_valuations():
    print(f"💎 Starting Valuation Scan for {len(SECTOR_MAP)} companies...")
    print("   (This involves heavy number crunching, please wait...)")
    
    results = []
    
    tickers = list(SECTOR_MAP.keys())
    
    for i, ticker in enumerate(tickers):
        print(f"   [{i+1}/{len(tickers)}] Analyzing {ticker}...", end=" ", flush=True)
        
        fair_value, is_undervalued, method = calculate_intrinsic_value(ticker)
        
        # Get current price for context (using yfinance inside the loop is slow but simple)
        try:
            import yfinance as yf
            current_price = yf.Ticker(ticker).history(period='1d')['Close'].iloc[-1]
        except:
            current_price = 0
            
        # Calculate Margin of Safety %
        # (Fair - Price) / Price
        if current_price > 0:
            upside = (fair_value - current_price) / current_price
        else:
            upside = 0
            
        print(f"-> Fair: {fair_value:.0f} | Upside: {upside:.1%}")
        
        results.append({
            'symbol': ticker,
            'current_price': round(current_price, 2),
            'fair_value': fair_value,
            'valuation_method': method,
            'upside_potential': round(upside, 4),
            'is_undervalued': is_undervalued
        })
        
        # Sleep to be polite to Yahoo API
        time.sleep(0.2)

    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv('src/valuation_data.csv', index=False)
    
    print("\n✅ Valuation Scan Complete. Saved to 'src/valuation_data.csv'.")
    
    # Show the "Deep Value" picks
    print("\n💰 DEEP VALUE OPPORTUNITIES (30% Margin of Safety):")
    value_picks = df[df['is_undervalued'] == True]
    if not value_picks.empty:
        print(value_picks[['symbol', 'current_price', 'fair_value', 'upside_potential']])
    else:
        print("   (No deep value stocks found. Market is expensive!)")

if __name__ == "__main__":
    scan_valuations()