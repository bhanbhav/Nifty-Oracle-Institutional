import yfinance as yf
import pandas as pd
import time
from sector_map import SECTOR_MAP # We use this just to get the list of tickers

def get_piotroski_score(ticker):
    """Calculates the 9-Point F-Score."""
    try:
        stock = yf.Ticker(ticker)
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        if financials.empty or balance_sheet.empty or cashflow.empty: return 0
        if len(financials.columns) < 2: return 0
            
        curr, prev = 0, 1
        score = 0
        
        # 1. ROA
        try:
            net_income = financials.loc['Net Income'].iloc[curr]
            total_assets = balance_sheet.loc['Total Assets'].iloc[curr]
            roa = net_income / total_assets
            if roa > 0: score += 1
        except: pass
        
        # 2. CFO
        try:
            cfo = cashflow.loc['Operating Cash Flow'].iloc[curr]
            if cfo > 0: score += 1
        except: pass
        
        # 3. Delta ROA
        try:
            prev_ni = financials.loc['Net Income'].iloc[prev]
            prev_assets = balance_sheet.loc['Total Assets'].iloc[prev]
            if roa > (prev_ni / prev_assets): score += 1
        except: pass
        
        # 4. Quality (Accruals)
        try:
            if cfo > net_income: score += 1
        except: pass
        
        # 5. Delta Leverage
        try:
            debt = balance_sheet.loc['Long Term Debt'].iloc[curr] if 'Long Term Debt' in balance_sheet.index else 0
            prev_debt = balance_sheet.loc['Long Term Debt'].iloc[prev] if 'Long Term Debt' in balance_sheet.index else 0
            if (debt/total_assets) < (prev_debt/prev_assets): score += 1
        except: pass
        
        # 6. Delta Liquidity
        try:
            curr_ratio = balance_sheet.loc['Current Assets'].iloc[curr] / balance_sheet.loc['Current Liabilities'].iloc[curr]
            prev_curr_ratio = balance_sheet.loc['Current Assets'].iloc[prev] / balance_sheet.loc['Current Liabilities'].iloc[prev]
            if curr_ratio > prev_curr_ratio: score += 1
        except: pass
        
        # 7. Dilution
        try:
            shares = balance_sheet.loc['Ordinary Shares Number'].iloc[curr] if 'Ordinary Shares Number' in balance_sheet.index else 0
            prev_shares = balance_sheet.loc['Ordinary Shares Number'].iloc[prev] if 'Ordinary Shares Number' in balance_sheet.index else 0
            if shares <= prev_shares: score += 1
        except: pass

        # 8. Delta Margin
        try:
            gm = financials.loc['Gross Profit'].iloc[curr] / financials.loc['Total Revenue'].iloc[curr]
            prev_gm = financials.loc['Gross Profit'].iloc[prev] / financials.loc['Total Revenue'].iloc[prev]
            if gm > prev_gm: score += 1
        except: pass
        
        # 9. Delta Turnover
        try:
            at = financials.loc['Total Revenue'].iloc[curr] / total_assets
            prev_at = financials.loc['Total Revenue'].iloc[prev] / prev_assets
            if at > prev_at: score += 1
        except: pass
        
        return score

    except Exception as e:
        return 0

def scan_market():
    tickers = list(SECTOR_MAP.keys())
    print(f"🏥 Starting Health Scan for {len(tickers)} companies...")
    print("   (This relies on yFinance, so it might take 1-2 mins)")
    
    results = []
    
    for symbol in tickers:
        score = get_piotroski_score(symbol)
        print(f"   👉 {symbol}: {score}/9")
        results.append({'symbol': symbol, 'F_Score': score})
        # Sleep briefly to avoid getting blocked by Yahoo
        time.sleep(0.5) 
        
    # Save Results
    df = pd.DataFrame(results)
    df.to_csv('src/fundamental_data.csv', index=False)
    print("\n✅ Scan Complete. Results saved to 'src/fundamental_data.csv'.")
    
    # Show Top Picks
    print("\n🏆 THE HONOR ROLL (Score >= 7):")
    print(df[df['F_Score'] >= 7])

if __name__ == "__main__":
    scan_market()