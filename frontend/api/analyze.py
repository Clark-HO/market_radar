import google.generativeai as genai
from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
import re

# [Debug Wrapper] Capture Import Errors
import_error = None
model_instance = None

try:
    # Initialize Client (Old SDK Style)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # Pre-initialize model? Or do it in request. 
            # Doing it here checks if SDK loads.
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
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()

        # 3. Check Critical Failures
        if import_error:
             self.wfile.write(json.dumps({
                "score": 0, "verdict": "Deploy Error", 
                "report": f"⚠️ Server Import Failed: {import_error}. Check requirements.txt."
            }).encode('utf-8'))
             return

        if not os.environ.get("GEMINI_API_KEY"):
            self.wfile.write(json.dumps({
                "score": 0, "verdict": "Config Error", 
                "report": "❌ GEMINI_API_KEY is missing in Vercel Environment Variables."
            }).encode('utf-8'))
            return
            
        # 4. Construct Prompt
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
            # 5. Call Gemini (Old SDK)
            # Use the stable 1.5 Flash model
            model_name = "gemini-1.5-flash"
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )
            content = response.text
            
            # 6. Parse Result
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
            error_msg = str(e)
            if "404" in error_msg:
                error_msg += " (Model Not Found - Check Version/Region)"
            elif "429" in error_msg:
                error_msg += " (Quota Exceeded - Rate Limit)"
                
            self.wfile.write(json.dumps({
                "score": 0, "verdict": "Runtime Error", 
                "report": f"⚠️ AI Error: {error_msg}"
            }).encode('utf-8'))
