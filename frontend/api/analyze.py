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
                f"現在是真實世界日期：{today}。請你擔任一位『講求籌碼與技術面的台股資深分析師』，針對台股代號 {stock_id} 進行即時掃描。"
                f"\n\n"
                f"### 執行步驟 (Mandatory Action)：\n"
                f"1. **SEARCH (必要)**：請務必使用 Google Search 搜尋該股『今日收盤價』、『最近 3 日三大法人買賣超』、『最新單月營收年增率』以及『近期重大新聞』。\n"
                f"2. **ANALYZE (分析)**：\n"
                f"   - 判斷目前位階是『高基期』還是『低基期』。\n"
                f"   - 觀察是否有『主力出貨』或『散戶接刀』的跡象。\n"
                f"3. **CALCULATE (計算)**：\n"
                f"   - 找出『支撐位』(均線或前波低點) 作為 buy_price。\n"
                f"   - 找出『壓力位』(套牢區或前波高點) 作為 sell_price。\n"
                f"\n\n"
                f"### 輸出格式 (Strict JSON)：\n"
                f"請**僅**回傳一個標準的 JSON 物件，不要有 Markdown 標記 (```json) 或其他廢話。JSON 必須包含以下三個欄位：\n"
                f"{{\n"
                f"  \"buy_price\": \"[數值區間]\",  // 即使目前看空，也要給出下方最強支撐區間 (例如: '23.5 - 24.0')，嚴禁寫中文或觀望。\n"
                f"  \"sell_price\": \"[數值區間]\", // 上方壓力區間 (例如: '28.0 - 28.5')，嚴禁寫中文。\n"
                f"  \"content\": \"[完整分析]\"     // 請用『條列式』分析：1. 位階判斷 (高/低基期)。2. 籌碼動向 (外資/投信是買是賣)。3. 操作建議 (短線/波段策略)。\n"
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
