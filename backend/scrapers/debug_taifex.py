import pandas as pd
import requests
from io import StringIO

url = "https://www.taifex.com.tw/cht/3/futContractsDate"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print(f"Fetching {url}...")
try:
    r = requests.get(url, headers=headers)
    r.encoding = 'utf-8'
    print("Response Length:", len(r.text))
    
    # Try generic match
    dfs = pd.read_html(StringIO(r.text), match="期貨")
    print(f"Found {len(dfs)} tables matching '期貨'")
    
    for i, df in enumerate(dfs):
        print(f"\n--- Table {i} ---")
        # Flatten
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
            
        print("COLUMNS:", list(df.columns))
        # Try to find which column is Contract
        col_contract = next((c for c in df.columns if "契約" in c), None)
        if col_contract:
            print(f"Identified Contract Column: [{col_contract}]")
            print("First 10 values in this column:")
            print(df[col_contract].head(10).tolist())
            
            subset = df[df[col_contract].astype(str).str.contains("臺股期貨", na=False)]
            print(f"Rows matching '臺股期貨': {len(subset)}")
        else:
            print("No '契約' column found.")
            
        col_identity = next((c for c in df.columns if "身" in c), None) # '身分別' or '身份別'
        if col_identity:
             print(f"Identified Identity Column: [{col_identity}]")
             print(df[col_identity].head(10).tolist())
            
except Exception as e:
    print("Error:", e)
