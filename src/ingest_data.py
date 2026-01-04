import yfinance as yf
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Database Config
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

# FULL UNIVERSE
TICKERS = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BEL.NS", "BPCL.NS",
    "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS",
    "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
    "ITC.NS", "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS",
    "LT.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS",
    "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS",
    "SUNPHARMA.NS", "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS", "^NSEI"
]

def ingest_historical_data():
    try:
        print("🔌 Connecting to the Vault...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print(f"📥 Downloading data for {len(TICKERS)} tickers (One by One)...")

        for ticker in TICKERS:
            try:
                # Download INDIVIDUAL ticker (Safe Mode)
                # auto_adjust=True gives us adjusted Close automatically
                df = yf.download(ticker, period="1y", interval="1h", progress=False, auto_adjust=True)
                
                if df.empty:
                    print(f"   ⚠️ Skipping {ticker} (No data found)")
                    continue

                # 1. Reset Index (Date becomes a column)
                df.reset_index(inplace=True)
                
                # 2. Rename columns safely
                # We map whatever Yahoo gives us to our standard names
                # Note: 'Datetime' is usually the name for hourly data
                df.rename(columns={
                    "Datetime": "time", 
                    "Date": "time", 
                    "Open": "open", 
                    "High": "high", 
                    "Low": "low", 
                    "Close": "close", 
                    "Volume": "volume"
                }, inplace=True)
                
                # Force rename first column if renaming didn't work (fallback)
                if 'time' not in df.columns:
                     df.rename(columns={df.columns[0]: "time"}, inplace=True)

                # 3. Timezone Cleanup
                if df['time'].dt.tz is None:
                    df['time'] = df['time'].dt.tz_localize('UTC')
                else:
                    df['time'] = df['time'].dt.tz_convert('UTC')
                
                # 4. Add Metadata
                df['symbol'] = ticker
                df['is_adjusted'] = True
                
                # 5. Insert
                # Filter only the columns we need to prevent errors
                final_df = df[['time', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'is_adjusted']].dropna()
                
                rows = final_df.values.tolist()
                
                query = """
                    INSERT INTO market_data (time, symbol, open, high, low, close, volume, is_adjusted)
                    VALUES %s
                    ON CONFLICT DO NOTHING;
                """
                execute_values(cur, query, rows)
                print(f"   ✅ {ticker}: Inserted {len(rows)} candles.")

            except Exception as e:
                print(f"   ❌ Error {ticker}: {e}")

        conn.commit()
        conn.close()
        print("\n🚀 FULL UNIVERSE INGESTED.")

    except Exception as e:
        print(f"❌ Critical Connection Error: {e}")

if __name__ == "__main__":
    ingest_historical_data()