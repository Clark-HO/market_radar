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
        "date": "2026-02"
    }
    chips = {
        "foreign_net": 12500,
        "trust_net": 3500,
        "analysis": "Accumulating"
    }
    
    # 3. Assemble Data Object
    item_data = {
        "stock_id": stock_id,
        "stock_name": name,
        "valuation": {
            "stock_id": stock_id,
            "current_pe": round(float(pe), 2),
            "sector_pe": 20.0,
            "status": "High Premium",
            "price": price
        },
        "revenue": revenue,
        "chips": chips
    }
    
    # 4. Generate AI Report
    print("🤖 Generating AI Report (Gemini 2.5)...")
    try:
        ai_data = generate_ai_report(item_data)
        item_data['ai_analysis'] = ai_data
        print(f"✅ AI Success: {ai_data['verdict']} (Score: {ai_data['score']})")
    except Exception as e:
        print(f"❌ AI Failed: {e}")
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
