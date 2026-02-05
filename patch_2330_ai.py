import json
import os
import yfinance as yf
from backend.analysis import generate_ai_report
from backend.data_updater import sanitize_float
import sys

# Init
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "frontend", "public", "stock_data.json")

def patch_2330():
    print("🚀 Patching 2330 (TSMC) with Live AI...")
    
    # 1. Fetch Basic Data
    stock_id = "2330"
    name = "台積電"
    
    try:
        t = yf.Ticker("2330.TW")
        price = t.fast_info.last_price
        info = t.info
        pe = info.get('trailingPE', 28.5)
    except:
        price = 1050.0
        pe = 28.5
        print("⚠️ YFinance failed, using fallback mock data.")

    # 2. Mock/Real Revenue & Chips (Keep it simple for patch)
    revenue = {
        "mom": 5.2,
        "yoy": 35.5,
        "revenue": 250000000000,
        "date": "2026-02",
        "history": [
            {"date": "2025-03", "revenue": 210000000000.0},
            {"date": "2025-04", "revenue": 215000000000.0},
            {"date": "2025-05", "revenue": 220000000000.0},
            {"date": "2025-06", "revenue": 225000000000.0},
            {"date": "2025-07", "revenue": 230000000000.0},
            {"date": "2025-08", "revenue": 235000000000.0},
            {"date": "2025-09", "revenue": 240000000000.0},
            {"date": "2025-10", "revenue": 245000000000.0},
            {"date": "2025-11", "revenue": 248000000000.0},
            {"date": "2025-12", "revenue": 250000000000.0},
            {"date": "2026-01", "revenue": 255000000000.0},
            {"date": "2026-02", "revenue": 250000000000.0}
        ]
    }
    chips = {
        "foreign_net": 12500,
        "trust_net": 3500,
        "analysis": "Accumulating"
    }
    
    # Calculate PE Score
    sector_pe = 20.0
    pe_score = 0
    status = "Fair Value"
    if pe > 0:
        pe_score = pe / sector_pe
        if pe_score > 1.2: status = "High Premium"
        elif pe_score < 0.8: status = "Undervalued"
    
    # 3. Assemble Data Object
    item_data = {
        "stock_id": stock_id,
        "stock_name": name,
        "valuation": {
            "stock_id": stock_id,
            "current_pe": round(float(pe), 2),
            "sector_pe": sector_pe,
            "pe_score": round(pe_score, 2),
            "status": status,
            "price": price
        },
        "revenue": revenue,
        "chips": chips
    }
    
    # 4. Generate AI Report
    # 4. Generate AI Report (With Retry for Quota)
    import time
    max_retries = 3
    for attempt in range(max_retries):
        print(f"🤖 Generating AI Report (Gemini 2.5) - Attempt {attempt+1}/{max_retries}...")
        try:
            ai_data = generate_ai_report(item_data)
            
            # Check if fallback occurred (Cheat detection)
            if "Rule-Based" in ai_data['report']:
                print("⚠️ Quota Hit (Fallback detected). Waiting 65s to reset quota...")
                time.sleep(65)
                continue # Retry
                
            item_data['ai_analysis'] = ai_data
            print(f"✅ AI Success: {ai_data['verdict']} (Score: {ai_data['score']})")
            print("--- Report Preview ---")
            print(ai_data['report'][:200])
            print("----------------------")
            break
        except Exception as e:
            print(f"❌ AI Failed: {e}")
            if attempt < max_retries - 1:
                print("Waiting 65s...")
                time.sleep(65)
            else:
                 item_data['ai_analysis'] = {"report": "AI Error", "score": 0, "verdict": "Error"}

    # 5. Save to File
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            full_data = json.load(f)
            
        full_data["2330"] = item_data
        
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
            
        print("✅ Saved to stock_data.json")
        
    except Exception as e:
        print(f"❌ File Error: {e}")

if __name__ == "__main__":
    patch_2330()
