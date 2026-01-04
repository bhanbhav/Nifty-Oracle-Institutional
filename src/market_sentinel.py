import yfinance as yf
import time
import smtplib
from datetime import datetime
from sentiment_engine import NewsSentimentEngine

# --- CONFIGURATION ---
CHECK_INTERVAL = 300  # Check every 5 minutes
CRASH_THRESHOLD = -0.025  # Panic if Market drops 2.5% intraday
SENTIMENT_PANIC = -0.40   # Panic if News Sentiment hits -0.40 (Disaster)
MY_EMAIL = "your_email@gmail.com" # Placeholder
EMAIL_PASSWORD = "your_app_password" # Placeholder

def send_emergency_alert(subject, body):
    """ Sends an email alert to your phone (Liquidate Signal) """
    print(f"\n🚨 EMERGENCY ALERT: {subject}")
    print(f"   {body}")
    # (Uncomment this section to actually send emails once you have App Password)
    # with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    #     server.login(MY_EMAIL, EMAIL_PASSWORD)
    #     message = f"Subject: {subject}\n\n{body}"
    #     server.sendmail(MY_EMAIL, MY_EMAIL, message)

def check_market_health():
    print(f"   👀 Sentinel Scanning at {datetime.now().strftime('%H:%M:%S')}...", end="\r")
    
    try:
        # 1. CHECK NIFTY CRASH (Price Shock)
        # We use ^NSEI (Nifty 50) as the proxy for the whole market
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="1d", interval="5m")
        
        if not hist.empty:
            open_price = hist['Open'].iloc[0]
            current_price = hist['Close'].iloc[-1]
            
            drop_pct = (current_price - open_price) / open_price
            
            if drop_pct < CRASH_THRESHOLD:
                send_emergency_alert(
                    "MARKET CRASH DETECTED", 
                    f"Nifty has crashed {drop_pct*100:.2f}% intraday!\n"
                    f"Open: {open_price}, Current: {current_price}\n"
                    "RECOMMENDATION: LIQUIDATE ALL POSITIONS IMMEDIATELY."
                )
                return "CRASH"

        # 2. CHECK NEWS SHOCK (Sentiment Shock)
        sent_engine = NewsSentimentEngine()
        # Check Nifty Sentiment (Macro View)
        score, count, headline = sent_engine.get_sentiment("^NSEI")
        
        if score < SENTIMENT_PANIC:
            send_emergency_alert(
                "NEWS DISASTER DETECTED",
                f"Global Sentiment has collapsed to {score}.\n"
                f"Headline: {headline}\n"
                "RECOMMENDATION: HALT TRADING / HEDGE POSITIONS."
            )
            return "PANIC"
            
        return "SAFE"

    except Exception as e:
        print(f"   ⚠️ Sentinel Error: {e}")
        return "ERROR"

def run_sentinel():
    print("🛡️ NIFTY SENTINEL IS ACTIVE (24/7 MONITORING)...")
    print("   (Press Ctrl+C to stop)")
    
    while True:
        status = check_market_health()
        
        # If disaster found, we can add logic to auto-close trades here later (Layer 5)
        if status in ["CRASH", "PANIC"]:
            # In a real bot, we would trigger 'broker.sell_all()' here
            time.sleep(3600) # Sleep 1 hour so we don't spam alerts
            
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_sentinel()