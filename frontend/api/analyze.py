from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
import requests
import re

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Setup Headers (CORS)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()

        # 2. Parse Query Params
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        def get_param(key, default="N/A"):
            return params.get(key, [default])[0]

        stock_id = get_param("stock_id")
        
        # 3. Validation & Setup API Key
        # [CRITICAL FIX] Define api_key BEFORE usage
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            self.wfile.write(json.dumps({
                "score": 0, "verdict": "Config Error", 
                "report": "❌ GEMINI_API_KEY is missing."
            }).encode('utf-8'))
            return
            
        if not stock_id or stock_id == "N/A":
             self.wfile.write(json.dumps({
                "score": 0, "verdict": "Ready", 
                "report": "✅ API Online. Waiting for stock_id."
            }).encode('utf-8'))
             return

        # 4. Construct Prompt (Preserving Persona for UI)
        stock_name = get_param("stock_name", stock_id)
        pe = get_param("pe")
        change = get_param("change")
        
        prompt = f"""
        你現在是華爾街頂尖避險基金的資深操盤手。
        請對 {stock_name} ({stock_id}) 進行 AI 智能診斷。
        數據: PE={pe}, MoM={change}% 
        
        請以避險基金經理語氣輸出 Markdown 報告：
        1. **AI 綜合戰力** (0-100)
        2. **趨勢訊號** (強烈看多/看空/觀望)
        3. 分析點評
        """

        try:
            # 5. Call Gemini via Raw HTTP (No SDK)
            # [User Request] Use gemini-2.0-flash (Stable, Better Quota)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7
                }
            }
            
            # The lightweight request
            response = requests.post(url, headers=headers, json=data)
            
            # Check non-200 status
            if response.status_code != 200:
                self.wfile.write(json.dumps({
                    "score": 0, "verdict": "API Error", 
                    "report": f"⚠️ Google Cloud Error: {response.text}"
                }).encode('utf-8'))
                return

            result = response.json()
            content = ""
            try:
                content = result['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                error_detail = result.get('error', {}).get('message', 'Unknown Error')
                raise Exception(f"Google Response Parse Error: {error_detail}")

            # 6. Parse Result (Robust Regex) for Frontend UI
            score_match = re.search(r'AI 綜合戰力\D*(\d+)', content)
            score = int(score_match.group(1)) if score_match else 75
            
            verdict_match = re.search(r'趨勢訊號.*?\*\*([^*]+)\*\*', content)
            verdict = verdict_match.group(1).strip() if verdict_match else "AI 分析完成"

            # 7. Return Result
            out_json = {
                "score": score,
                "verdict": verdict,
                "report": content,
                "analysis": content # Legacy support
            }
            self.wfile.write(json.dumps(out_json).encode('utf-8'))

        except Exception as e:
            self.wfile.write(json.dumps({
                "score": 0, "verdict": "Runtime Error", 
                "report": f"⚠️ Backend Exception: {str(e)}"
            }).encode('utf-8'))
