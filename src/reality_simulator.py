import pandas as pd

class IndiaTradingCostModel:
    """
    Layer 4: The Reality Check.
    Calculates the 'Friction' of Indian markets (STT, GST, Stamp Duty).
    """
    def __init__(self, capital=100000):
        self.capital = capital
        
        # --- INDIAN GOVT & EXCHANGE FEE STRUCTURE (Equity Delivery) ---
        self.STT_RATE = 0.001          # 0.1% on Buy & Sell
        self.TXN_CHARGE_NSE = 0.0000325 # 0.00325% (NSE Transaction Fee)
        self.STAMP_DUTY = 0.00015      # 0.015% (Buy Only)
        self.SEBI_FEES = 0.000001      # ₹10 per crore
        self.GST_RATE = 0.18           # 18% on (Brokerage + Txn Charges)
        self.BROKERAGE = 0.0           # Assuming Discount Broker

    def calculate_trade_cost(self, price, quantity, transaction_type):
        """
        NEW: Calculates cost for a SINGLE real trade (for PortfolioManager).
        Returns: (Execution Price, Total Tax/Friction)
        """
        value = price * quantity
        
        # 1. Base Charges (Common to Buy & Sell)
        stt = value * self.STT_RATE
        txn_charge = value * self.TXN_CHARGE_NSE
        sebi_fees = value * self.SEBI_FEES
        gst = (txn_charge + self.BROKERAGE) * self.GST_RATE
        
        total_tax = stt + txn_charge + sebi_fees + gst
        
        # 2. Specific Charges
        if transaction_type == "BUY":
            # Stamp Duty is Buy Only
            stamp_duty = value * self.STAMP_DUTY
            total_tax += stamp_duty
            
            # Slippage Logic (Buy = Pay More)
            # We assume a standard 0.1% slippage for realism
            slippage = price * 0.001
            execution_price = price + slippage
            
        else: # SELL
            # No Stamp Duty on Sell
            # Slippage Logic (Sell = Receive Less)
            slippage = price * 0.001
            execution_price = price - slippage

        return execution_price, total_tax

    def calculate_friction(self, allocations):
        """
        OLD: The Detailed Report (Kept for Console Analysis).
        """
        print(f"\n💸 LAYER 4: REALITY CHECK (Capital: ₹{self.capital:,.2f})")
        print("-" * 75)
        print(f"{'SYMBOL':<15} | {'ALLOC':<10} | {'VALUE (₹)':<12} | {'COSTS (₹)':<10} | {'BREAKEVEN %':<12}")
        print("-" * 75)
        
        total_friction = 0
        
        for symbol, weight in allocations.items():
            if weight <= 0.001: continue
            
            # Position Value
            buy_value = self.capital * weight
            
            # --- BUY SIDE CHARGES ---
            stt_buy = buy_value * self.STT_RATE
            txn_buy = buy_value * self.TXN_CHARGE_NSE
            stamp_duty = buy_value * self.STAMP_DUTY
            sebi_buy = buy_value * self.SEBI_FEES
            gst_buy = (txn_buy + self.BROKERAGE) * self.GST_RATE
            
            total_buy_charges = stt_buy + txn_buy + stamp_duty + sebi_buy + gst_buy
            
            # --- SELL SIDE CHARGES (Estimated) ---
            stt_sell = buy_value * self.STT_RATE
            txn_sell = buy_value * self.TXN_CHARGE_NSE
            sebi_sell = buy_value * self.SEBI_FEES
            gst_sell = (txn_sell + self.BROKERAGE) * self.GST_RATE
            
            total_sell_charges = stt_sell + txn_sell + sebi_sell + gst_sell
            
            # Total Round-Trip Cost
            round_trip_cost = total_buy_charges + total_sell_charges
            total_friction += round_trip_cost
            
            # Breakeven Calculation
            breakeven_pct = (round_trip_cost / buy_value) * 100
            
            print(f"{symbol:<15} | {weight:.1%}     | ₹{buy_value:,.0f}      | ₹{round_trip_cost:<9.2f} | {breakeven_pct:.3f}%")

        print("-" * 75)
        print(f"🛑 TOTAL FRICTION LOSS: ₹{total_friction:,.2f} ({(total_friction/self.capital)*100:.2f}% of Portfolio)")
        print("   (This is the 'Alpha' you lose to the Govt automatically)")
        print("=" * 75)