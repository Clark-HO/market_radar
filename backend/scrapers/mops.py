from functools import lru_cache
import pandas as pd
import requests
import time
from datetime import datetime

class MOPSScraper:
    def __init__(self):
        self.base_url = "https://mops.twse.com.tw/mops/web"
        self.headers = {
             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
             "Origin": "https://mops.twse.com.tw"
        }

    @lru_cache(maxsize=4)
    def fetch_monthly_revenue(self, year: int, month: int):
        """
        Fetch monthly revenue for all companies.
        Year: Republic Era (e.g., 113 for 2024)
        """
        url = f"{self.base_url}/ajax_t05st10_ifrs"
        
        # MOPS uses ROC year
        roc_year = year if year < 1000 else year - 1911
        
        form_data = {
            "encodeURIComponent": "1",
            "step": "1",
            "firstin": "1",
            "off": "1",
            "year": str(roc_year),
            "month": str(month).zfill(2),
            "co_id": "", # Empty for all
            "type": "none", # 'sii' for TWSE, 'otc' for TPEX, etc.
        }
        
        try:
            time.sleep(3)
            # Need to specify 'sii' (上市) and 'otc' (上櫃) separately usually, or Iterate?
            # actually t05st10 usually returns a table.
            # Let's try fetching for 'sii' (Listing) first.
            
            form_data['type'] = 'sii' # Domestic Listing
            
            response = requests.post(url, data=form_data, headers=self.headers, timeout=10, verify=False)
            response.encoding = 'utf8'
            
            dfs = pd.read_html(response.text)
            # dfs usually contains multiple tables, the main one is often index 0 or 1
            if dfs:
                return dfs[1] # Usually the second table has the data, 0 is often header/stats
            return None
        except Exception as e:
            print(f"MOPS Revenue fetch failed: {e}")
            return None

    def fetch_eps(self, year: int, season: int):
        """
        Fetch EPS (Comprehensive Income)
        """
        url = f"{self.base_url}/ajax_t163sb04"
        roc_year = year if year < 1000 else year - 1911
        
        form_data = {
            "encodeURIComponent": "1",
            "step": "1",
            "firstin": "1",
            "off": "1",
            "year": str(roc_year),
            "season": str(season),
            "type": "sii", # Listing
        }
        
        try:
            time.sleep(3)
            response = requests.post(url, data=form_data, headers=self.headers)
            response.encoding = 'utf8'
            
            dfs = pd.read_html(response.text)
            if dfs:
                # Need to find the table with EPS
                return dfs[-1] # Often the last one or by analyzing columns
            return None
        except Exception as e:
             print(f"MOPS EPS fetch failed: {e}")
             return None

if __name__ == "__main__":
    scraper = MOPSScraper()
    print("Testing Monthly Revenue...")
    # Test with last month (e.g., 2024, 1)
    print(scraper.fetch_monthly_revenue(2024, 1))
