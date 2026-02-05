import json
import math
import os

# Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "frontend", "public", "stock_data.json")

print(f"Reading {FILE_PATH}...")

try:
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        # Read raw content
        content = f.read()

    # Replace invalid JSON tokens
    # Note: Python's json.dump(allow_nan=True) produces NaN, Infinity, -Infinity
    # We will replace them textually to be safe, or use json.loads with parse_constant
    
    fixed_content = content.replace(": NaN", ": 0").replace(": Infinity", ": 0").replace(": -Infinity", ": 0")
    
    # Verify it parses
    data = json.loads(fixed_content)
    print(f"✅ Successfully parsed {len(data)} items.")
    
    # Save back
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print("✅ Fixed JSON saved.")

except Exception as e:
    print(f"❌ Error: {e}")
