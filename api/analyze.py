from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
import requests
import re
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')

    def _send_json(self, data, status=200):
        self.send_response(status)
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _generate_rule_based_fallback(self, stock_id, current_price, pe_val, current_change):
        """當外部 AI API 故障、超時或無效 Key 時的離線安全分析，確保前端 UI 不崩潰"""
        try:
            pe_num = float(pe_val) if pe_val not in ["N/A", "未知", ""] else 20.0
        except:
            pe_num = 20.0
            
        try:
            price_num = float(current_price) if current_price not in ["N/A", "未知", ""] else 100.0
        except:
            price_num = 100.0

        if pe_num < 15:
            verdict = "謹慎看多"
            score = 78
            bias = "本益比處於相對低檔區間，具備價值投資安全邊際。"
        elif pe_num > 28:
            verdict = "中立觀望"
            score = 62
            bias = "目前評價已偏高，成長預期已大致反映於股價中。"
        else:
            verdict = "中立偏多"
            score = 70
            bias = "估值落於合理區間，重點觀察主力買賣超籌碼流向。"

        buy_low = round(price_num * 0.94, 1)
        buy_high = round(price_num * 0.97, 1)
        sell_low = round(price_num * 1.06, 1)
        sell_high = round(price_num * 1.10, 1)

        content = (
            f"#### 🎯 核心邏輯剖析\n"
            f"- **估值與成長對決**: 目標股價現報 {current_price}，本益比約 {pe_val}。{bias}\n"
            f"- **籌碼博弈解讀**: 今日漲跌為 {current_change}，建議密切觀察投信與外資近期買賣超是否出現同步轉折。\n\n"
            f"#### 🔮 實戰預判 & 操作策略\n"
            f"- **走勢預演**: 短線預期在月線上下震盪整理，待量能放大後方有方向性突破。\n"
            f"- **關鍵操作**: 建議拉回 {buy_low}~{buy_high} 逢低分批布局，短線壓力區落於 {sell_low}~{sell_high}。"
        )

        return {
            "buy_price": f"{buy_low} - {buy_high}",
            "sell_price": f"{sell_low} - {sell_high}",
            "score": score,
            "verdict": verdict,
            "report": content,
            "content": content
        }

    def _call_groq(self, prompt, api_key):
        """呼叫免費又極速的 Groq API (Llama 3.3 70B)"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a senior hedge fund portfolio manager. Output strict JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(url, headers=headers, json=data, timeout=12)
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            return json.loads(content)
        return None

    def _call_gemini(self, prompt, api_key):
        """呼叫 Google Gemini API (優先嘗試 2.0-flash，備援 1.5-flash)"""
        models_to_try = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash"
        ]
        
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
        
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=12)
                if resp.status_code == 200:
                    result = resp.json()
                    raw_text = result['candidates'][0]['content']['parts'][0]['text']
                    clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_text)
            except Exception:
                continue
        return None

    def do_GET(self):
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        def get_param(key, default="N/A"):
            return params.get(key, [default])[0]

        stock_id = get_param("stock_id")
        
        if not stock_id or stock_id == "N/A":
            self._send_json({
                "score": 0, "verdict": "Ready", 
                "report": "✅ API 在線中，等待查詢個股代號。"
            })
            return

        # 驗證代號格式 (台股代號通常為 4~6 碼數字或字母)
        if not re.match(r'^[0-9A-Za-z]{2,6}$', stock_id):
            self._send_json({
                "score": 0, "verdict": "Input Error",
                "report": "⚠️ 股票代號格式錯誤，請輸入 4 碼台股代號。"
            }, 400)
            return

        current_price = get_param("price", "未知")
        current_change = get_param("change", "未知")
        pe = get_param("pe", "N/A") 
        
        # 數據清洗
        try:
            if current_price not in ["未知", "N/A"]:
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
            f"### 【即時市場數據】\n"
            f"目標個股代號：{stock_id}\n"
            f"目前股價：{current_price} (最新成交價)\n"
            f"今日漲跌：{current_change}\n"
            f"本益比(PE)：{pe}\n"
            f"\n"
            f"### 輸出格式 (Strict JSON ONLY)：\n"
            f"請務必回傳標準 JSON 物件，**嚴禁**使用 Markdown (```json)，也**嚴禁**包含閒聊文字。格式如下：\n"
            f"{{\n"
            f"  \"buy_price\": \"[數值區間]\",\n"
            f"  \"sell_price\": \"[數值區間]\",\n"
            f"  \"score\": 0-100,\n"
            f"  \"verdict\": \"[強烈看多 / 謹慎看多 / 中立觀望 / 轉弱看空]\",\n" 
            f"  \"content\": \"[完整分析]\"\n"
            f"}}\n"
            f"\n"
            f"### Content 欄位內容指引：\n"
            f"在 'content' 欄位中包含以下段落：\n"
            f"#### 🎯 核心邏輯剖析\n"
            f"- **估值與成長對決**: (分析目前股價 {current_price} 是否合理，PEG 觀點)\n"
            f"- **籌碼博弈解讀**: (分析外資與主力心態，是吃貨還是出貨)\n"
            f"\n"
            f"#### 🔮 實戰預判 & 操作策略\n"
            f"- **走勢預演**: (預測下週走勢預判)\n"
            f"- **關鍵操作**: (給出具體進出建議)\n"
        )

        ai_data = None
        
        # 1. 優先嘗試 Groq (若有配置 GROQ_API_KEY)
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            try:
                ai_data = self._call_groq(prompt, groq_key)
            except Exception:
                ai_data = None

        # 2. 嘗試 Gemini (若有配置 GEMINI_API_KEY)
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not ai_data and gemini_key:
            try:
                ai_data = self._call_gemini(prompt, gemini_key)
            except Exception:
                ai_data = None

        # 3. 若外部 AI 均失敗或無 Key，自動觸發規則引擎 Fallback (確保畫面絕對不崩潰)
        if not ai_data:
            ai_data = self._generate_rule_based_fallback(stock_id, current_price, pe, current_change)

        if 'report' not in ai_data and 'content' in ai_data:
            ai_data['report'] = ai_data['content']
            
        self._send_json(ai_data)
