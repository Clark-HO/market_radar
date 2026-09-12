from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
import requests
import re
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _send_json(self, data, status=200):
        self.send_response(status)
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # Parse Query Params
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        def get_param(key, default="N/A"):
            return params.get(key, [default])[0]

        stock_id = get_param("stock_id")
        
        # Validate API Key
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            self._send_json({
                "score": 0, "verdict": "Config Error", 
                "report": "❌ API configuration error."
            }, 500)
            return
            
        if not stock_id or stock_id == "N/A":
            self._send_json({
                "score": 0, "verdict": "Ready", 
                "report": "✅ API Online. Waiting for stock_id."
            })
            return

        # Input validation
        if not re.match(r'^[0-9A-Za-z]{2,6}$', stock_id):
            self._send_json({
                "score": 0, "verdict": "Input Error",
                "report": "⚠️ Invalid stock_id format."
            }, 400)
            return

        # Construct Prompt
        current_price = get_param("price", "未知")
        current_change = get_param("change", "未知")
        pe = get_param("pe", "N/A") 
        
        # Sanitize numeric inputs
        try:
            if current_price != "未知" and current_price != "N/A":
                current_price = str(float(current_price))
        except (ValueError, TypeError):
            current_price = "未知"
        try:
            if pe != "N/A":
                pe = str(float(pe))
        except (ValueError, TypeError):
            pe = "N/A"
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        prompt = (
            f"現在是真實世界日期：{today}。請你擔任一位華爾街頂尖避險基金的資深操盤手，風格犀利、邏輯嚴謹，擅長從「籌碼面」與「基本面」的背離中尋找交易機會。"
            f"\n\n"
            f"### 【重要：即時市場數據】\n"
            f"目標個股：{stock_id}\n"
            f"目前股價：{current_price} (這是最新價格，請以此為準)\n"
            f"今日漲跌：{current_change}\n"
            f"本益比(PE)：{pe}\n"
            f"\n"
            f"### 執行指令：\n"
            f"請忽略你記憶中的舊股價，嚴格根據上述『目前股價 {current_price}』進行判斷。\n"
            f"請運用你的金融知識庫，模擬分析該股的技術面與籌碼面邏輯。\n"
            f"\n"
            f"### 輸出格式 (Strict JSON ONLY)：\n"
            f"請務必回傳一個標準的 JSON 物件，**嚴禁**使用 Markdown (```json)，也**嚴禁**包含閒聊文字。JSON 格式如下：\n"
            f"{{\n"
            f"  \"buy_price\": \"[數值區間]\",\n"
            f"  \"sell_price\": \"[數值區間]\",\n"
            f"  \"score\": 0-100,\n"
            f"  \"verdict\": \"[強烈看多 / 謹慎看多 / 中立觀望 / 轉弱看空]\",\n" 
            f"  \"content\": \"[完整分析]\"\n"
            f"}}\n"
            f"\n"
            f"### Content 欄位撰寫指引：\n"
            f"在 JSON 的 'content' 欄位中，請包含以下兩個段落 (語氣要果斷)：\n"
            f"#### 🎯 核心邏輯剖析\n"
            f"- **估值與成長對決**: (分析目前股價 {current_price} 是否合理，PEG 觀點)\n"
            f"- **籌碼博弈解讀**: (分析外資與主力心態，是吃貨還是出貨)\n"
            f"\n"
            f"#### 🔮 實戰預判 & 操作策略\n"
            f"- **走勢預演**: (預測下週走勢)\n"
            f"- **關鍵操作**: (給出具體進出建議)\n"
        )

        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': api_key
            }
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=15)
            
            if response.status_code != 200:
                self._send_json({
                    "score": 0, "verdict": "API Error", 
                    "report": "⚠️ AI 服務暫時不可用，請稍後再試。"
                }, 502)
                return

            result = response.json()
            raw_text = ""
            try:
                raw_text = result['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                self._send_json({
                    "score": 0, "verdict": "Parse Error",
                    "report": "⚠️ AI 回應格式異常，請重試。"
                }, 502)
                return

            # Parse JSON from AI Response
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            try:
                ai_data = json.loads(clean_text)
                if 'report' not in ai_data and 'content' in ai_data:
                    ai_data['report'] = ai_data['content']
                
                self._send_json(ai_data)
            except json.JSONDecodeError:
                fallback = {
                    "buy_price": "N/A", 
                    "sell_price": "N/A", 
                    "score": 75,
                    "verdict": "AI 分析完成",
                    "report": raw_text
                }
                self._send_json(fallback)

        except requests.Timeout:
            self._send_json({
                "score": 0, "verdict": "Timeout",
                "report": "⚠️ AI 分析超時，請稍後再試。"
            }, 504)
        except Exception as e:
            self._send_json({
                "score": 0, "verdict": "Runtime Error", 
                "report": "⚠️ 伺服器內部錯誤，請稍後再試。"
            }, 500)
