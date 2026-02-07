import os
import requests
import json

# 設定你的 API Key (如果環境變數沒抓到，請暫時直接貼在這裡測試)
API_KEY = os.environ.get("GEMINI_API_KEY") 
API_KEY = "AIzaSyCMbyVS1myWQHlSTSFbmNJI8jVb67BIxjw"

def list_available_models():
    if not API_KEY:
        print("❌ 錯誤: 找不到 GEMINI_API_KEY")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    
    try:
        print(f"🔍 正在向 Google 查詢可用模型清單...")
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ 查詢失敗 (Status {response.status_code}):")
            print(response.text)
            return

        data = response.json()
        print("\n✅ 查詢成功！以下是您可以使用的模型名稱：")
        print("="*60)
        
        # 篩選出 generateContent 類型的模型
        valid_models = []
        for model in data.get('models', []):
            name = model.get('name', '').replace('models/', '')
            methods = model.get('supportedGenerationMethods', [])
            
            if 'generateContent' in methods:
                print(f"👉 {name:<30} (支援生成文字)")
                valid_models.append(name)
        
        print("="*60)
        
        # 智慧推薦
        print("\n💡 推薦您使用的替代模型：")
        if "gemini-2.0-flash-lite" in str(valid_models):
             print("🌟 gemini-2.0-flash-lite (推測是 1.5 Flash 的繼任者，高額度)")
        elif "gemini-2.0-flash" in str(valid_models):
             print("🌟 gemini-2.0-flash (標準版)")
        else:
             print("❓ 請從上方清單中挑選一個含有 'flash' 字眼的最新版本")

    except Exception as e:
        print(f"❌ 發生例外錯誤: {e}")

if __name__ == "__main__":
    list_available_models()