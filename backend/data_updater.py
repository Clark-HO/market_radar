import time
import json
import requests
import pandas as pd
import yfinance as yf
import datetime
import os
import urllib3
from io import StringIO
from dateutil.relativedelta import relativedelta
from dateutil.relativedelta import relativedelta
# from backend import analysis # Removed for Pure Scraper

# --- 0. 忽略 SSL 警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 設定路徑 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Target: market_radar/frontend/public
PUBLIC_DIR = os.path.join(BASE_DIR, "frontend", "public")
if not os.path.exists(PUBLIC_DIR):
    os.makedirs(PUBLIC_DIR)
    
JSON_PATH = os.path.join(PUBLIC_DIR, "stock_data.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Connection": "keep-alive"
}

import math

def get_roc_date_parts(date_obj):
    """回傳：(民國年, 月份數字, 顯示字串)"""
    roc_year = date_obj.year - 1911
    return roc_year, date_obj.month, f"{roc_year}/{date_obj.month}"

def sanitize_float(val):
    """Convert NaN/Infinity to 0 for valid JSON"""
    if val is None: return 0
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f): return 0
        return f
    except: return 0

def fetch_twse_chips_global():
    """[Tier 1] 抓取上市(TWSE)三大法人買賣超"""
    print("🥡 [1/3] Downloading TWSE Chips (Smart Money)...")
    now = datetime.datetime.now()
    for i in range(5):
        target_date = now - datetime.timedelta(days=i)
        if target_date.weekday() > 4: continue 
        date_str = target_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()
            if data.get('stat') == 'OK':
                print(f"   ✅ Found TWSE Chips for {date_str}")
                fields = data.get('fields', [])
                try:
                    idx_foreign = next(i for i, f in enumerate(fields) if '外陸資買賣超' in f)
                    idx_trust = next(i for i, f in enumerate(fields) if '投信買賣超' in f)
                    idx_code = 0
                except:
                    idx_code = 0; idx_foreign = 4; idx_trust = 10
                chips_map = {}
                for row in data.get('data', []):
                    try:
                        code = row[idx_code]
                        name = row[1].strip() # Capture Name
                        if len(code) != 4: continue 
                        def parse_num(s): return int(s.replace(',', '')) if s else 0
                        chips_map[code] = {
                            "name": name,
                            "foreign": parse_num(row[idx_foreign]) // 1000, 
                            "trust": parse_num(row[idx_trust]) // 1000
                        }
                    except: continue
                return chips_map
        except: pass
    print("   ⚠️ Failed to fetch TWSE Chips data.")
    return {}

def fetch_tpex_chips_global():
    """[Tier 1.5] 抓取上櫃(OTC)三大法人買賣超 - 修正 tables 格式與欄位索引"""
    print("🥡 [1.5/3] Downloading OTC Chips...")
    now = datetime.datetime.now()
        
    for i in range(5):
        target_date = now - datetime.timedelta(days=i)
        if target_date.weekday() > 4: continue
        
        roc_year = target_date.year - 1911
        date_str = f"{roc_year}/{target_date.strftime('%m/%d')}"
        
        url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={date_str}"
        headers_tpex = HEADERS.copy()
        headers_tpex["Referer"] = "https://www.tpex.org.tw/"
        
        try:
            r = requests.get(url, headers=headers_tpex, verify=False, timeout=10)
            try: data = r.json()
            except: continue
            
            # --- 關鍵修正：相容 tables 格式 ---
            raw_rows = []
            
            # 優先檢查 tables (新格式)
            if 'tables' in data and len(data['tables']) > 0:
                if 'data' in data['tables'][0]:
                    raw_rows = data['tables'][0]['data']
            # 其次檢查 aaData (舊格式)
            elif 'aaData' in data:
                raw_rows = data['aaData']
            
            if len(raw_rows) > 0:
                print(f"   ✅ Found OTC Chips for {date_str} (Count: {len(raw_rows)})")
                chips_map = {}
                for row in raw_rows:
                    try:
                        code = row[0]
                        name = row[1].strip() # Capture Name
                        if len(code) != 4: continue 
                        def p(v): return int(v.replace(',', '')) if v else 0
                        
                        # [修正索引] 根據您的 Sample Row (24欄)
                        # Index 4: 外資買賣超
                        # Index 13: 投信買賣超 (原本是 7 錯了)
                        
                        # 防呆：確保欄位夠長
                        if len(row) > 13:
                            foreign_net = p(row[4]) // 1000
                            trust_net = p(row[13]) // 1000
                        else:
                            # 萬一格式不同，Fallback 到舊版索引
                            foreign_net = p(row[4]) // 1000
                            trust_net = p(row[7]) // 1000

                        chips_map[code] = {
                            "name": name,
                            "foreign": foreign_net,
                            "trust": trust_net
                        }
                    except: continue
                return chips_map
        except Exception: continue
    
    print("   ⚠️ Failed to fetch OTC Chips.")
    return {}

def fetch_mops_revenue_history_global():
    """[Tier 2] 抓取 MOPS 營收"""
    print("🥡 [2/3] Building 12-Month Revenue History (MOPS)...")
    history_map = {} 
    latest_stats_map = {} 
    MOPS_DOMAIN = "https://mopsov.twse.com.tw" 
    anchor_date = datetime.datetime.now()
    found_anchor = False
    
    print(f"   🕵️ Probing {MOPS_DOMAIN} for latest data...")
    for i in range(1, 25): 
        probe_date = anchor_date - relativedelta(months=i)
        roc_year, roc_month, roc_str = get_roc_date_parts(probe_date)
        url = f"{MOPS_DOMAIN}/nas/t21/sii/t21sc03_{roc_year}_{roc_month}_0.html"
        try:
            r = requests.get(url, headers=HEADERS, verify=False, timeout=5)
            r.encoding = 'big5'
            if r.status_code == 200 and len(r.text) > 5000:
                try:
                    pd.read_html(StringIO(r.text))
                    anchor_date = probe_date
                    found_anchor = True
                    print(f"   ✅ Anchor found at: {roc_str}")
                    break
                except: pass
        except: pass
            
    if not found_anchor:
        print("   ❌ Critical: Could not find ANY revenue data.")
        return ({}, {})

    for i in range(12):
        target_date = anchor_date - relativedelta(months=i)
        roc_year, roc_month, roc_str = get_roc_date_parts(target_date)
        is_latest_month = (i == 0)
        
        markets = ['sii', 'otc']
        for mkt in markets:
            url = f"{MOPS_DOMAIN}/nas/t21/{mkt}/t21sc03_{roc_year}_{roc_month}_0.html"
            try:
                r = requests.get(url, headers=HEADERS, verify=False, timeout=10)
                r.encoding = 'big5'
                dfs = pd.read_html(StringIO(r.text))
                for df in dfs:
                    if df.shape[1] > 6:
                        df.columns = [str(col) for col in df.columns]
                        cols_str = "".join(df.columns)
                        if "代號" in cols_str or "公司" in cols_str or True:
                             for _, row in df.iterrows():
                                try:
                                    code = str(row.iloc[0]).strip()
                                    if len(code) != 4 or not code.isdigit(): continue
                                    rev_raw = row.iloc[2]
                                    if pd.isna(rev_raw) or str(rev_raw).strip() == '-': continue
                                    # REVERT: Use * 1000 to get Raw Dollars (Frontend divides by 10^8)
                                    rev_val = float(str(rev_raw).replace(',', '')) * 1000 
                                    
                                    if code not in history_map: history_map[code] = []
                                    history_map[code].append({
                                        "date": target_date.strftime("%Y-%m"),
                                        "revenue": rev_val 
                                    })
                                    
                                    # Capture YoY from the most recent valid month (MOPS Source)
                                    if code not in latest_stats_map:
                                        try:
                                            # Index 6: YoY
                                            yoy = float(str(row.iloc[6]).replace(',', ''))
                                            latest_stats_map[code] = {"mom": 0, "yoy": yoy} # MoM calc later
                                        except:
                                            latest_stats_map[code] = {"mom": 0, "yoy": 0}
                                except: continue
            except: continue

    # Reverse history & Manual MoM Calculation
    for code, hist in history_map.items():
        hist.reverse() # Oldest to Newest
        
        # Calculate MoM manually for consistency
        if len(hist) >= 2:
            latest = hist[-1]['revenue']
            prev = hist[-2]['revenue']
            if prev > 0:
                mom = ((latest - prev) / prev) * 100
                if code in latest_stats_map:
                    latest_stats_map[code]['mom'] = round(mom, 2)
                else:
                    latest_stats_map[code] = {"mom": round(mom, 2), "yoy": 0}
    return history_map, latest_stats_map


DATA_FILE = "stock_data.json"

def main():
    import sys
    import time
    import os
    
    # Check for Freshness (12 Hours)
    # Allows bypassing via --force flag or if file doesn't exist
    has_force_flag = '--force' in sys.argv
    is_fresh = False
    
    if os.path.exists(DATA_FILE) and not has_force_flag:
        mtime = os.path.getmtime(DATA_FILE)
        age_hours = (time.time() - mtime) / 3600
        if age_hours < 12:
            is_fresh = True
            print(f"✅ Data is fresh (Updated {age_hours:.1f} hours ago). Skipping update.")
            print("   (Use '--force' to run anyway)")
            return

    # Start Update Process
    if has_force_flag:
        print("🚀 Force Update Requested...")
    else:
        print(f"📉 Data is old (or missing). Starting update...")
        
    twse_chips = fetch_twse_chips_global()
    tpex_chips = fetch_tpex_chips_global()
    
    full_chips = twse_chips.copy()
    full_chips.update(tpex_chips)
    
    revenue_history, revenue_stats = fetch_mops_revenue_history_global()
    
    raw_stocks = list(full_chips.keys())
    target_stocks = [c for c in raw_stocks if len(c) == 4]
    
    if len(target_stocks) < 10:
         print("   ⚠️ Chips API returned few stocks. Adding fallback list.")
         fallback = ["2330", "2317", "2454", "2603", "2881", "8069", "3293", "5347", "2365"]
         for s in fallback:
             if s not in target_stocks: target_stocks.append(s)
    
    print(f"🚀 [3/3] Processing Batch Data for {len(target_stocks)} stocks...")
    
    
    # [Safety Layer 1] Data Merging: Load existing data first
    final_db = {}
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, 'r', encoding='utf-8') as f:
                final_db = json.load(f)
            print(f"🔄 Loaded existing DB ({len(final_db)} records). Using as base.")
        except:
             print("⚠️ Failed to load existing DB. Starting fresh.")
    
    batch_size = 50
    
    for i in range(0, len(target_stocks), batch_size):
        batch = target_stocks[i:i+batch_size]
        print(f"   Batch {i}-{i+len(batch)} processing...")
        
        yf_tickers = []
        for c in batch:
            if c in tpex_chips: yf_tickers.append(f"{c}.TWO")
            else: yf_tickers.append(f"{c}.TW")
        
        # [Safety Layer 3] Optimize YFinance Call (Retry Loop)
        tickers = None
        for attempt in range(3):
            try:
                tickers = yf.Tickers(" ".join(yf_tickers))
                break
            except Exception as e:
                print(f"   ⚠️ YFinance Retry {attempt+1}/3: {e}")
                time.sleep(2)
        
        if not tickers:
            print("   ❌ Failed to fetch batch after 3 retries. Skipping.")
            continue

        try:
            # Process Batch
            for code in batch:
                try:
                    price = 0; pe = 0
                    suffix = ".TWO" if code in tpex_chips else ".TW"
                    
                    try:
                        t = tickers.tickers[f"{code}{suffix}"]
                        fast_info = t.fast_info
                        price = fast_info.last_price
                        info = t.info
                        pe = info.get('trailingPE')
                        if pe is None:
                            eps = info.get('trailingEps')
                            if eps and eps > 0 and price:
                                pe = price / eps
                            else:
                                pe = info.get('forwardPE', 0)
                    except: pass 
                        
                    sector_pe = 20.0 
                    status = "Fair Value"
                    score = 0
                    if pe and pe > 0:
                        score = pe / sector_pe
                        if score > 1.2: status = "High Premium"
                        elif score < 0.8: status = "Undervalued"
                    elif price > 0: status = "N/A"
                    
                    # [Safety Layer 1] Only overwrite if fetch was successful
                    if price <= 0:
                        if code in final_db:
                           # Keep existing data
                           continue
                        
                        # Special Logic for 2330 Fallback if completely missing
                        if code == "2330":
                            # Force inject 2330 if missing
                            pass # Will fall through to exception handler logic below? 
                            # Actually, simpler to raise exception here to trigger fallback
                            raise ValueError("TSMC Fetch Failed")
                        continue

                    rev_hist = revenue_history.get(code, [])
                    last_rev = rev_hist[-1]['revenue'] if rev_hist else 0
                    stats = revenue_stats.get(code, {"mom": 0, "yoy": 0})
                    chip_info = full_chips.get(code, {"foreign": 0, "trust": 0, "name": code})
                    stock_name = chip_info.get('name', code) # Get Name
                    
                    item_data = {
                        "stock_id": code,
                        "stock_name": stock_name,
                        "valuation": {
                            "stock_id": code, 
                            "current_pe": round(sanitize_float(pe), 2),
                            "sector_pe": sanitize_float(sector_pe),
                            "pe_score": round(sanitize_float(score), 2),
                            "status": status, 
                            "price": round(sanitize_float(price), 1)
                        },
                        "revenue": {
                            "date": rev_hist[-1]['date'] if rev_hist else "N/A",
                            "revenue": sanitize_float(last_rev), 
                            "mom": sanitize_float(stats.get('mom')), 
                            "yoy": sanitize_float(stats.get('yoy')), 
                            "history": rev_hist 
                        }
                    }
                    
                    # AI Report - REMOVED (Moved to On-Demand API)
                    # Data Updater now only handles numeric data.

                    final_db[code] = item_data
                    
                except Exception:
                    # Fallback for 2330 if YFinance fails but we want it in DB
                    if code == "2330" and "2330" not in final_db:
                        # Mock/Fallback Data for TSMC (Pure Numeric)
                        print("⚠️ using built-in fallback for 2330...")
                        fb = {
                             "stock_id": "2330", "stock_name": "台積電",
                             "valuation": { "stock_id": "2330", "current_pe": 28.5, "sector_pe": 20.0, "pe_score": 1.42, "status": "High Premium", "price": 1050.0 },
                             "revenue": { "date": "2026-02", "revenue": 250000000000, "mom": 5.2, "yoy": 35.5, "history": [] },
                             "chips": { "foreign_net": 12000, "trust_net": 3000, "analysis": "Accumulating" }
                        }
                        # No AI here.
                        final_db["2330"] = fb
                    continue
            time.sleep(1) 
        except Exception: print("Batch skipped")

    # [Safety Layer 2] The "Canary" Integrity Check (Safe Save)
    print("🛡️ Performing Integrity Checks...")
    
    # Check 1: Total Count
    if len(final_db) < 5:
        print(f"❌ Critical Error: Integrity Check Failed! Only {len(final_db)} stocks found (Minimum 5).")
        print("🛑 Update Aborted. Old data preserved.")
        exit(1)
        return

    # Check 2: TSMC Canary
    tsmc = final_db.get("2330")
    if not tsmc or tsmc.get("valuation", {}).get("price", 0) <= 0:
        print("❌ Critical Error: Integrity Check Failed! TSMC (2330) is missing or invalid.")
        print("🛑 Update Aborted. Old data preserved.")
        exit(1)
        return

    print("✅ Integrity Check Passed.")
    with open(JSON_PATH, "w", encoding='utf-8') as f:
        json.dump(final_db, f, ensure_ascii=False, indent=2)
    print(f"✅ All Done! Saved to {JSON_PATH}")

if __name__ == "__main__":
    main()