import requests
import pandas as pd
from io import StringIO
import yfinance as yf

# 1. Debug Futures
print("--- Debugging Futures (TAIFEX) ---")
try:
    url = "https://www.taifex.com.tw/cht/3/futContractsDate"
    r = requests.get(url, verify=False, timeout=10)
    print(f"Status: {r.status_code}")
    dfs = pd.read_html(StringIO(r.text), match="期貨")
    print(f"Found {len(dfs)} tables")
    for i, df in enumerate(dfs):
        print(f"Table {i}:")
        print(df.head(3))
        # Try to find Foreign Net OI
        # Usually it's in a row with '外資' and col '未平倉餘額' -> '口數'
        # Need to print column names to be sure
except Exception as e:
    print(f"Futures Error: {e}")

# 2. Debug Currency
print("\n--- Debugging Currency (Yahoo) ---")
try:
    t = yf.Ticker("USDTWD=X")
    print(f"Fast Info Last: {t.fast_info.last_price}")
    print(f"Info Bid: {t.info.get('bid')}")
except Exception as e:
    print(f"Currency Error: {e}")
