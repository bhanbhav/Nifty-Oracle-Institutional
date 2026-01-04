import json
import os
import pandas as pd
from datetime import datetime

PORTFOLIO_FILE = "portfolio.json"
TRADE_LOG = "trade_history.csv"

class PortfolioManager:
    def __init__(self, initial_capital=100000.0):
        self.load_portfolio(initial_capital)

    def load_portfolio(self, initial_capital):
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {
                "cash": initial_capital,
                "holdings": {},  # { "TICKER": {"qty": 10, "avg_price": 500} }
                "equity_value": 0.0,
                "total_value": initial_capital
            }
            self.save_portfolio()

    def save_portfolio(self):
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(self.data, f, indent=4)

    def update_valuations(self, current_prices):
        """Updates the current market value of holdings."""
        equity_val = 0.0
        for ticker, info in self.data["holdings"].items():
            current_price = current_prices.get(ticker, info['avg_price'])
            equity_val += info['qty'] * current_price
        
        self.data["equity_value"] = round(equity_val, 2)
        self.data["total_value"] = round(self.data["cash"] + equity_val, 2)
        self.save_portfolio()

    def execute_trade(self, action, ticker, price, quantity, transaction_cost):
        """
        Executes a trade in the Shadow Ledger.
        action: 'BUY' or 'SELL'
        price: The execution price (including slippage in logic, but raw here)
        transaction_cost: STT + Taxes calculated by Friction Engine
        """
        total_cost = (price * quantity)
        
        if action == "BUY":
            effective_cost = total_cost + transaction_cost
            if self.data["cash"] >= effective_cost:
                self.data["cash"] -= effective_cost
                
                # Update Holdings
                if ticker in self.data["holdings"]:
                    old_qty = self.data["holdings"][ticker]["qty"]
                    old_cost = old_qty * self.data["holdings"][ticker]["avg_price"]
                    new_cost = old_cost + total_cost
                    new_qty = old_qty + quantity
                    self.data["holdings"][ticker] = {"qty": new_qty, "avg_price": new_cost / new_qty}
                else:
                    self.data["holdings"][ticker] = {"qty": quantity, "avg_price": price}
                
                self._log_trade(ticker, "BUY", price, quantity, transaction_cost)
                return True
            else:
                print(f"❌ INSUFFICIENT FUNDS: Needed {effective_cost:.2f}, Have {self.data['cash']:.2f}")
                return False

        elif action == "SELL":
            if ticker in self.data["holdings"]:
                # STT is deducted from sale proceeds
                effective_revenue = total_cost - transaction_cost
                self.data["cash"] += effective_revenue
                
                # Update Holdings
                self.data["holdings"][ticker]["qty"] -= quantity
                if self.data["holdings"][ticker]["qty"] <= 0:
                    del self.data["holdings"][ticker]
                
                self._log_trade(ticker, "SELL", price, quantity, transaction_cost)
                return True
            return False

    def _log_trade(self, ticker, action, price, qty, costs):
        record = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Ticker": ticker,
            "Action": action,
            "Price": price,
            "Qty": qty,
            "Costs_Tax": costs
        }
        df = pd.DataFrame([record])
        if not os.path.exists(TRADE_LOG):
            df.to_csv(TRADE_LOG, index=False)
        else:
            df.to_csv(TRADE_LOG, mode='a', header=False, index=False)

    def get_portfolio_state(self):
        return self.data