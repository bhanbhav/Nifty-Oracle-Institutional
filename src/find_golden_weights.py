import yfinance as yf
import pandas as pd
import numpy as np
from sector_map import SECTOR_MAP
import itertools
import warnings

warnings.filterwarnings("ignore")

# --- CONFIG ---
# DOWNLOAD START: Need 1 year buffer for 200-SMA calc
DOWNLOAD_START = "2023-01-01" 
# TEST START: Where we actually begin the optimization
TEST_START = "2024-01-01"
TEST_END = "2024-12-31"

def get_data_and_regime():
    print("⏳ Downloading Universe Data (w/ history buffer)...")
    tickers = list(SECTOR_MAP.keys()) + ["^NSEI"]
    
    # Chunked download to prevent errors
    chunk_size = 50
    all_data = []
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        try:
            df = yf.download(chunk, start=DOWNLOAD_START, end=TEST_END, interval="1d", progress=False, auto_adjust=True, threads=False)['Close']
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            all_data.append(df)
            print(f"   Batch {i//chunk_size + 1} downloaded...", end="\r")
        except: continue
    
    print("\n   Processing Data...")
    if not all_data: return None, None, None
    data = pd.concat(all_data, axis=1)
    
    # Calculate Regime (Bull/Bear)
    # We use data from 2023 to calc SMA, but valid_regime starts later
    nifty = data['^NSEI'].copy()
    sma_200 = nifty.rolling(200).mean()
    
    # 1 = Bull, 0 = Bear. (NaN if not enough data)
    regime_mask = np.where(nifty > sma_200, 'BULL', 'BEAR')
    regime_df = pd.DataFrame(regime_mask, index=data.index, columns=['Regime'])
    
    # Mask out the warmup period (2023)
    # We only want to optimize on 2024 data
    regime_df = regime_df.loc[TEST_START:] 
    
    print("📊 Calculating Factors...")
    factors = {}
    
    for ticker in tickers:
        if ticker == "^NSEI": continue
        try:
            series = data[ticker]
            # 1. Momentum (126 day)
            mom = series.pct_change(126)
            
            # 2. Safety (Inverse of Downside Volatility)
            ret = series.pct_change()
            downside = ret.apply(lambda x: 0 if x > 0 else x**2).rolling(20).mean().apply(np.sqrt)
            safety = 1 / (downside + 0.001)
            
            # 3. Value Proxy (Distance from 52-week Low)
            low_52 = series.rolling(252).min()
            val_proxy = (series - low_52) / low_52
            val_score = 1 / (val_proxy + 0.1)

            # Combine and trim to Test Period only
            df_f = pd.DataFrame({
                'Momentum': mom,
                'Safety': safety,
                'Value': val_score
            })
            factors[ticker] = df_f.loc[TEST_START:]
            
        except: continue
        
    # Trim prices to Test Period too
    prices = data.loc[TEST_START:]
        
    return prices, regime_df, factors

def backtest_weights(weights, factors, prices, regime_series, target_regime):
    w_mom, w_safe, w_val = weights
    
    # Filter dates where Regime matches Target (e.g., only check BULL days)
    valid_dates = regime_series[regime_series['Regime'] == target_regime].index
    
    # Rebalance Monthly
    monthly_dates = [d for d in valid_dates if d.is_month_end]
    
    if not monthly_dates: return -999 # No days found for this regime

    returns = []
    
    for date in monthly_dates:
        daily_scores = {}
        for ticker, df_feat in factors.items():
            if date not in df_feat.index: continue
            row = df_feat.loc[date]
            
            # Normalize inputs roughly so weights matter
            # (Simple Z-score like normalization logic is implicit here for speed)
            score = (row['Momentum'] * w_mom) + (row['Safety'] * w_safe * 0.1) + (row['Value'] * w_val)
            
            if not np.isnan(score):
                daily_scores[ticker] = score
        
        if not daily_scores: continue
        
        # Pick Top 10
        top_picks = sorted(daily_scores, key=daily_scores.get, reverse=True)[:10]
        
        try:
            current_price = prices.loc[date, top_picks]
            # Look forward 20 trading days
            future_idx = prices.index.get_loc(date) + 20
            if future_idx < len(prices):
                future_date = prices.index[future_idx]
                future_price = prices.loc[future_date, top_picks]
                
                period_ret = (future_price - current_price) / current_price
                returns.append(period_ret.mean())
        except: pass
        
    return np.mean(returns) if returns else -999

def optimize():
    prices, regime, factors = get_data_and_regime()
    if prices is None: return

    # Grid Search Options
    options = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    combinations = [p for p in itertools.product(options, repeat=3) if abs(sum(p) - 1.0) < 0.01]
    
    print(f"\n🧪 Testing {len(combinations)} combinations...")
    
    # --- BULL ---
    print("\n🐂 OPTIMIZING BULL MARKET...")
    best_bull_ret = -999
    best_bull_w = (0.5, 0.0, 0.5) # Default fallback
    
    for w in combinations:
        ret = backtest_weights(w, factors, prices, regime, "BULL")
        if ret > best_bull_ret and ret != -999:
            best_bull_ret = ret
            best_bull_w = w
            print(f"   New Best: Mom {w[0]:.1f} | Safe {w[1]:.1f} | Val {w[2]:.1f} -> {ret*100:.2f}%")
            
    # --- BEAR ---
    print("\n🐻 OPTIMIZING BEAR MARKET...")
    best_bear_ret = -999
    best_bear_w = (0.0, 1.0, 0.0) # Default fallback
    
    for w in combinations:
        ret = backtest_weights(w, factors, prices, regime, "BEAR")
        if ret > best_bear_ret and ret != -999:
            best_bear_ret = ret
            best_bear_w = w
            print(f"   New Best: Mom {w[0]:.1f} | Safe {w[1]:.1f} | Val {w[2]:.1f} -> {ret*100:.2f}%")

    print("\n" + "="*60)
    print("🏆 THE GOLDEN WEIGHTS")
    print("="*60)
    print(f"🚀 BULL: Momentum {best_bull_w[0]*100:.0f}% | Safety {best_bull_w[1]*100:.0f}% | Value {best_bull_w[2]*100:.0f}%")
    print(f"🛡️ BEAR: Momentum {best_bear_w[0]*100:.0f}% | Safety {best_bear_w[1]*100:.0f}% | Value {best_bear_w[2]*100:.0f}%")
    print("="*60)

if __name__ == "__main__":
    optimize()