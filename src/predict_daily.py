import pandas as pd
import numpy as np
import yfinance as yf
import os
import warnings
import sys
from datetime import datetime

# --- INTERNAL MODULES ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from sector_map import SECTOR_MAP
except ImportError:
    SECTOR_MAP = {}
    
from sentiment_engine import NewsSentimentEngine
from valuation_logic import get_intrinsic_value
# (If you don't have portfolio_manager or reality_simulator yet, comment these out)
# from portfolio_manager import PortfolioManager
# from reality_simulator import IndiaTradingCostModel

warnings.filterwarnings("ignore")
LOG_FILE = "nifty_oracle_log.csv"
SENTIMENT_THRESHOLD = -0.20
SAMPLE_MODE = False  # Set to True for fast testing

def get_market_regime():
    print("\n🌎 ANALYZING MARKET REGIME...", flush=True)
    try:
        nifty = yf.download("^NSEI", period="1y", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
        
        current_price = float(nifty.iloc[-1])
        sma200 = float(nifty.rolling(200).mean().iloc[-1])
        
        if current_price < sma200:
            return {"status": "BEARISH", "multiplier": 0.8}
        return {"status": "BULLISH", "multiplier": 1.2}
    except:
        return {"status": "NEUTRAL", "multiplier": 1.0}

def calculate_downside_deviation(series):
    returns = series.pct_change().dropna()
    negative_returns = returns[returns < 0]
    if len(negative_returns) < 2: return 0.02
    return float(negative_returns.std())

def calculate_composite_score(row, regime_status):
    if row['Status'] != 'Active': return 0.0
    
    mom_rank = row.get('Momentum_Rank', 0.5)
    safe_rank = row.get('Safety_Rank', 0.5)
    val_rank = np.clip((row.get('Upside_Pct', 0) + 0.2), 0, 1)
    
    if regime_status == "BULLISH":
        w_mom, w_safe, w_val = 0.18, 0.36, 0.36
        base_score = (mom_rank * w_mom) + (safe_rank * w_safe) + (val_rank * w_val)
    else:
        w_safe = 0.90
        base_score = (safe_rank * w_safe)
    
    return round(base_score * 100, 1)

def make_predictions():
    regime = get_market_regime()
    
    # 1. GET FULL LIST
    full_list = [t for t in SECTOR_MAP.keys() if len(str(t)) > 2]
    # Fallback if sector map is empty
    if not full_list:
        full_list = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "^NSEI"]
        
    tickers = full_list[:20] if SAMPLE_MODE else full_list
    if "^NSEI" not in tickers: tickers.append("^NSEI")
    
    print(f"📡 AUDITING {len(tickers)} ASSETS (Audit Mode: ON)...", flush=True)
    
    candidates = []
    sent_engine = NewsSentimentEngine()
    
    for i, ticker in enumerate(tickers):
        row_data = {
            'symbol': ticker, 'Close': 0, 'Momentum_Raw': 0,
            'Downside_Risk_Raw': 0, 'Upside_Pct': 0,
            'News_Score': 0, 'F_Score': 0, 'Fair_Value': 0,
            'Status': 'Unknown'
        }
        
        try:
            df = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
            
            if df is None or df.empty or len(df) < 100:
                row_data['Status'] = 'Data Error'
                candidates.append(row_data)
                print(f"[{i+1}/{len(tickers)}] ❌ {ticker}: Data Error", end="\r", flush=True)
                continue
            
            # Metrics
            if isinstance(df.columns, pd.MultiIndex):
                # Fix for new yfinance format
                close_series = df.xs('Close', axis=1, level=0).iloc[:, 0]
            else:
                close_series = df['Close']
                
            close_price = float(close_series.iloc[-1])
            momentum = float(close_series.pct_change(126).iloc[-1])
            downside_risk = calculate_downside_deviation(close_series)
            
            # Advanced
            f_score = 5 
            fair_val = get_intrinsic_value(ticker)
            upside_pct = (fair_val - close_price) / close_price if fair_val else 0
            news_score, _, _ = sent_engine.get_sentiment(ticker)
            
            row_data.update({
                'Close': close_price, 'Momentum_Raw': momentum,
                'Downside_Risk_Raw': downside_risk, 'Upside_Pct': upside_pct,
                'News_Score': news_score, 'F_Score': f_score,
                'Fair_Value': fair_val
            })
            
            if news_score < SENTIMENT_THRESHOLD:
                row_data['Status'] = 'Rejected: Sentiment'
            else:
                row_data['Status'] = 'Active'
                
        except Exception as e:
            row_data['Status'] = f'Error: {str(e)[:20]}'
        
        candidates.append(row_data)
        status_icon = "✅" if row_data['Status'] == 'Active' else "⚠️"
        print(f"[{i+1}/{len(tickers)}] {status_icon} Scanned {ticker} ({row_data['Status']})   ", end="\r", flush=True)

    # 3. RANKING
    df_results = pd.DataFrame(candidates)
    active_mask = df_results['Status'] == 'Active'
    
    if active_mask.sum() > 0:
        df_results.loc[active_mask, 'Momentum_Rank'] = df_results.loc[active_mask, 'Momentum_Raw'].rank(pct=True)
        df_results.loc[active_mask, 'Safety_Rank'] = 1 - df_results.loc[active_mask, 'Downside_Risk_Raw'].rank(pct=True)
    else:
        df_results['Momentum_Rank'] = 0
        df_results['Safety_Rank'] = 0

    df_results['Oracle_Score'] = df_results.apply(lambda r: calculate_composite_score(r, regime['status']), axis=1)
    
    # 4. SAVE LOG
    today = datetime.now().strftime('%Y-%m-%d')
    log_data = []
    for _, row in df_results.iterrows():
        s_badge = "🛡️ HIGH" if row.get('Safety_Rank', 0) > 0.6 else "⚠️ MED"
        m_badge = "🚀 FAST" if row.get('Momentum_Rank', 0) > 0.6 else "🐢 SLOW"
        
        log_data.append({
            'Date': today,
            'Ticker': row['symbol'],
            'Entry_Price': round(row['Close'], 2),
            'Oracle_Score': round(row['Oracle_Score'], 1),
            'Projected_Upside': round(row['Upside_Pct'] * 100, 1),
            'Fair_Value': round(row['Fair_Value'], 2),
            'F_Score': row['F_Score'],
            'Status': row['Status'],
            'Safety_Badge': s_badge,
            'Momentum_Badge': m_badge,
            'Regime_Active': regime['status']
        })
        
    final_df = pd.DataFrame(log_data)
    final_df.to_csv(LOG_FILE, index=False)
    print(f"\n\n🏆 AUDIT COMPLETE. {len(final_df)} assets logged to {LOG_FILE}.", flush=True)

if __name__ == "__main__":
    make_predictions()