import os
from backend.analysis import generate_ai_report, generate_rule_based_report
from dotenv import load_dotenv

load_dotenv()

# Mock Data (TSMC)
mock_data = {
    "stock_id": "2330",
    "stock_name": "台積電",
    "valuation": {
        "current_pe": 28.5,
        "sector_pe": 20.0
    },
    "revenue": {
        "mom": 5.2,
        "yoy": 35.5
    },
    "chips": {
        "foreign_net": 12500,
        "trust_net": 3500,
        "analysis": "Accumulating"
    }
}

print("🚀 Testing AI Report Generation...")
print(f"API Key Present: {'Yes' if os.getenv('GEMINI_API_KEY') else 'No'}")

try:
    result = generate_ai_report(mock_data)
    print("\n--- Result ---")
    print(f"Score: {result['score']}")
    print(f"Verdict: {result['verdict']}")
    print("\n--- Report Content ---")
    print(result['report'][:500] + "...") # Preview
    
except Exception as e:
    print(f"❌ Error: {e}")
