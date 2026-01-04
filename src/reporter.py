from fpdf import FPDF
import pandas as pd
import os
from datetime import datetime

def create_pdf():
    """Generates the Daily Institutional Tear Sheet (Emoji-Safe)"""
    LOG_FILE = "nifty_oracle_log.csv"
    if not os.path.exists(LOG_FILE):
        print("⚠️ No log file found to generate PDF.")
        return

    df = pd.read_csv(LOG_FILE)
    latest_date = df['Date'].max()
    today_df = df[df['Date'] == latest_date].copy()

    # --- THE FIX: STRIP EMOJIS FOR PDF STABILITY ---
    # FPDF latin-1 cannot handle 🛡️ or 🚀. We convert them to plain text.
    if 'Safety_Badge' in today_df.columns:
        today_df['Safety_Badge'] = today_df['Safety_Badge'].str.replace('🛡️ ', '').str.replace('⚠️ ', '').str.replace('💣 ', '')
    if 'Momentum_Badge' in today_df.columns:
        today_df['Momentum_Badge'] = today_df['Momentum_Badge'].str.replace('🚀 ', '').str.replace('🐢 ', '')

    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Nifty Oracle Institutional Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Generated on: {latest_date}", ln=True, align='C')
    pdf.ln(10)

    # Table Header
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(35, 10, "Ticker", 1)
    pdf.cell(35, 10, "Oracle Score", 1)
    pdf.cell(35, 10, "Upside %", 1)
    pdf.cell(35, 10, "Safety", 1)
    pdf.cell(35, 10, "Momentum", 1)
    pdf.ln()

    # Table Content
    pdf.set_font("Arial", size=10)
    for _, row in today_df.iterrows():
        pdf.cell(35, 10, str(row['Ticker']), 1)
        pdf.cell(35, 10, str(row['Oracle_Score']), 1)
        pdf.cell(35, 10, f"{row['Projected_Upside']}%", 1)
        pdf.cell(35, 10, str(row['Safety_Badge']), 1)
        pdf.cell(35, 10, str(row['Momentum_Badge']), 1)
        pdf.ln()

    if not os.path.exists('reports'):
        os.makedirs('reports')
        
    report_path = f"reports/TearSheet_{latest_date}.pdf"
    
    # The clean output won't trigger the UnicodeEncodeError
    pdf.output(report_path)
    print(f"📄 Emoji-Safe PDF Report Generated: {report_path}")

if __name__ == "__main__":
    create_pdf()