import requests
import pandas as pd
from io import StringIO
import datetime

# Mock Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7'
}

# Target Date: 114/12 (Dec 2025) which is safe.
url = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_114_12_0.html"

print(f"Fetching {url}...")
try:
    r = requests.get(url, headers=HEADERS, verify=False, timeout=10)
    r.encoding = 'big5'
    dfs = pd.read_html(StringIO(r.text))
    
    found_2365 = False
    
    for i, df in enumerate(dfs):
        if df.shape[1] > 6:
            # Print headers for context
            print(f"--- Table {i} Headers (First 7) ---")
            print(df.columns.tolist()[:7])
            
            # Print row for 2365 if found
            for idx, row in df.iterrows():
                try:
                    code = str(row.iloc[0]).strip()
                    if code == '2365':
                        print("\n--- FOUND 2365 ---")
                        print(f"Index 5 (MoM Raw): '{row.iloc[5]}'")
                        print(f"Index 6 (YoY Raw): '{row.iloc[6]}'")
                        
                        # Test Conversion
                        try:
                            mom = float(str(row.iloc[5]).replace(',', ''))
                            print(f"MoM Parsed: {mom}")
                        except Exception as e:
                            print(f"MoM Parse Error: {e}")
                            
                        try:
                            yoy = float(str(row.iloc[6]).replace(',', ''))
                            print(f"YoY Parsed: {yoy}")
                        except Exception as e:
                            print(f"YoY Parse Error: {e}")
                        break
                except: continue
except Exception as e:
    print(e)
