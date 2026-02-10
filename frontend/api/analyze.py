from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
import requests
import re
from datetime import datetime

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
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # ✅ NEW PROMPT: Force Numerical Buy/Sell Targets
        prompt = (
            f"今天是 {today}。請擔任一位嚴格的技術分析師，分析台股代號 {stock_name} ({stock_id})。"
            f"數據: PE={pe}, MoM={change}%。\n"
            f"請務必回傳 JSON 格式，包含以下四個欄位："
            f'1. "buy_price": 即使目前不建議買進，也請根據『支撐位』給出一個具體的『數字區間』(例如: "23.5 - 24.0")，絕對不要寫『觀望』或文字。'
            f'2. "sell_price": 請根據『壓力位』給出一個具體的『數字區間』(例如: "28.0 - 28.5")。'
            f'3. "score": 0-100(數字)。'
            f'4. "verdict": "趨勢訊號(強烈看多/看空/觀望)"。'
            f'5. "content": 這裡才寫你的完整文字分析，包含趨勢判斷與建議。'
            f"注意：buy_price 和 sell_price 欄位只能包含數字和連字號，不要有其他文字。"
        )

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
            raw_text = ""
            try:
                raw_text = result['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                error_detail = result.get('error', {}).get('message', 'Unknown Error')
                self.wfile.write(json.dumps({"error": str(error_detail)}).encode('utf-8'))
                return

            # ✅ Parse JSON from AI Response
            # Clean up potential Markdown wrappers (```json ... ```)
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            try:
                ai_data = json.loads(clean_text)
                # Map 'content' to 'report' for frontend compatibility if needed, 
                # but frontend likely uses 'content' or 'report'. 
                # StockScan.jsx uses 'report'. Let's ensure 'report' exists.
                if 'report' not in ai_data and 'content' in ai_data:
                    ai_data['report'] = ai_data['content']
                
                # Send structured data to frontend
                self.wfile.write(json.dumps(ai_data).encode('utf-8'))
            except json.JSONDecodeError:
                # Fallback if AI fails to give JSON
                fallback = {
                    "buy_price": "N/A", 
                    "sell_price": "N/A", 
                    "score": 75,
                    "verdict": "AI 分析完成",
                    "report": raw_text
                }
                self.wfile.write(json.dumps(fallback).encode('utf-8'))

        except Exception as e:
            self.wfile.write(json.dumps({
                "score": 0, "verdict": "Runtime Error", 
                "report": f"⚠️ Backend Exception: {str(e)}"
            }).encode('utf-8'))
