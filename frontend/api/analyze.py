from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
import re

# [Debug Wrapper] Capture Import Errors
# This prevents 500 crashes if dependencies differ on Vercel
import_error = None
client = None

try:
    from google import genai
    from google.genai import types
    
    # Initialize Client
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Client Init Error: {e}")
except ImportError as e:
    import_error = f"Import Error: {e}"
except Exception as e:
    import_error = f"Setup Error: {e}"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Parse Query Params
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        # Helper string cleaner
        def get_param(key, default="N/A"):
            return params.get(key, [default])[0]

        stock_id = get_param("stock_id")
        
        # 2. Setup Headers (CORS is crucial)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*') # Allow frontend access
        self.end_headers()

        # 3. Check Critical Failures (Before AI Logic)
        if import_error:
             self.wfile.write(json.dumps({
                "score": 0, "verdict": "Deploy Error", 
                "report": f"⚠️ Server Import Failed: {import_error}. Check requirements.txt."
            }).encode('utf-8'))
             return

        if not client:
            self.wfile.write(json.dumps({
                "score": 0, "verdict": "Config Error", 
                "report": "❌ GEMINI_API_KEY is missing in Vercel Environment Variables."
            }).encode('utf-8'))
            return
            
        # 4. Construct Prompt
        # Verify valid stock_id
        if not stock_id or stock_id == "N/A":
             self.wfile.write(json.dumps({
                "score": 0, "verdict": "Ready", 
                "report": "✅ API Online. Waiting for stock_id."
            }).encode('utf-8'))
             return

        stock_name = get_param("stock_name", stock_id)
        
        prompt = f"""
        你現在是華爾街頂尖避險基金的資深操盤手。
        請對 {stock_name} ({stock_id}) 進行 AI 智能診斷。
        數據: PE={get_param("pe")}, MoM={get_param("change")}% 
        
        請以避險基金經理語氣輸出 Markdown 報告：
        1. **AI 綜合戰力** (0-100)
        2. **趨勢訊號** (強烈看多/看空/觀望)
        3. 分析點評
        """

        try:
            # 5. Call Gemini
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            content = response.text
            
            # 6. Parse Result (Robust Regex)
            score_match = re.search(r'AI 綜合戰力\D*(\d+)', content)
            score = int(score_match.group(1)) if score_match else 75
            
            verdict_match = re.search(r'趨勢訊號.*?\*\*([^*]+)\*\*', content)
            verdict = verdict_match.group(1).strip() if verdict_match else "AI 分析完成"

            # 7. Return Result
            out_json = {
                "score": score,
                "verdict": verdict,
                "report": content
            }
            self.wfile.write(json.dumps(out_json).encode('utf-8'))

        except Exception as e:
            self.wfile.write(json.dumps({
                "score": 0, "verdict": "Runtime Error", 
                "report": f"⚠️ Runtime Exception: {str(e)}"
            }).encode('utf-8'))
