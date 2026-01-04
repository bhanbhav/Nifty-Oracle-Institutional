import pandas as pd
import numpy as np
import psycopg2
import warnings
from sector_map import SECTOR_MAP 

warnings.filterwarnings("ignore")

DB_CONFIG = { "dbname": "postgres", "user": "postgres", "password": "password", "host": "localhost", "port": "5432" }

def fetch_all_data():
    conn = psycopg2.connect(**DB_CONFIG)
    query = "SELECT time, symbol, close, volume FROM market_data ORDER BY time ASC;"
    df = pd.read_sql(query, conn)
    conn.close()
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    return df

def calculate_rsi(series, period=14):
    delta = series.diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_width(series, window=20, num_std=2):
    rolling_mean = series.rolling(window=window).mean()
    rolling_std = series.rolling(window=window).std()
    upper = rolling_mean + (rolling_std * num_std)
    lower = rolling_mean - (rolling_std * num_std)
    return (upper - lower) / rolling_mean

def load_fundamental_scores():
    """Loads the Piotroski F-Scores from CSV"""
    try:
        f_df = pd.read_csv('src/fundamental_data.csv')
        # Create a dictionary map: {'RELIANCE.NS': 4, 'NTPC.NS': 8 ...}
        return dict(zip(f_df['symbol'], f_df['F_Score']))
    except FileNotFoundError:
        print("⚠️ Warning: fundamental_data.csv not found. Running without CA scores.")
        return {}

def build_master_dataset():
    print("🌍 Loading Universe for Sector & Fundamental Analysis...")
    raw_df = fetch_all_data()
    
    # Load Fundamentals
    f_scores = load_fundamental_scores()
    
    close_pivot = raw_df.pivot(columns='symbol', values='close')
    volume_pivot = raw_df.pivot(columns='symbol', values='volume')
    returns_df = close_pivot.pct_change()
    
    # --- SECTOR INDICES ---
    print("🏭 Building Synthetic Sector Indices...")
    sector_returns = pd.DataFrame(index=returns_df.index)
    unique_sectors = set(SECTOR_MAP.values())
    
    for sector in unique_sectors:
        stocks_in_sector = [s for s in SECTOR_MAP if SECTOR_MAP[s] == sector]
        valid_stocks = [s for s in stocks_in_sector if s in returns_df.columns]
        if valid_stocks:
            sector_returns[sector] = returns_df[valid_stocks].mean(axis=1)
            
    # --- INDIVIDUAL PROCESSING ---
    final_dfs = []
    nifty_ret = returns_df['^NSEI'] if '^NSEI' in returns_df.columns else returns_df.mean(axis=1)

    print("⚙️  Calculating Technicals + Fundamentals...")
    for symbol in returns_df.columns:
        if symbol == '^NSEI': continue 
        
        sector = SECTOR_MAP.get(symbol, "OTHER")
        
        df = pd.DataFrame(index=returns_df.index)
        df['close'] = close_pivot[symbol]
        df['volume'] = volume_pivot[symbol]
        df['stock_return'] = returns_df[symbol]
        
        # Technicals
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        df['RSI'] = calculate_rsi(df['close'])
        df['BB_Width'] = calculate_bollinger_width(df['close'])
        df['Volume_Ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Relative Strength
        df['Market_Rel_Strength'] = df['stock_return'] - nifty_ret
        if sector in sector_returns.columns:
            df['Sector_Rel_Strength'] = df['stock_return'] - sector_returns[sector]
        else:
            df['Sector_Rel_Strength'] = 0.0
            
        # --- NEW: FUNDAMENTAL F-SCORE ---
        # Map the score. If missing (like ^IXIC), default to 0.
        score = f_scores.get(symbol, 0)
        df['F_Score'] = score
            
        # Target
        df['target'] = (df['Market_Rel_Strength'].shift(-1) > 0).astype(int)
        
        # We add 'F_Score' to the feature list
        features = ['log_return', 'RSI', 'BB_Width', 'Volume_Ratio', 'Market_Rel_Strength', 'Sector_Rel_Strength', 'F_Score', 'target']
        df = df[features].dropna()
        final_dfs.append(df)
        
    return pd.concat(final_dfs)