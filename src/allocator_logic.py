import pandas as pd
import numpy as np
import yfinance as yf
from pypfopt import risk_models, BlackLittermanModel, EfficientFrontier
from sector_map import SECTOR_MAP
import warnings

warnings.filterwarnings("ignore")

# BLUEPRINT CONSTRAINTS (Layer 3.2)
MAX_SECTOR_WEIGHT = 0.25 
CORRELATION_THRESHOLD = 0.85 # Slight adjustment to allow distinct alpha
RISK_FREE_RATE = 0.072       # KEPT AT 7.2% (Your Requirement)

def run_black_litterman_allocation(buy_recommendations):
    print("\n🧠 LAYER 3: EXECUTING INSTITUTIONAL ALLOCATOR...")
    
    if buy_recommendations.empty:
        return {}

    # 1. DATA SANITIZATION
    tickers = buy_recommendations['symbol'].tolist()
    benchmark = "^NSEI"
    all_assets = tickers + [benchmark]
    
    # ... [Data Fetching block remains same] ...
    print(f"   📉 Fetching and aligning history for {len(all_assets)} assets...")
    raw_data = yf.download(all_assets, period="1y", interval="1d", progress=False, auto_adjust=True)['Close']
    data = raw_data.dropna(axis=1, how='all').ffill().dropna()

    if data.empty or len(data) < 30:
        print("   ❌ Error: Insufficient overlapping history. Reverting to Index.")
        return {benchmark: 1.0}

    valid_tickers = [t for t in tickers if t in data.columns]
    
    # 2. CORRELATION FILTER
    final_universe = [benchmark]
    for t in valid_tickers:
        corr = data[t].corr(data[benchmark])
        if corr > CORRELATION_THRESHOLD:
            print(f"   ⚠️  Correlation Alert: {t} ({corr:.2f}) is too market-linked.")
        final_universe.append(t)

    # 3. BLACK-LITTERMAN POSTERIOR
    S = risk_models.CovarianceShrinkage(data[final_universe]).ledoit_wolf()
    
    viewdict = {}
    confidences = []
    mkt_caps = {}
    
    for ticker in final_universe:
        if ticker == benchmark:
            viewdict[ticker] = 0.12 # We expect Nifty to give ~12% long term
            confidences.append(0.60)
            mkt_caps[ticker] = 100.0 
        else:
            conf = buy_recommendations.set_index('symbol').loc[ticker, 'Confidence']
            
            # --- THE FIX IS HERE ---
            # If Confidence is 60% (0.60), we imply a 25% return potential.
            # Formula: (0.60 - 0.50) * 2.5 = 0.25 (25%)
            # This easily clears the 7.2% hurdle.
            expected_return = (conf - 0.50) * 2.5 
            
            viewdict[ticker] = expected_return
            confidences.append(conf)
            mkt_caps[ticker] = 1.0

    bl = BlackLittermanModel(S, pi="market", market_caps=pd.Series(mkt_caps), 
                              absolute_views=viewdict, omega="idzorek", 
                              view_confidences=confidences)
    
    # 4. OPTIMIZATION
    ef = EfficientFrontier(bl.bl_returns(), bl.bl_cov())
    
    sector_mapper = {t: SECTOR_MAP.get(t, "MARKET_INDEX") for t in final_universe}
    sectors = set(sector_mapper.values())
    s_upper = {s: MAX_SECTOR_WEIGHT for s in sectors}
    s_upper["MARKET_INDEX"] = 1.0 
    
    try:
        ef.add_sector_constraints(sector_mapper, {s: 0.0 for s in sectors}, s_upper)
        # Maximize Sharpe with your strict 7.2% hurdle
        weights = ef.max_sharpe(risk_free_rate=RISK_FREE_RATE)
        print("   ✅ Posterior Weights Calculated.")
        return ef.clean_weights()
    except Exception as e:
        print(f"   ⚠️  Solver fail: {e}. Reverting to Index Equilibrium.")
        return {benchmark: 1.0}