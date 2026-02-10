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
            f"現在是真實世界日期：{today}。請你擔任一位『講求籌碼與技術面的台股資深分析師』，針對台股代號 {stock_id} 進行分析。"
            f"\n\n"
            f"### 執行指令：\n"
            f"請運用你的金融知識庫，模擬分析該股的技術面與籌碼面邏輯（無需即時連網，請根據線型型態判斷）。\n"
            f"\n"
            f"### 輸出格式 (Strict JSON ONLY)：\n"
            f"請務必回傳一個標準的 JSON 物件，**嚴禁**使用 Markdown (```json)，也**嚴禁**包含任何開頭或結尾的閒聊文字。JSON 格式如下：\n"
            f"{{\n"
            f"  \"buy_price\": \"[數值區間]\",  // 請根據技術支撐位 (均線/前低) 給出建議買進區間 (例如: '23.5 - 24.0')，請給出具體數字。\n"
            f"  \"sell_price\": \"[數值區間]\", // 請根據壓力位 (前高/套牢區) 給出建議賣出區間 (例如: '28.0 - 28.5')。\n"
            f"  \"score\": 0-100, // 務必包含此欄位 (數字)\n"
            f"  \"verdict\": \"趨勢訊號\", // 務必包含此欄位 (例如: '強烈看多')\n" 
            f"  \"content\": \"[完整分析]\"     // 請以條列式分析：1. 位階判斷。2. 籌碼邏輯(模擬)。3. 操作建議。\n"
            f"}}\n"
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
