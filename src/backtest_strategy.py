import yfinance as yf
import pandas as pd
import numpy as np
from sector_map import SECTOR_MAP
import warnings

warnings.filterwarnings("ignore")

START_DATE = "2024-01-01"
END_DATE = "2024-12-31" 
INITIAL_CAPITAL = 100000

def get_historical_data(tickers):
    # (Same chunking logic as before...)
    print(f"   ⏳ Downloading history for {len(tickers)} stocks...")
    chunk_size = 50
    all_data = []
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        try:
            df = yf.download(chunk, start=START_DATE, end=END_DATE, interval="1d", progress=False, auto_adjust=True, threads=False)['Close']
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            all_data.append(df)
            print(f"      Batch {i//chunk_size + 1} downloaded...", end="\r")
        except: continue
    if not all_data: return pd.DataFrame()
    return pd.concat(all_data, axis=1)

def calculate_monthly_scores(date, data):
    # (Same logic as your previous successful backtest)
    scores = {}
    past_data = data.loc[:date]
    if len(past_data) < 200: return []
    
    if '^NSEI' not in data.columns: return []
    nifty = past_data['^NSEI'].dropna()
    regime = "BULLISH"
    if nifty.iloc[-1] < nifty.rolling(200).mean().iloc[-1]: regime = "BEARISH"
        
    for ticker in data.columns:
        if ticker == "^NSEI": continue
        try:
            series = past_data[ticker].dropna()
            if len(series) < 200: continue
            
            close = series.iloc[-1]
            mom = series.pct_change(126).iloc[-1]
            ret = series.pct_change().dropna()
            neg_ret = ret[ret < 0]
            downside_risk = neg_ret.std() if len(neg_ret) > 10 else 0.02
            
            mom_score = mom * 100
            risk_score = downside_risk * 1000 
            
            if regime == "BULLISH":
                tech_score = (mom_score * 0.4) - (risk_score * 0.6)
            else:
                tech_score = (mom_score * 0.1) - (risk_score * 0.9)
            scores[ticker] = tech_score
        except: continue
        
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [x[0] for x in sorted_scores[:10]]

def calculate_max_drawdown(wealth_index):
    """ Calculates the worst peak-to-trough crash """
    peaks = wealth_index.cummax()
    drawdown = (wealth_index - peaks) / peaks
    return drawdown.min()

def calculate_sharpe_ratio(returns):
    """ Calculates Risk-Adjusted Return (Annualized) """
    if returns.std() == 0: return 0
    return (returns.mean() / returns.std()) * np.sqrt(12) # Annualized for monthly data

def run_backtest():
    print("\n🚀 STARTING INSTITUTIONAL VALIDATION BACKTEST...")
    tickers = list(SECTOR_MAP.keys()) + ["^NSEI"]
    data = get_historical_data(tickers)
    
    if data.empty: return
    
    monthly_prices = data.resample('ME').last()
    portfolio_value = INITIAL_CAPITAL
    
    history = []
    current_holdings = []
    monthly_returns = []
    
    print(f"\n   📊 Processing {len(monthly_prices)} months...")
    
    for date, row in monthly_prices.iterrows():
        # 1. Performance Calculation
        if current_holdings:
            curr_idx = monthly_prices.index.get_loc(date)
            if curr_idx > 0:
                prev_date = monthly_prices.index[curr_idx - 1]
                month_ret = 0
                valid = 0
                for ticker in current_holdings:
                    if ticker in data.columns:
                        p_start = monthly_prices.loc[prev_date, ticker]
                        p_end = row[ticker]
                        if not pd.isna(p_start) and not pd.isna(p_end) and p_start > 0:
                            ret = (p_end - p_start) / p_start
                            month_ret += ret
                            valid += 1
                
                avg_ret = month_ret / valid if valid > 0 else 0
                portfolio_value *= (1 + avg_ret)
                monthly_returns.append(avg_ret)

        # 2. Rebalance
        current_holdings = calculate_monthly_scores(date, data)
        history.append(portfolio_value)
    
    # --- INSTITUTIONAL REPORT CARD ---
    history_series = pd.Series(history)
    returns_series = pd.Series(monthly_returns)
    
    final_return = (portfolio_value - INITIAL_CAPITAL) / INITIAL_CAPITAL
    max_dd = calculate_max_drawdown(history_series)
    sharpe = calculate_sharpe_ratio(returns_series)
    
    print("\n\n🏆 INSTITUTIONAL REPORT CARD (2024):")
    print("=" * 50)
    print(f"   💰 Total Return:    {final_return:+.1%}  (Abs Return)")
    print(f"   📉 Max Drawdown:    {max_dd:+.1%}  (Worst Crash)")
    print(f"   ⚖️  Sharpe Ratio:    {sharpe:.2f}   (Target > 1.0)")
    print("=" * 50)
    
    if sharpe > 1.0 and max_dd > -0.15:
        print("   ✅ VERDICT: REAL SOLUTION (Fund Grade)")
    elif sharpe > 0.5:
        print("   ⚠️ VERDICT: DECENT (Retail Grade)")
    else:
        print("   ❌ VERDICT: FAILED (High Risk / Low Reward)")

if __name__ == "__main__":
    run_backtest()