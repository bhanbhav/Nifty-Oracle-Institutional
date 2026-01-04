import yfinance as yf
import pandas as pd
import numpy as np

def get_intrinsic_value(ticker):
    """
    Calculates Intrinsic Value using DCF.
    SMART FIX: Auto-detects Banks/NBFCs and switches to 'Earnings Model' 
    instead of 'Cash Flow Model' to avoid false negatives.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # 1. GET METADATA (Sector Check)
        info = stock.info
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        
        # 🏦 BANK CHECK: If it's a financial stock, DCF is useless.
        is_financial = "Financial" in sector or "Bank" in industry or "Credit" in industry
        
        # 2. GET FINANCIALS
        financials = stock.financials
        cashflow = stock.cashflow
        
        if financials.empty or cashflow.empty:
            return None

        # 3. SELECT THE RIGHT METRIC (The Fix)
        metric_used = ""
        free_cash_flow = 0
        
        if is_financial:
            # BANKS: Use Net Income (Earnings), not Cash Flow
            # Banks don't have 'Capex' in the traditional sense.
            free_cash_flow = financials.loc['Net Income'].iloc[0]
            metric_used = "Net Income (Financial Stock)"
            # print(f"   ℹ️  [Valuation] {ticker}: Detected Financial/Bank. Using Net Income.")
            
        else:
            # NON-BANKS: Try Free Cash Flow (OCF - Capex)
            try:
                ocf = cashflow.loc['Operating Cash Flow'].iloc[0]
                # Capex is negative in statements, so we add it (or subtract abs value)
                capex = cashflow.loc['Capital Expenditure'].iloc[0] 
                
                # Standard FCF
                free_cash_flow = ocf + capex 
                
                # FALLBACK: If FCF is negative (Heavy Capex), switch to Net Income
                if free_cash_flow < 0:
                    net_income = financials.loc['Net Income'].iloc[0]
                    if net_income > 0:
                        free_cash_flow = net_income
                        metric_used = "Net Income (Negative FCF Fallback)"
                        # print(f"   ℹ️  [Valuation] {ticker}: Heavy Capex (FCF < 0). Using Net Income.")
                    else:
                        # Company is actually losing money
                        return None
                else:
                    metric_used = "Free Cash Flow"
                    
            except KeyError:
                # If fields missing, fallback to Net Income
                if 'Net Income' in financials.index:
                    free_cash_flow = financials.loc['Net Income'].iloc[0]
                    metric_used = "Net Income (Data Missing)"
                else:
                    return None

        # 4. DCF CALCULATION (Simplified 2-Stage)
        # Assumptions
        growth_rate = 0.12  # Conservative 12% growth
        discount_rate = 0.10 # 10% cost of capital
        terminal_multiple = 15 # Exit PE/FCF multiple
        shares_outstanding = info.get('sharesOutstanding', 1)
        
        if shares_outstanding is None: return None

        # Project 5 years
        future_cash_flows = []
        for year in range(1, 6):
            fcf = free_cash_flow * ((1 + growth_rate) ** year)
            discounted_fcf = fcf / ((1 + discount_rate) ** year)
            future_cash_flows.append(discounted_fcf)
            
        # Terminal Value
        terminal_val = future_cash_flows[-1] * terminal_multiple
        discounted_tv = terminal_val / ((1 + discount_rate) ** 5)
        
        total_value = sum(future_cash_flows) + discounted_tv
        intrinsic_value = total_value / shares_outstanding
        
        return intrinsic_value

    except Exception as e:
        # print(f"   ⚠️ Valuation Failed for {ticker}: {e}")
        return None