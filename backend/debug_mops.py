import requests
import pandas as pd
from io import StringIO
import urllib3

urllib3.disable_warnings()

def debug_mops():
    url = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_114_12_0.html"
    print(f"Fetching {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        r.encoding = 'big5'
        print(f"Status: {r.status_code}")
        
        dfs = pd.read_html(StringIO(r.text))
        print(f"Found {len(dfs)} tables.")
        
        # Inspect Table 4 (likely a data table)
        if len(dfs) > 4:
            df = dfs[4]
            print("\n----- INSPECTING TABLE 4 -----")
            print("Columns:", df.columns.tolist())
            print("Row 0:", df.iloc[0].tolist())
            print("Row 1:", df.iloc[1].tolist())
            
            # Check for '公司代號' in any column
            for col in df.columns:
                print(f"Col: {col} | Type: {type(col)}")
                
        # Also check Table 2 just in case
        if len(dfs) > 2:
            df = dfs[2]
            print("\n----- INSPECTING TABLE 2 -----")
            print("Row 0:", df.iloc[0].tolist())

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_mops()
