import pandas as pd
import requests
import io
import os

def generate_nifty500_map():
    print("🌍 Connecting to NSE Indices Server...")
    
    # Official NSE URL for Nifty 500 Constituents
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            csv_content = response.content.decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Filter for Equity series only
            if 'Series' in df.columns:
                df = df[df['Series'] == 'EQ']
            
            print(f"✅ Downloaded {len(df)} active constituents from NSE.")
            
            # Start writing the Python file content
            py_content = "# NIFTY 500 CONSTITUENTS (AUTO-GENERATED)\n"
            py_content += f"# Updated: {pd.Timestamp.now()}\n\n"
            py_content += "SECTOR_MAP = {\n"
            
            count = 0
            for index, row in df.iterrows():
                symbol = row['Symbol']
                sector = row['Industry']
                
                # Yahoo Finance format requires .NS suffix
                ticker = f"{symbol}.NS"
                
                # Cleaning Sector Names for easier grouping
                sec_upper = str(sector).upper()
                if "FINANCIAL" in sec_upper or "BANK" in sec_upper: final_sector = "Financials"
                elif "AUTO" in sec_upper: final_sector = "Auto"
                elif "IT" in sec_upper or "INFORMATION" in sec_upper: final_sector = "Technology"
                elif "PHARMA" in sec_upper or "HEALTH" in sec_upper: final_sector = "Healthcare"
                elif "OIL" in sec_upper or "GAS" in sec_upper or "ENERGY" in sec_upper or "POWER" in sec_upper: final_sector = "Energy"
                elif "FMCG" in sec_upper or "CONSUMER" in sec_upper: final_sector = "Consumer"
                elif "CONSTRUCT" in sec_upper or "REALTY" in sec_upper: final_sector = "Construction"
                elif "METAL" in sec_upper or "MINING" in sec_upper: final_sector = "Materials"
                else: final_sector = sector.title() 
                
                py_content += f'    "{ticker}": "{final_sector}",\n'
                count += 1
            
            py_content += "}\n"
            
            # Overwrite the sector_map.py file
            with open("src/sector_map.py", "w") as f:
                f.write(py_content)
                
            print(f"🚀 Success! 'src/sector_map.py' has been updated with {count} stocks.")
            
        else:
            print(f"❌ Failed to download. Status Code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_nifty500_map()