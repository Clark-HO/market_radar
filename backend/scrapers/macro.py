import requests
import pandas as pd
import yfinance as yf
import json
import time
import os
from datetime import datetime
from io import StringIO

# 確保路徑正確 (存到 E:\antigravity\market_radar\frontend\public\macro_data.json)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUBLIC_DIR = os.path.join(BASE_DIR, "frontend", "public")
if not os.path.exists(PUBLIC_DIR):
    os.makedirs(PUBLIC_DIR)
    
MACRO_DATA_FILE = os.path.join(PUBLIC_DIR, "macro_data.json")

class MacroScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_yahoo_safe(self, ticker_id, name):
        """
        [新增] 安全抓取 Yahoo 數據的通用函式
        包含：自動重試機制 (Retry Logic)
        """
        print(f"   -> Fetching {name} ({ticker_id})...")
        retries = [5, 10, 15] # 第一次失敗等5秒，第二次10秒...
        
        for i, delay in enumerate(retries):
            try:
                # 使用 fast_info 比較快且不易被擋
                t = yf.Ticker(ticker_id)
                price = t.fast_info.last_price
                
                # 嘗試抓歷史計算漲跌幅
                change = 0
                change_pct = 0
                try:
                    hist = t.history(period="2d")
                    if len(hist) >= 2:
                        curr = hist.iloc[-1]['Close']
                        prev = hist.iloc[-2]['Close']
                        change = curr - prev
                        change_pct = (change / prev) * 100
                except:
                    pass # 如果抓不到歷史就算了，至少有現價
                
                return {
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2)
                }
                
            except Exception as e:
                if i < len(retries) - 1:
                    print(f"      ⚠️ Yahoo Busy. Retrying in {delay}s... ({i+1}/{len(retries)})")
                    time.sleep(delay)
                else:
                    print(f"      ❌ Failed to fetch {name}: {e}")
                    return None
        return None

    def fetch_taiex(self):
        """抓取加權指數 (^TWII)"""
        data = self.fetch_yahoo_safe("^TWII", "TAIEX")
        if data:
            return {
                "taiex_close": data['price'],
                "change": data['change'],
                "change_percent": data['change_percent']
            }
        return None

    def fetch_currency(self):
        """抓取匯率 (USDTWD=X)"""
        data = self.fetch_yahoo_safe("USDTWD=X", "USD/TWD")
        if data:
            trend = "Stable"
            if data['change'] > 0: trend = "Depreciating" # 台幣貶值 (USD變貴)
            elif data['change'] < 0: trend = "Appreciating"
            
            return {
                "usd_twd": data['price'],
                "trend": trend
            }
        return {"usd_twd": 32.0, "trend": "Stable"}

    def fetch_futures_oi(self):
        """
        抓取期交所外資空單 (保留你原本優秀的邏輯)
        """
        print("   -> Fetching Futures OI (TAIFEX Scraper)...")
        url = "https://www.taifex.com.tw/cht/3/futContractsDate"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            dfs = pd.read_html(StringIO(response.text), match="期貨")
            
            for i, df in enumerate(dfs):
                # print(f"      👀 Inspecting Table {i} Shape: {df.shape}")
                
                df = df.reset_index()
                
                # 處理 MultiIndex 欄位名稱
                if isinstance(df.columns, pd.MultiIndex):
                     df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
                
                # 關鍵字搜尋欄位
                col_contract = next((c for c in df.columns if "契約" in c or "商品" in c), None)
                col_identity = next((c for c in df.columns if "身" in c), None)
                col_net_oi   = next((c for c in df.columns if "多空淨額" in c and "未平倉" in c), None)
                
                if col_contract and col_identity and col_net_oi:
                    # 填補空白欄位 (Forward Fill)
                    df[col_contract] = df[col_contract].ffill()
                    
                    # 篩選：臺股期貨 + 外資 (排除小型)
                    target_row = df[
                        (df[col_contract].astype(str).str.contains("臺股期貨")) &
                        (~df[col_contract].astype(str).str.contains("小型")) & 
                        (df[col_identity].astype(str).str.contains("外資"))
                    ]
                    
                    if not target_row.empty:
                        raw_val = target_row.iloc[0][col_net_oi]
                        try:
                            net_oi = int(str(raw_val).replace(",", "").strip())
                            print(f"      ✅ Found Foreign Futures Net OI: {net_oi}")
                            return net_oi
                        except:
                            print(f"      ⚠️ Parse Error for value: {raw_val}")

            print("      ⚠️ Scraper finished but could not find target row.")
            return -35000 
            
        except Exception as e:
            print(f"      ⚠️ Futures fetch failed: {e}")
            return -5000 

    def fetch_sector_flow(self):
        """
        抓取真實類股資金流向 (TWSE BFIAMU)
        """
        print("   -> Fetching Sector Flow (TWSE BFIAMU)...")
        
        # 嘗試抓取最新交易日 (回溯 5 天)
        date_check = datetime.now()
        found_data = None
        
        for _ in range(5):
            date_str = date_check.strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/rwd/zh/afterTrading/BFIAMU?date={date_str}&response=json"
            try:
                r = requests.get(url, headers=self.headers, timeout=10)
                data = r.json()
                if data.get('stat') == 'OK':
                    found_data = data
                    print(f"      ✅ Found Sector Data for {date_str}")
                    break
            except:
                pass
            date_check -= timedelta(days=1)
            
        if not found_data:
            print("      ⚠️ Sector Flow fetch failed. Using empty list.")
            return []

        # Parse Data
        # Fields: ['分類指數名稱', '成交股數', '成交金額', '成交筆數', '漲跌指數']
        # Index 0: Name, Index 2: Value
        try:
            raw_sectors = []
            total_value = 0
            
            for row in found_data.get('data', []):
                name = row[0]
                val_str = row[2]
                try:
                    val = float(val_str.replace(',', ''))
                    total_value += val
                    # Filter out "Total" (總計) or specific aggregate rows if any
                    if name not in ['發行量加權股價指數', '未含金融保險股指數', '未含電子股指數', '未含金融電子股指數']:
                         raw_sectors.append({"name": name, "value": val})
                except:
                    continue
            
            # Sort by Value Desc
            raw_sectors.sort(key=lambda x: x['value'], reverse=True)
            
            # Take Top 5 and Aggregate Others
            top_5 = raw_sectors[:5]
            others_val = sum(x['value'] for x in raw_sectors[5:])
            
            result = []
            
            # Helper to determine trend (Hot/Cool) - simplified logic based on Ratio?
            # Or usually we compare to yesterday. 
            # For now, just labels based on volume dominance.
            
            for s in top_5:
                ratio = (s['value'] / total_value) * 100
                trend = "Normal"
                if ratio > 30: trend = "Hot"
                elif ratio < 5: trend = "Cool"
                
                # Normalize names (Remove "類")
                display_name = s['name'].replace("類", "")
                
                result.append({
                    "name": display_name,
                    "ratio": round(ratio, 1),
                    "trend": trend
                })
            
            # Add Others
            if others_val > 0:
                others_ratio = (others_val / total_value) * 100
                result.append({
                    "name": "其他",
                    "ratio": round(others_ratio, 1),
                    "trend": "Normal"
                })
                
            return result
            
        except Exception as e:
            print(f"      ⚠️ Sector parsing failed: {e}")
            return []

    def run(self):
        print("🚀 [Macro Worker] Starting Update (Robust Mode)...")
        
        # 1. 強制休息一下，避免跟上一支程式 (data_updater) 搶頻寬被 Yahoo 封鎖
        time.sleep(2)
        
        # 2. TAIEX
        taiex = self.fetch_taiex()
        if not taiex:
             taiex = {"taiex_close": 0.0, "change": 0.0, "change_percent": 0.0}

        # 3. Futures
        net_oi = self.fetch_futures_oi()
        
        # 判斷多空訊號
        fut_status = "Neutral"
        color = "gray"
        if net_oi < -15000: # 空單超過 1.5萬口
            fut_status = "Bearish Alert"
            color = "red" # 依照你的設定: 紅色代表警戒
        elif net_oi > 10000:
             fut_status = "Bullish"
             color = "green"
        
        futures_data = {
            "futures_net_oi": net_oi,
            "futures_status": fut_status,
            "futures_color": color
        }

        # 4. Currency
        curr = self.fetch_currency()

        # 5. Sector
        volume = self.fetch_sector_flow()
        
        # Assemble
        data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "market_status": taiex,
            "chips": futures_data,
            "currency": curr,
            "sector_flow": volume
        }
        
        with open(MACRO_DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print(f"✅ [Macro Worker] Data saved to {MACRO_DATA_FILE}")

if __name__ == "__main__":
    scraper = MacroScraper()
    scraper.run()