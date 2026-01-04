import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score
from feature_engineering import build_master_dataset

def train_ai_model(return_model=False):
    """
    Trains the Institutional AI model.
    - return_model=True: Returns the trained model (for predict_daily.py).
    - return_model=False: Prints the Sniper Report AND Feature Importance (for manual testing).
    """
    if not return_model:
        print("⛽️ Injecting Sector-Aware + Fundamental Fuel...")
    
    # 1. Build the Dataset
    df = build_master_dataset()
    
    if df.empty:
        print("❌ Dataset empty. Check database or ingestion.")
        return None

    # 2. Split Data (Strict Time-Based Split)
    split_point = int(len(df) * 0.8)
    train_df = df.iloc[:split_point]
    test_df = df.iloc[split_point:]
    
    # THE COMPLETE FEATURE LIST
    features = [
        'log_return',           # Momentum
        'RSI',                  # Overbought/Oversold
        'BB_Width',             # Volatility Squeeze
        'Volume_Ratio',         # Liquidity Spikes
        'Market_Rel_Strength',  # Alpha vs Nifty 50
        'Sector_Rel_Strength',  # Alpha vs Sector
        'F_Score'               # Fundamental Health (Piotroski)
    ]
    target = 'target'
    
    X_train = train_df[features]
    y_train = train_df[target]
    X_test = test_df[features]
    y_test = test_df[target]
    
    if not return_model:
        print(f"🔥 Training XGBoost on {len(X_train)} rows...")
    
    # 3. Initialize Model (Max Depth = 3 to prevent Overconfidence)
    model = xgb.XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    )
    
    # 4. Train
    model.fit(X_train, y_train)
    
    # 5. Get Probabilities
    probs = model.predict_proba(X_test)[:, 1]
    
    test_df = test_df.copy()
    test_df['confidence'] = probs
    test_df['actual_target'] = y_test
    
    # --- REPORTING (Only runs if we are NOT asking for the model) ---
    if not return_model:
        # 6. Sniper Scope Calibration
        print("\n🎯 SNIPER SCOPE CALIBRATION")
        print(f"{'THRESHOLD':<10} | {'TRADES':<10} | {'WIN RATE':<10}")
        print("-" * 35)
        
        thresholds = [0.50, 0.51, 0.52, 0.53, 0.54, 0.55]
        
        for t in thresholds:
            sniper_trades = test_df[test_df['confidence'] > t]
            if len(sniper_trades) > 30:
                win_rate = accuracy_score(sniper_trades['actual_target'], [1]*len(sniper_trades))
                print(f"{t:.2f}       | {len(sniper_trades):<10} | {win_rate:.2%}")
            else:
                print(f"{t:.2f}       | {len(sniper_trades):<10} | (Not enough data)")

        # 7. Feature Importance Analysis (THIS WAS MISSING)
        print("\n🧠 Feature Importance (What is the AI looking at?):")
        importance = pd.DataFrame({
            'Feature': features,
            'Importance': model.feature_importances_
        }).sort_values(by='Importance', ascending=False)
        print(importance)

    # 8. Return the model object
    if return_model:
        return model

if __name__ == "__main__":
    train_ai_model()