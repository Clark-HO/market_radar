import yfinance as yf
import json
import os
import datetime
import copy
import requests
from dateutil.relativedelta import relativedelta
import time

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "frontend", "public")
if not os.path.exists(PUBLIC_DIR):
    os.makedirs(PUBLIC_DIR)

JSON_PATH = os.path.join(PUBLIC_DIR, "global_data.json")


def load_events():
    """Load event calendar from external JSON file."""
    events_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.json")
    if not os.path.exists(events_path):
        print(f"⚠️ Events file not found: {events_path}")
        return []
    with open(events_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def fetch_otc_tickers():
    """Fetch all OTC (TPEx) stock codes from the TPEx open data API."""
    try:
        url = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        otc_set = {item.get('SecuritiesCompanyCode', '') for item in data if item.get('SecuritiesCompanyCode')}
        print(f"   ✅ Loaded {len(otc_set)} OTC tickers from TPEx API")
        return otc_set
    except Exception as e:
        print(f"   ⚠️ Failed to fetch OTC tickers: {e}. Defaulting to .TW for all.")
        return set()


def fetch_prices(tickers, otc_tickers=None):
    """
    Batch fetch prices for US and TW stocks.
    Returns: { 'NVDA': {price: 1200, change: 2.5}, '2330': {...} }
    """
    if otc_tickers is None:
        otc_tickers = set()
    print(f"   -> Fetching prices for {len(tickers)} assets...")
    
    yf_tickers = []
    mapping = {}
    
    for t in tickers:
        if t.isdigit():  # Taiwan Stock
            suffix = ".TWO" if t in otc_tickers else ".TW"
            s = f"{t}{suffix}"
            yf_tickers.append(s)
            mapping[s] = t
        else:  # US Stock
            yf_tickers.append(t)
            mapping[t] = t
            
    try:
        data = yf.Tickers(" ".join(yf_tickers))
        results = {}
        
        for yt in yf_tickers:
            try:
                ticker_obj = data.tickers[yt]
                fast = ticker_obj.fast_info
                price = fast.last_price
                prev = fast.previous_close
                
                if prev and prev > 0:
                    change_pct = ((price - prev) / prev) * 100
                else:
                    change_pct = 0
                
                clean_ticker = mapping[yt]
                results[clean_ticker] = {
                    "price": round(price, 2),
                    "change": round(change_pct, 2)
                }
            except Exception:
                clean_ticker = mapping[yt]
                results[clean_ticker] = {"price": 0, "change": 0}
                
        return results
    except Exception as e:
        print(f"   ⚠️ Price fetch failed: {e}")
        return {}


def update_global_intelligence():
    print("🚀 [Global Intel] Starting Update...")
    
    # Load events from external JSON
    event_calendar = load_events()
    if not event_calendar:
        print("⚠️ No events loaded. Skipping Global Intel update.")
        return
    
    # Fetch OTC tickers for proper suffix detection
    otc_tickers = fetch_otc_tickers()
    
    # Filter Events
    now = datetime.datetime.now()
    current_date = now.date()

    display_events = []
    all_tickers_to_fetch = set()

    for evt in event_calendar:
        evt_date = datetime.datetime.strptime(evt['date'], "%Y-%m-%d").date()
        days_diff = (evt_date - current_date).days
        
        if days_diff > -30 and days_diff < 180:
            # Determine Status
            status = "Upcoming"
            end_date_str = evt.get('end_date', evt['date'])
            end_date_obj = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            if days_diff <= 0 and (current_date <= end_date_obj):
                status = "Ongoing"
            elif days_diff < 0:
                status = "Finished"
            elif days_diff <= 14:
                status = "Imminent"
            
            # Use deepcopy to avoid mutating the source data
            evt_copy = copy.deepcopy(evt)
            evt_copy['status'] = status
            evt_copy['days_to_go'] = days_diff
            display_events.append(evt_copy)
            
            # Collect Tickers
            for group in evt.get('supply_chain', []):
                all_tickers_to_fetch.add(group['us_symbol'])
                for tw in group['tw_tickers']:
                    all_tickers_to_fetch.add(tw)

    # Fetch Market Data (with OTC awareness)
    market_data = fetch_prices(list(all_tickers_to_fetch), otc_tickers)

    # Enrich Data
    final_output = []
    for evt in display_events:
        enriched_groups = []
        for group in evt.get('supply_chain', []):
            us_sym = group['us_symbol']
            us_data = market_data.get(us_sym, {"price": 0, "change": 0})
            
            tw_list = []
            for tw_sym in group['tw_tickers']:
                tw_data = market_data.get(tw_sym, {"price": 0, "change": 0})
                
                signal = "Neutral"
                if us_data['change'] > 2.0 and tw_data['change'] < 1.0:
                    signal = "Lagging (Buy?)"
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
        
        evt['chains'] = enriched_groups
        if 'supply_chain' in evt:
            del evt['supply_chain']
        final_output.append(evt)

    # Save (atomic write)
    output = {
        "last_updated": now.strftime("%Y-%m-%d %H:%M"),
        "events": final_output
    }
    
    tmp_path = JSON_PATH + '.tmp'
    with open(tmp_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, JSON_PATH)
    
    print(f"✅ [Global Intel] Saved {len(final_output)} events to {JSON_PATH}")


if __name__ == "__main__":
    update_global_intelligence()
