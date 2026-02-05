import yfinance as yf
import json
import os
import datetime
from dateutil.relativedelta import relativedelta
import time

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Target: market_radar/frontend/public
PUBLIC_DIR = os.path.join(BASE_DIR, "frontend", "public")
if not os.path.exists(PUBLIC_DIR):
    os.makedirs(PUBLIC_DIR)

JSON_PATH = os.path.join(PUBLIC_DIR, "global_data.json")

# --- 1. The Knowledge Graph (2026 Event Calendar) ---
# This simulates a "Researched Database" of events and supply chains.
EVENT_CALENDAR = [
    {
        "event": "MWC 世界行動通訊大會 2026",
        "date": "2026-02-26",
        "end_date": "2026-03-01",
        "theme": "6G / Wi-Fi 7 / 邊緣 AI",
        "description": "全球最大通訊展。聚焦非地面網路 (NTN) 與終端 AI 應用。觀察網通設備升級潮。",
        "supply_chain": [
            {"us_symbol": "QCOM", "us_name": "高通", "tw_tickers": ["2454", "2379", "3105"], "tw_sector": "IC 設計"},
            {"us_symbol": "AVGO", "us_name": "博通", "tw_tickers": ["5388", "6285"], "tw_sector": "網通設備"}
        ]
    },
    {
        "event": "NVIDIA GTC 大會 2026",
        "date": "2026-03-18",
        "end_date": "2026-03-21",
        "theme": "Blackwell Ultra / Rubin GPU",
        "description": "AI 界的伍茲塔克。黃仁勳將揭曉下一代 AI 推論晶片與 Sovereign AI 戰略。",
        "supply_chain": [
            {"us_symbol": "NVDA", "us_name": "輝達", "tw_tickers": ["2330", "2382", "3231", "6669"], "tw_sector": "AI 伺服器"},
            {"us_symbol": "SMCI", "us_name": "美超微", "tw_tickers": ["2376", "2324"], "tw_sector": "伺服器代工"}
        ]
    },
    {
        "event": "Google I/O 開發者大會",
        "date": "2026-05-14",
        "end_date": "2026-05-15",
        "theme": "Gemini 2.0 / Android 17",
        "description": "Google 軟體火力展示。關注 Pixel 手機的 AI 整合與各種 Agent 應用。",
        "supply_chain": [
            {"us_symbol": "GOOGL", "us_name": "Alphabet", "tw_tickers": ["2357", "2498"], "tw_sector": "安卓生態系"}
        ]
    },
    {
        "event": "Computex 台北國際電腦展",
        "date": "2026-06-02",
        "end_date": "2026-06-06",
        "theme": "AI PC / Copilot+",
        "description": "台灣主場優勢。AMD, Intel, Qualcomm 執行長將齊聚台北，發布 AI PC 新品。",
        "supply_chain": [
            {"us_symbol": "MSFT", "us_name": "微軟", "tw_tickers": ["2353", "2357", "2301"], "tw_sector": "AI PC 供應鏈"},
            {"us_symbol": "AMD", "us_name": "超微", "tw_tickers": ["2330", "3711"], "tw_sector": "HPC 運算"}
        ]
    },
    {
        "event": "Apple WWDC 開發者大會",
        "date": "2026-06-10",
        "end_date": "2026-06-14",
        "theme": "iOS 20 / Siri LLM",
        "description": "蘋果 AI 戰略關鍵時刻。預期發布裝置端 (On-device) AI 新功能。",
        "supply_chain": [
            {"us_symbol": "AAPL", "us_name": "蘋果", "tw_tickers": ["2317", "3008", "4938"], "tw_sector": "蘋果供應鏈"}
        ]
    }
]

def fetch_prices(tickers):
    """
    Batch fetch prices for US and TW stocks.
    Returns: { 'NVDA': {price: 1200, change: 2.5}, '2330': {...} }
    """
    print(f"   -> Fetching prices for {len(tickers)} assets...")
    
    # Separate US and TW for better batching if needed, but yf handles mix well usually.
    # TW tickers need .TW or .TWO suffix. The calendar has raw codes.
    
    yf_tickers = []
    mapping = {} # "2330" -> "2330.TW"
    
    for t in tickers:
        if t.isdigit(): # Taiwan Stock
            # Simple logic: Try .TW first (Most are TWSE)
            # For production, we should check existing DB, but let's default to .TW
            s = f"{t}.TW"
            yf_tickers.append(s)
            mapping[s] = t
        else: # US Stock
            yf_tickers.append(t)
            mapping[t] = t
            
    try:
        data = yf.Tickers(" ".join(yf_tickers))
        results = {}
        
        for yt in yf_tickers:
            try:
                # yfinance specific handling for Tickers object
                ticker_obj = data.tickers[yt]
                
                # fast_info is often faster/more reliable for current price
                fast = ticker_obj.fast_info
                price = fast.last_price
                prev = fast.previous_close
                change_pct = ((price - prev) / prev) * 100
                
                clean_ticker = mapping[yt]
                results[clean_ticker] = {
                    "price": round(price, 2),
                    "change": round(change_pct, 2)
                }
            except:
                # Fallback or error
                clean_ticker = mapping[yt]
                results[clean_ticker] = {"price": 0, "change": 0}
                
        return results
    except Exception as e:
        print(f"   ⚠️ Price fetch failed: {e}")
        return {}

def update_global_intelligence():
    print("🚀 [Global Intel] Starting Update...")
    
    # 1. Filter Events (Show Recent Past 1 Month + Future)
    now = datetime.datetime.now()
    if now.year == 2026: # Trust 2026 time
        current_date = now.date()
    else:
        # Fallback simulation date
        current_date = datetime.date(2026, 2, 5)

    display_events = []
    all_tickers_to_fetch = set()

    for evt in EVENT_CALENDAR:
        evt_date = datetime.datetime.strptime(evt['date'], "%Y-%m-%d").date()
        
        # Logic: Keep if end_date is not older than 30 days ago
        # And start_date is within next 6 months
        days_diff = (evt_date - current_date).days
        
        if days_diff > -30 and days_diff < 180:
            # Determine Status
            status = "Upcoming"
            # Parse end_date for logic
            end_date_obj = datetime.datetime.strptime(evt['end_date'], "%Y-%m-%d").date()
            
            if days_diff <= 0 and (current_date <= end_date_obj):
                status = "Ongoing"
            elif days_diff < 0:
                status = "Finished"
            elif days_diff <= 14:
                status = "Imminent" # Within 2 weeks
            
            evt['status'] = status
            evt['days_to_go'] = days_diff
            display_events.append(evt)
            
            # Collect Tickers
            for group in evt['supply_chain']:
                all_tickers_to_fetch.add(group['us_symbol'])
                for tw in group['tw_tickers']:
                    all_tickers_to_fetch.add(tw)

    # 2. Fetch Market Data
    market_data = fetch_prices(list(all_tickers_to_fetch))

    # 3. Enrich Data
    final_output = []
    for evt in display_events:
        enriched_groups = []
        for group in evt['supply_chain']:
            us_sym = group['us_symbol']
            us_data = market_data.get(us_sym, {"price": 0, "change": 0})
            
            tw_list = []
            for tw_sym in group['tw_tickers']:
                tw_data = market_data.get(tw_sym, {"price": 0, "change": 0})
                
                # Signal Logic
                signal = "Neutral"
                if us_data['change'] > 2.0 and tw_data['change'] < 1.0:
                    signal = "Lagging (Buy?)" # US fly, TW sleep
                elif us_data['change'] > 2.0 and tw_data['change'] > 2.0:
                    signal = "Sympathy Rally"
                elif us_data['change'] < -2.0:
                    signal = "Risk Alert"
                    
                tw_list.append({
                    "ticker": tw_sym,
                    "price": tw_data['price'],
                    "change": tw_data['change'],
                    "signal": signal
                })
            
            enriched_groups.append({
                "us_stock": {
                    "symbol": us_sym,
                    "name": group['us_name'],
                    "price": us_data['price'],
                    "change": us_data['change']
                },
                "tw_sector": group['tw_sector'],
                "tw_stocks": tw_list
            })
        
        # Create a new dict to avoid modifying the constant if rerun
        new_evt = evt.copy()
        new_evt['chains'] = enriched_groups
        if 'supply_chain' in new_evt: del new_evt['supply_chain'] 
        final_output.append(new_evt)

    # 4. Save
    output = {
        "last_updated": now.strftime("%Y-%m-%d %H:%M"),
        "events": final_output
    }
    
    with open(JSON_PATH, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ [Global Intel] Saved {len(final_output)} events to {JSON_PATH}")

if __name__ == "__main__":
    update_global_intelligence()
