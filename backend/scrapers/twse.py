from functools import lru_cache
import pandas as pd
import requests
import time
from datetime import datetime
import json

class TWSEScraper:
    def __init__(self):
        self.base_url = "https://www.twse.com.tw"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://www.twse.com.tw/zh/page/trading/exchange/STOCK_DAY.html"
        }

    # Cache the result for at least a few minutes/hours since it's daily data
    # Note: simple lru_cache works for arguments, but here we want to cache by date essentially.
    
    def _get_json(self, url, params=None):
        try:
            time.sleep(1) # Reduced sleep, rely on cache
            print(f"Fetching {url}...")
            # Disable SSL verify to avoid hangs on some corporate networks/proxies
            response = requests.get(url, params=params, headers=self.headers, timeout=5, verify=False) 
            response.raise_for_status()
            data = response.json()
            if data['stat'] != 'OK':
                print(f"Error fetching data: {data['stat']}")
                return None
            return data
        except Exception as e:
            print(f"Request failed: {e}")
            return None

    def fetch_daily_quotes(self, stock_id: str):
        """
        Fetch daily quotes for a specific stock for the current month.
        """
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        url = f"{self.base_url}/exchangeReport/STOCK_DAY"
        params = {
            "response": "json",
            "date": date_str,
            "stockNo": stock_id
        }
        
        data = self._get_json(url, params)
        if not data:
            return None
            
        # Parse data
        fields = data['fields']
        records = data['data']
        df = pd.DataFrame(records, columns=fields)
        return df

    def fetch_institutional_trading(self):
        """
        Fetch 3 Major Investors trading data (T86).
        """
        now = datetime.now()
        date_str = now.strftime("%Y%m%d") 
        # Note: If today is weekend/holiday, this might fail or return empty. 
        # Real impl needs to find last trading day. For now, try today.
        
        url = f"{self.base_url}/rwd/zh/fund/T86"
        params = {
            "response": "json",
            "date": date_str,
            "selectType": "ALL"
        }
        
        data = self._get_json(url, params)
        if not data:
            return None
            
        fields = data['fields']
        records = data['data']
        df = pd.DataFrame(records, columns=fields)
        return df

    @lru_cache(maxsize=1)
    def fetch_sector_pe(self):
        """
        Fetch Sector P/E, Dividend Yield, PB Ratio (BWESS).
        Cached to avoid hitting TWSE on every request.
        """
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        
        url = f"{self.base_url}/exchangeReport/BWESS"
        params = {
            "response": "json",
            "date": date_str,
            "selectType": "ALL"
        }
        
        print("Scraping Sector PE (This might take a while)...")
        data = self._get_json(url, params)
        if not data:
            return None
        
        fields = data['fields']
        records = data['data']
        df = pd.DataFrame(records, columns=fields)
        return df

if __name__ == "__main__":
    scraper = TWSEScraper()
    print("Testing Daily Quotes for 2330...")
    print(scraper.fetch_daily_quotes("2330"))
