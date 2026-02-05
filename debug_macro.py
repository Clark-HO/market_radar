import requests
import pandas as pd
from io import StringIO
import urllib3

urllib3.disable_warnings()

def debug_taifex():
    url = "https://www.taifex.com.tw/cht/3/futContractsDate"
    print(f"Fetching {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=15)
        r.encoding = 'utf-8'
        print(f"Status: {r.status_code}")
        
        dfs = pd.read_html(StringIO(r.text))
        print(f"Found {len(dfs)} tables.")
        
        for i, df in enumerate(dfs):
            print(f"\n--- Table {i} ---")
            print("Columns:", df.columns.tolist())
            print(df.head())
            
            # Simple check for target keywords
            txt = df.to_string()
            if "臺股期貨" in txt and "外資" in txt:
                print(f"✅ Potential Target Table Found: Index {i}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_taifex()
