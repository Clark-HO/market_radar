import requests
import pandas as pd
import json
import time
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# 確保路徑正確
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

    def clean_number(self, val):
        """Remove commas and convert to float/int"""
        try:
            if isinstance(val, (int, float)): return val
            return float(str(val).replace(",", "").strip())
        except:
            return 0

    def roc_to_date(self, roc_date_str):
        """Convert '113/02/06' to '2024-02-06'"""
        try:
            parts = roc_date_str.split('/')
            if len(parts) != 3: return roc_date_str
            year = int(parts[0]) + 1911
            return f"{year}-{parts[1]}-{parts[2]}"
        except:
            return roc_date_str

    def fetch_taiex_history(self):
        """
        抓取 TAIEX 歷史數據 (FMTQIK) - 確保取得近 20 日
        來源: TWSE
        """
        print("   -> Fetching TAIEX History (FMTQIK)...")
        history = []
        
        # Fetch Current Month and Previous Month to ensure 20 days
        months_to_fetch = [0, 1] 
        
        for m_offset in months_to_fetch:
            target_date = datetime.now() - relativedelta(months=m_offset)
            date_str = target_date.strftime("%Y%m01")
            url = f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={date_str}&response=json"
            
            try:
                time.sleep(1) # Polite delay
                r = requests.get(url, headers=self.headers, timeout=10)
                data = r.json()
                
                if data.get('stat') == 'OK':
                    # Rows: [日期, 成交股數, 成交金額, 成交筆數, 發行量加權股價指數, 漲跌點數]
                    # Index: 0=Date, 2=Turnover(Amount), 4=Close, 1=Volume(Shares)
                    # We usually visualize Price (4) and Turnover Amount (2) for Index
                    
                    for row in data.get('data', []):
                        date_str = self.roc_to_date(row[0])
                        close = self.clean_number(row[4])
                        turnover = self.clean_number(row[2]) # Amount (Money)
                        change = self.clean_number(row[5])
                        
                        # Extra stats for today (High/Low not directly in FMTQIK summary list, 
                        # usually need Daily Quote for H/L. 
                        # Wait, FMTQIK usually just gives Close. 
                        # Let's check if we can get High/Low. 
                        # Actually FMTQIK is 'Daily Average' stats. 
                        # For true Daily OHLC, we assume Close is good enough for History Line.
                        # For TODAY's High/Low, we might need a separate fetch or use the latest Close as proxy for now.
                        # User asked for "Daily High/Low". 
                        # NOTE: FMTQIK *does* store H/L in specific columns? No, usually just Close.
                        # Let's stick to Close/Volume for History Chart first.
                        
                        history.append({
                            "date": date_str,
                            "close": close,
                            "volume": turnover / 100000000, # Convert to E (億)
                            "change": change
                        })
            except Exception as e:
                print(f"      ⚠️ Month {m_offset} fetch failed: {e}")
        
        # Sort and Slice
        history.sort(key=lambda x: x['date'])
        
        # Remove duplicates if overlaps
        unique_history = {v['date']:v for v in history}.values()
        history = list(unique_history)
        history.sort(key=lambda x: x['date'])
        
        last_20 = history[-20:]
        print(f"      ✅ Got {len(last_20)} days history.")
        return last_20

    def fetch_daily_stats_and_institutional(self, latest_date_str):
        print(f"   -> Fetching Institutional & Stats for {latest_date_str}...")
        
        date_param = latest_date_str.replace("-", "")
        institutional = []
        
        # A. Institutional (BFI82U)
        url_inst = f"https://www.twse.com.tw/rwd/zh/fund/BFI82U?date={date_param}&response=json"
        
        # Init values
        foreign = 0; trust = 0; dealer = 0
        found_rows = False

        try:
            r = requests.get(url_inst, headers=self.headers, timeout=10)
            data = r.json()
            if data.get('stat') == 'OK':
                rows = data.get('data', [])
                found_rows = True
                
                # BFI82U Columns: [0]Unit Name, [1]Buy, [2]Sell, [3]Net
                for row in rows:
                    name = row[0].strip()
                    try:
                        # Explicit string cleaning as requested
                        net_str = str(row[3]).replace(',', '').strip()
                        net_val = float(net_str) / 100000000 # E
                    except: net_val = 0
                    
                    # Logic: Strict matching for Foreign
                    if "外資及陸資(不含外資自營商)" in name: 
                        foreign += net_val
                    elif "投信" in name:
                        trust += net_val
                    elif "自營商" in name and "合計" not in name:
                        dealer += net_val
                        
                print(f"      ✅ Inst Found: Foreign={foreign:.2f}, Trust={trust:.2f}, Dealer={dealer:.2f}")

                institutional = [
                    {"name": "外資", "net": round(foreign, 2)},
                    {"name": "投信", "net": round(trust, 2)},
                    {"name": "自營商", "net": round(dealer, 2)}
                ]
            else:
                 print(f"      ⚠️ BFI82U Stat: {data.get('stat')}, Msg: {data.get('title')}")
                 
        except Exception as e:
            print(f"      ⚠️ Inst fetch failed: {e}")

        if not found_rows:
             institutional = [
                {"name": "外資", "net": 0}, {"name": "投信", "net": 0}, {"name": "自營商", "net": 0}
            ]
        
        return institutional, {} 

    def fetch_twse_mis_stats(self):
        """
        [New] Fetch Realtime High/Low directly from TWSE MIS
        Endpoint: https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw
        """
        print("   -> Fetching Realtime TAIEX Stats (TWSE MIS)...")
        timestamp = int(time.time() * 1000)
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw&json=1&delay=0&_={timestamp}"
        
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            data = r.json()
            
            if 'msgArray' in data and len(data['msgArray']) > 0:
                info = data['msgArray'][0]
                
                # h = High, l = Low, z = Current Price, o = Open, y = Yesterday Close
                def p(k): 
                    try: 
                        val = str(info.get(k, '0'))
                        return float(val.replace(',', '')) 
                    except: return 0.0
                
                high = p('h')
                low = p('l')
                curr = p('z')
                open_p = p('o')
                prev = p('y')
                
                # Fallbacks if Market Closed/Zero
                if high == 0 and curr > 0: high = curr
                if low == 0 and curr > 0: low = curr
                
                change = curr - prev
                change_pct = (change / prev) * 100 if prev > 0 else 0
                
                print(f"      ✅ MIS Stats: H={high}, L={low}, Now={curr}")
                
                return {
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(curr, 2),
                    "open": round(open_p, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "price": round(curr, 2)
                }
        except Exception as e:
            print(f"      ⚠️ MIS fetch failed: {e}. Falling back to Yahoo.")
            
        # Fallback to Yahoo Safe
        return self.fetch_yahoo_stats_fallback()

    def fetch_yahoo_stats_fallback(self):
        import yfinance as yf
        try:
            t = yf.Ticker("^TWII")
            info = t.fast_info
            
            price = info.last_price or 0
            hi = info.day_high or 0
            lo = info.day_low or 0
            prev = info.previous_close or 0
            
            if hi == 0: hi = price
            if lo == 0: lo = price
            
            change = price - prev
            change_pct = (change / prev) * 100 if prev > 0 else 0
            
            return {
                "high": round(hi, 2),
                "low": round(lo, 2),
                "close": round(price, 2),
                "open": round(0, 2),
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "price": round(price, 2)
            }
        except:
             return {"high": 0, "low": 0, "close": 0, "open": 0, "change": 0, "change_percent": 0, "price": 0}

    def fetch_sector_flow(self):
        # ... (Keep existing BFIAMU logic, abridged for brevity but will include full) ...
        # Copied from previous logical block
        print("   -> Fetching Sector Flow (TWSE BFIAMU)...")
        date_check = datetime.now()
        found_data = None
        for _ in range(5):
            date_str = date_check.strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/rwd/zh/afterTrading/BFIAMU?date={date_str}&response=json"
            try:
                r = requests.get(url, headers=self.headers, timeout=5)
                data = r.json()
                if data.get('stat') == 'OK':
                    found_data = data; break
            except: pass
            date_check -= timedelta(days=1)
            
        if not found_data: return []

        try:
            raw_sectors = []
            total_value = 0
            for row in found_data.get('data', []):
                name = row[0]
                try:
                    val = float(str(row[2]).replace(',', ''))
                    total_value += val
                    if name not in ['發行量加權股價指數', '未含金融保險股指數', '未含電子股指數', '未含金融電子股指數']:
                         raw_sectors.append({"name": name, "value": val})
                except: continue
            
            raw_sectors.sort(key=lambda x: x['value'], reverse=True)
            result = []
            for s in raw_sectors[:5]:
                ratio = (s['value'] / total_value) * 100
                trend = "Hot" if ratio > 30 else "Cool" if ratio < 5 else "Normal"
                result.append({"name": s['name'].replace("類", ""), "ratio": round(ratio, 1), "trend": trend})
            
            others = sum(x['value'] for x in raw_sectors[5:])
            if others > 0:
                result.append({"name": "其他", "ratio": round((others/total_value)*100, 1), "trend": "Normal"})
            return result
        except: return []

    def fetch_currency(self):
        """Fetch USD/TWD from Bank of Taiwan (Realtime & Robust)"""
        try:
            url = "https://rate.bot.com.tw/xrt?Lang=en-US"
            r = requests.get(url, headers=self.headers, timeout=10)
            # Simple text parsing to find USD and the Spot Selling rate
            # HTML structure: <td data-table="Currency">...USD...</td>...<td data-table="Spot Selling">32.5</td>
            if "USD" in r.text:
                # Find the block with USD, then find the rate
                # Split by USD to get the section after it
                parts = r.text.split('USD')
                if len(parts) > 1:
                    # Look for data-table="Spot Selling" in the immediate following text
                    # Regex is cleaner
                    import re
                    # Pattern: Spot Selling.*?class="rate-content-sight text-right print_width".*?>([\d.]+)
                    match = re.search(r'Spot Selling.*?class="rate-content-sight text-right print_width"[^>]*>([\d.]+)', parts[1], re.DOTALL)
                    if match:
                        price = float(match.group(1))
                        return {"usd_twd": price, "trend": "Stable"}
            
            # Fallback to Yahoo if BOT fails
            return self.fetch_yahoo_currency_fallback()
        except: return self.fetch_yahoo_currency_fallback()

    def fetch_yahoo_currency_fallback(self):
        import yfinance as yf
        try:
            t = yf.Ticker("USDTWD=X")
            price = t.fast_info.last_price
            return {"usd_twd": round(price, 2), "trend": "Stable"}
        except: return {"usd_twd": 32.5, "trend": "Stable"}

    def fetch_futures_oi(self):
        """
        Fetch Futures Net OI (Foreign) from TAIFEX.
        Resilient Text Search approach.
        """
        try:
            url = "https://www.taifex.com.tw/cht/3/futContractsDate"
            r = requests.get(url, headers=self.headers, verify=False, timeout=10)
            r.encoding = 'utf-8' # Ensure correct decoding
            
            # Logic:
            # 1. Find "臺股期貨" (TAIEX Futures) block.
            # 2. Inside that, find "外資" (Foreign Investors).
            # 3. Get the "Net OI" column (usually the last or specific offset).
            
            # Since HTML table parsing is fragile, let's use pandas if possible, but handle "No Tables Found"
            try:
                dfs = pd.read_html(StringIO(r.text))
            except: dfs = []
            
            for df in dfs:
                # Convert to string to search keywords
                df_str = df.to_string()
                if "臺股期貨" in df_str and "外資" in df_str:
                    # Iterate rows to find the exact line
                    # Usually: [Identity, Long, Short, Net] ...
                    # We want "外資" row's "未平倉餘額" -> "多空淨額" (Net OI)
                    # Many columns. Let's find row with "外資"
                    for _, row in df.iterrows():
                        row_s = [str(x) for x in row.values]
                        if any("外資" in x for x in row_s):
                            # This is the Foreign row.
                            # Extract all numbers. The Net OI is often the last integer or 2nd to last?
                            # Table: ... | Net Buy/Sell | ... | Open Interest (Long) | Open Interest (Short) | Open Interest (Net)
                            # Actually TAIFEX "Daily" table:
                            # Identity | Trading Lot | ... | Open Interest
                            #          | Long | Short | Net | Long | Short | Net
                            # We want Open Interest -> Net. (The last column usually)
                            
                            numbers = []
                            for val in row_s:
                                try:
                                    # Remove commas, skip empty
                                    clean = val.replace(',', '').strip()
                                    if clean.replace('-', '').isdigit():
                                        numbers.append(int(clean))
                                except: pass
                            
                            if numbers:
                                # The last number is usually Net OI on TAIFEX summary
                                return numbers[-1]
                                
            return None # Not found
        except Exception as e: 
            print(f"Futures Error: {e}")
            return None

    def run(self):
        print("🚀 [Macro Worker] Starting Update (TWSE Enhanced)...")
        time.sleep(1)
        
        # 1. History (20 Days)
        history = self.fetch_taiex_history()
        
        # 2. Latest Data Points
        last_date = history[-1]['date'] if history else datetime.now().strftime("%Y-%m-%d")
        
        # 3. Institutional & Stats
        inst_data, _ = self.fetch_daily_stats_and_institutional(last_date)
        
        # 4. Realtime Stats (TWSE MIS -> Yahoo Fallback)
        rt_stats = self.fetch_twse_mis_stats()
        
        # 5. Sector & Currency & Futures
        sector = self.fetch_sector_flow()
        curr = self.fetch_currency()
        fut_oi = self.fetch_futures_oi()
        
        # Futures Color
        fut_status = "Neutral"
        fut_color = "gray"
        if fut_oi is None:
            fut_oi = "N/A"
            fut_status = "N/A"
            fut_color = "gray"
        else:
            if fut_oi < -10000: fut_status = "Bearish"; fut_color = "green" 
            if fut_oi > 0: fut_color = "red"; fut_status = "Bullish"
            else: fut_color = "green"; fut_status = "Bearish"
        
        final_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "market_status": {
                "taiex_close": history[-1]['close'] if history else 0,
                "change": history[-1]['change'] if history else 0,
                "change_percent": round((history[-1]['change'] / (history[-1]['close'] - history[-1]['change'])) * 100, 2) if history else 0,
                "high": rt_stats['high'],
                "low": rt_stats['low'],
                "volume": history[-1]['volume'] if history else 0 # 億
            },
            "history": history,
            "institutional": inst_data,
            "chips": {
                "futures_net_oi": fut_oi,
                "futures_status": fut_status,
                "futures_color": fut_color
            },
            "currency": curr,
            "sector_flow": sector
        }
        
        with open(MACRO_DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Saved to {MACRO_DATA_FILE}")

if __name__ == "__main__":
    s = MacroScraper()
    s.run()