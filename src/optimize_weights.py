import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sector_map import SECTOR_MAP
import warnings

warnings.filterwarnings("ignore")

def get_nifty_regime_history():
    print("   📊 Fetching Nifty 50 Regime History...")
    nifty = yf.download("^NSEI", period="2y", progress=False, auto_adjust=True)
    if isinstance(nifty.columns, pd.MultiIndex): nifty.columns = nifty.columns.get_level_values(0)
    nifty['SMA_200'] = nifty['Close'].rolling(200).mean()
    nifty['Regime_Tag'] = np.where(nifty['Close'] > nifty['SMA_200'], 'BULL', 'BEAR')
    return nifty[['Regime_Tag']]

def calculate_factors_and_slice(df, nifty_regime):
    df = df.copy()
    # Factors
    df['Momentum'] = df['Close'].pct_change(252)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['Volatility'] = df['Close'].pct_change().rolling(20).std()
    
    # Target (Next Month Return)
    df['Next_Month_Return'] = df['Close'].shift(-20) / df['Close'] - 1
    
    df = df.join(nifty_regime, how='left')
    return df.dropna()

def run_regime_optimization():
    print("🧪 STARTING REGIME-BASED OPTIMIZATION LAB...")
    nifty_regime_df = get_nifty_regime_history()
    tickers = list(SECTOR_MAP.keys())[:30]
    
    bull_bucket = []
    bear_bucket = []
    
    for i, ticker in enumerate(tickers):
        try:
            print(f"   [{i+1}/{len(tickers)}] Slicing Data for {ticker}...", end="\r")
            df = yf.download(ticker, period="2y", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            if len(df) > 200:
                processed_df = calculate_factors_and_slice(df, nifty_regime_df)
                bull_bucket.append(processed_df[processed_df['Regime_Tag'] == 'BULL'])
                bear_bucket.append(processed_df[processed_df['Regime_Tag'] == 'BEAR'])
        except: continue
            
    def solve_formula(dataset, regime_name):
        if not dataset: return
        full_df = pd.concat(dataset)
        X = full_df[['Momentum', 'RSI', 'Volatility']]
        y = full_df['Next_Month_Return']
        
        model = LinearRegression()
        model.fit(X, y)
        
        # --- THE TRUTH CHECK ---
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        
        weights = model.coef_
        total = sum(abs(weights))
        w_mom = (weights[0]/total) * 100
        w_rsi = (weights[1]/total) * 100
        w_vol = (weights[2]/total) * 100
        
        print(f"\n\n   🦁 {regime_name} STATISTICS:")
        print("-" * 60)
        print(f"      R-SQUARED (Predictive Power): {r2:.4f}  (Target: >0.02)")
        print("-" * 60)
        print(f"      1. Momentum Weight:   {w_mom:+.1f}%")
        print(f"      2. RSI Weight:        {w_rsi:+.1f}%")
        print(f"      3. Volatility Weight: {w_vol:+.1f}%")
        print("-" * 60)

    solve_formula(bull_bucket, "BULL MARKET")
    solve_formula(bear_bucket, "BEAR MARKET")

if __name__ == "__main__":
    run_regime_optimization()