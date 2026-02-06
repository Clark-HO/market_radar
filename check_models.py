from google import genai
import os

# 記得確認這裡會抓到你的 API KEY
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("🔍 Scanning available models for your API Key...")

try:
    # 列出所有模型
    for model in client.models.list(config={"page_size": 100}):
        # 只顯示名字裡有 "flash" 的，比較好找
        if "flash" in model.name or "pro" in model.name:
            print(f"✅ Found: {model.name}")
            
except Exception as e:
    print(f"❌ Error: {e}")