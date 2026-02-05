from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os

app = FastAPI(title="Market Radar API (JSON Mode)", version="3.0.0")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "stock_data.json"

def load_data():
    """Reads the JSON file from disk."""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading data file: {e}")
        return {}

@app.on_event("startup")
async def startup_event():
    print("🚀 Server Started [JSON READ-ONLY MODE]")
    # Verify data file exists
    if not os.path.exists(DATA_FILE):
        print("⚠️ Warning: stock_data.json not found. Run 'python backend/data_updater.py' first.")
    else:
        print("✅ stock_data.json detected.")

@app.get("/")
def read_root():
    return {"status": "Online", "mode": "JSON Read-Only"}
from backend.analysis import generate_ai_report

@app.get("/api/stock/{query}/dashboard")
def get_stock_dashboard(query: str):
    # Strictly Read-Only. No logic.
    data_store = load_data()
    
    # 1. Try Direct Match (Stock ID)
    stock_data = data_store.get(query)
    
    # 2. Try Name Search if no ID match (iterate dict)
    if not stock_data:
        for code, info in data_store.items():
            # Exact or Partial Name Match
            name = info.get('stock_name', '')
            if query == name or (len(query) > 1 and query in name):
                stock_data = info
                # Add ID alias to ensure frontend works
                break
    
    if not stock_data:
        return {
            "stock_id": query,
            "valuation": None,
            "revenue": None,
            "note": "No data in stock_data.json"
        }
    
    # On-the-fly AI Analysis
    ai_report = generate_ai_report(stock_data)
        
    return {
        "stock_id": stock_data.get('stock_id'),
        "stock_name": stock_data.get('stock_name', ''),
        "valuation": stock_data.get('valuation'),
        "revenue": stock_data.get('revenue'),
        "chips": stock_data.get('chips'),
        "analysis": ai_report
    }

MACRO_DATA_FILE = "macro_data.json"

@app.get("/api/macro/dashboard")
def get_macro_dashboard():
    """
    Read-Only Endpoint for Macro Data.
    Zero latency, reads pre-computed JSON.
    """
    if not os.path.exists(MACRO_DATA_FILE):
        return {"status": "No Data", "note": "Run python -m backend.scrapers.macro first"}
    
    try:
        with open(MACRO_DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

GLOBAL_DATA_FILE = "global_data.json"

@app.get("/api/global/dashboard")
def get_global_dashboard():
    """
    Read-Only Endpoint for Global Intelligence Data.
    """
    if not os.path.exists(GLOBAL_DATA_FILE):
        return {"status": "No Data", "events": []}
    
    try:
        with open(GLOBAL_DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e), "events": []}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
