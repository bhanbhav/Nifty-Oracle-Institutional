import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import sys
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# --- PATH FIX ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from sector_map import SECTOR_MAP
except ImportError:
    SECTOR_MAP = {}

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Nifty Oracle Command Center",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS ---
st.markdown("""
    <style>
        .ticker-wrap { width: 100%; overflow: hidden; background-color: #0E1117; color: #00FF7F; font-family: 'Consolas', monospace; padding: 8px 0; border-bottom: 1px solid #303030; white-space: nowrap; }
        .ticker { display: inline-block; animation: ticker 45s linear infinite; }
        @keyframes ticker { 0% { transform: translate(0, 0); } 100% { transform: translate(-100%, 0); } }
        .ticker-item { display: inline-block; padding: 0 2rem; font-size: 14px; }
        div[data-testid="stMetricValue"] { font-family: 'Arial', sans-serif; font-size: 24px; }
    </style>
""", unsafe_allow_html=True)

# --- CONSTANTS ---
LOG_FILE = "nifty_oracle_log.csv"
PORTFOLIO_FILE = "portfolio.json"

# --- BOND ETF DATABASE ---
BOND_ETFS = {
    "LIQUIDBEES.NS": {"Type": "Cash Equiv", "Risk": 1, "Name": "Nippon Liquid BeES (Safe)"},
    "LICNETFGSC.NS": {"Type": "G-Sec 10Y", "Risk": 3, "Name": "LIC G-Sec 10Y ETF (Yield)"},
    "GILT5YBEES.NS": {"Type": "G-Sec 5Y", "Risk": 2, "Name": "Nippon 5Y Gilt (Balanced)"},
    "SETF10GILT.NS": {"Type": "G-Sec 10Y", "Risk": 3, "Name": "SBI 10Y Gilt (Aggressive)"},
    "GOLDBEES.NS": {"Type": "Commodity", "Risk": 4, "Name": "Nippon Gold BeES (Hedge)"}
}

def load_data():
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        numeric_cols = ['Oracle_Score', 'Projected_Upside', 'Momentum_Raw', 'F_Score', 'Fair_Value', 'Entry_Price']
        for col in numeric_cols:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        def get_sector(ticker):
            clean = str(ticker).replace('.NS', '')
            if ticker in SECTOR_MAP: return SECTOR_MAP[ticker]
            if clean in SECTOR_MAP: return SECTOR_MAP[clean]
            return "Others"
        
        df['Sector'] = df['Ticker'].apply(get_sector)
        return df
    return None

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f: return json.load(f)
    return None

# --- CHART HELPERS ---
def get_candlestick_chart(ticker, name):
    try:
        if not ticker: return None
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#00FF7F', decreasing_line_color='#FF4B4B')])
        fig.update_layout(title=name, template="plotly_dark", height=300, margin=dict(l=0, r=0, t=40, b=0), xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig
    except: return None

def plot_mini_line(ticker):
    try:
        df = yf.download(ticker, period="3mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#00FF7F', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 127, 0.1)'))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=80, template="plotly_dark", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, showticklabels=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig
    except: return None

def get_bond_analysis(risk_tolerance):
    results = []
    target_risk = 1
    if risk_tolerance > 33: target_risk = 2
    if risk_tolerance > 66: target_risk = 3
    
    for ticker, info in BOND_ETFS.items():
        if info['Risk'] == target_risk or (target_risk == 3 and info['Risk'] == 4):
            try:
                df = yf.download(ticker, period="1y", progress=False)
                if df.empty: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                curr = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[0])
                ytd_ret = ((curr - prev) / prev) * 100
                vol = df['Close'].pct_change().std() * np.sqrt(252) * 100
                
                results.append({
                    "Ticker": ticker,
                    "Asset Name": info['Name'],
                    "Type": info['Type'],
                    "Price": curr,
                    "1Y Return": ytd_ret,
                    "Risk (Vol)": vol
                })
            except: continue
    return pd.DataFrame(results)

# --- MAIN APP ---
df = load_data()
portfolio = load_portfolio()

# CRASH PROTECTION
if df is not None:
    for col in ['F_Score', 'Fair_Value', 'Sector', 'Projected_Upside', 'Oracle_Score']:
        if col not in df.columns: df[col] = 0 if col != 'Sector' else "Others"

# 1. TICKER TAPE
if df is not None:
    latest_df = df[df['Date'] == df['Date'].max()].copy()
    top_picks = latest_df.sort_values(by='Oracle_Score', ascending=False).head(20)
    ticker_text = "   |   ".join([f"{r['Ticker'].replace('.NS','')}: {r['Entry_Price']:,.0f} ({'^' if r['Projected_Upside']>0 else 'v'}{r['Projected_Upside']}%)" for _, r in top_picks.iterrows()])
    st.markdown(f'<div class="ticker-wrap"><div class="ticker"><span class="ticker-item">{ticker_text}</span></div></div>', unsafe_allow_html=True)

st.title("Nifty Oracle Command Center")

# 2. GLOBAL PULSE
col1, col2, col3 = st.columns(3)
with col1:
    fig = get_candlestick_chart("^NSEI", "Nifty 50")
    if fig: st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = get_candlestick_chart("^BSESN", "Sensex") 
    if fig: st.plotly_chart(fig, use_container_width=True)
with col3:
    fig = get_candlestick_chart("^IXIC", "Nasdaq")
    if fig: st.plotly_chart(fig, use_container_width=True)

st.divider()

# 3. MASTER NAVIGATION
tabs = st.tabs(["MY PORTFOLIO", "SECTOR INTEL", "MARKET UNIVERSE", "FIXED INCOME", "QUANT LAB", "DEEP DIVE"])

# === TAB 1: PORTFOLIO (UPDATED WITH TOTAL P&L) ===
with tabs[0]:
    if portfolio and portfolio.get("holdings"):
        # Calculate Aggregates
        total_invested = sum(d['qty'] * d['avg_price'] for d in portfolio['holdings'].values())
        current_equity = portfolio.get('equity_value', 0)
        
        total_pnl = current_equity - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Display 4 Metrics Now
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Net Worth", f"INR {portfolio.get('total_value',0):,.2f}")
        c2.metric("Overall P&L", f"{total_pnl_pct:.2f}%", f"INR {total_pnl:,.2f}")
        c3.metric("Equity", f"INR {current_equity:,.2f}")
        c4.metric("Cash", f"INR {portfolio.get('cash',0):,.2f}")
        
        st.divider()
        st.markdown("#### Holdings Performance")
        
        for ticker, data in portfolio["holdings"].items():
            qty = data["qty"]
            avg_cost = data["avg_price"]
            with st.container():
                cols = st.columns([1.5, 1.5, 4])
                with cols[0]:
                    st.markdown(f"**{ticker}**")
                    st.caption(f"Qty: {qty} | Avg: INR {avg_cost:,.2f}")
                with cols[1]:
                    try:
                        df_tick = yf.download(ticker, period="1d", progress=False)
                        curr_price = float(df_tick['Close'].values[-1]) if not df_tick.empty else avg_cost
                        pnl_val = (curr_price - avg_cost) * qty
                        pnl_pct = (pnl_val / (avg_cost * qty)) * 100
                        st.metric("P&L", f"{pnl_pct:.2f}%", f"INR {pnl_val:,.2f}")
                    except: st.metric("P&L", "0.00%", "INR 0.00")
                with cols[2]:
                    chart = plot_mini_line(ticker)
                    if chart: st.plotly_chart(chart, use_container_width=True, config={'displayModeBar': False})
                st.markdown("---")
    else: st.info("Portfolio Empty. Start trading.")

# === TAB 2: SECTOR INTEL ===
with tabs[1]:
    st.subheader("Industry Heatmap")
    if df is not None:
        sector_stats = latest_df.groupby('Sector')[['Oracle_Score', 'Projected_Upside']].mean().reset_index()
        sector_stats = sector_stats[sector_stats['Sector'] != 'Others'].sort_values(by='Oracle_Score', ascending=False)
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_bar = px.bar(sector_stats, x='Sector', y='Oracle_Score', color='Oracle_Score', color_continuous_scale='Viridis')
            fig_bar.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            st.dataframe(sector_stats, column_config={"Oracle_Score": st.column_config.NumberColumn("Score", format="%.1f"), "Projected_Upside": st.column_config.NumberColumn("Upside", format="%.1f%%")}, hide_index=True, use_container_width=True)

# === TAB 3: MARKET UNIVERSE ===
with tabs[2]:
    st.subheader("Full Market Scan")
    if df is not None:
        search = st.text_input("Search Ticker:", "")
        display_df = latest_df.copy()
        if search: display_df = display_df[display_df['Ticker'].str.contains(search.upper())]
        st.dataframe(display_df[['Ticker', 'Sector', 'Entry_Price', 'Oracle_Score', 'Projected_Upside', 'F_Score']], column_config={"Oracle_Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"), "Projected_Upside": st.column_config.NumberColumn("Upside", format="%.1f%%"), "Entry_Price": st.column_config.NumberColumn("Price", format="INR %.2f")}, hide_index=True, use_container_width=True, height=600)

# === TAB 4: FIXED INCOME ===
with tabs[3]:
    st.subheader("Fixed Income Allocator")
    st.caption("Lower volatility alternatives to 3 Patti (and Equities).")
    
    risk_level = st.select_slider("Select Risk Profile", options=["Safety (Liquid)", "Balanced (Gilt 5Y)", "Growth (Gold/10Y)"])
    risk_map = {"Safety (Liquid)": 10, "Balanced (Gilt 5Y)": 50, "Growth (Gold/10Y)": 90}
    
    st.divider()
    bond_df = get_bond_analysis(risk_map[risk_level])
    
    if not bond_df.empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            top_asset = bond_df.iloc[0]['Ticker']
            top_name = bond_df.iloc[0]['Asset Name']
            fig_bond = get_candlestick_chart(top_asset, f"Trend: {top_name}")
            if fig_bond: st.plotly_chart(fig_bond, use_container_width=True)
        with c2:
            st.dataframe(bond_df, column_config={"1Y Return": st.column_config.NumberColumn("Yield (1Y)", format="%.2f%%"), "Risk (Vol)": st.column_config.NumberColumn("Risk", format="%.2f%%"), "Price": st.column_config.NumberColumn("NAV", format="INR %.2f")}, hide_index=True, use_container_width=True)
            if risk_map[risk_level] < 33: st.success("✅ **Liquid BeES:** Pays ~6-7%. Basically a savings account on the stock market. Zero lock-in.")
            elif risk_map[risk_level] < 66: st.info("⚖️ **Gilt 5Y:** Government Bonds. Good balance of safety and yield, but reacts to RBI rate changes.")
            else: st.warning("🚀 **Gold/10Y:** High volatility. Gold acts as a hedge against inflation. 10Y Bonds rally when rates fall.")

# === TAB 5: QUANT LAB ===
with tabs[4]:
    st.subheader("Efficient Frontier")
    if df is not None:
        fig_scatter = px.scatter(latest_df, x="Oracle_Score", y="Projected_Upside", color="Sector", size="F_Score", hover_data=["Ticker", "Entry_Price"])
        fig_scatter.add_hline(y=0, line_dash="dash", line_color="white")
        fig_scatter.update_layout(template="plotly_dark", height=600, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_scatter, use_container_width=True)

# === TAB 6: DEEP DIVE ===
with tabs[5]:
    if df is not None:
        selected = st.selectbox("Select Asset:", df['Ticker'].unique())
        if selected:
            row = latest_df[latest_df['Ticker'] == selected].iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Score", f"{row['Oracle_Score']}")
            c2.metric("Fair Value", f"INR {row['Fair_Value']}")
            c3.metric("F-Score", f"{row['F_Score']}")
            c4.metric("Upside", f"{row['Projected_Upside']}%")
            fig = get_candlestick_chart(selected, f"{selected}")
            if fig: st.plotly_chart(fig, use_container_width=True)