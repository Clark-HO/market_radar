from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import re
from google import genai
from google.genai import types

# Initialize Gemini Client (Outside handler for potential caching)
# Note: Vercel might re-init, which is fine.
api_key = os.environ.get("GEMINI_API_KEY")
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except: pass

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Parse Query Params
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        # Helper to safely get param
        def get_param(key, default="N/A"):
            return params.get(key, [default])[0]

        stock_id = get_param("stock_id")
        stock_name = get_param("stock_name", stock_id)
        
        # 2. Setup Headers (CORS & Content-Type)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        # Allow CORS for local dev and production
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()

        # 3. Check API Key
        if not client:
            self.wfile.write(json.dumps({
                "score": 0, 
                "verdict": "Configuration Error", 
                "report": "❌ API Key Missing on Server."
            }).encode('utf-8'))
            return

        # 4. Construct Data Context
        # Using raw params from URL to avoid DB lookups ensuring speed
        prompt = f"""
        你現在是華爾街頂尖避險基金的資深操盤手，風格犀利、邏輯嚴謹。
        請根據以下數據，對 {stock_name} ({stock_id}) 進行 AI 智能診斷。

        [基本面]
        - 本益比: {get_param("pe")}x (同業: {get_param("sector_pe")}x)
        - 營收動能: 月增 {get_param("mom")}% / 年增 {get_param("yoy")}%

        [籌碼面]
        - 外資: {get_param("foreign")}張
        - 投信: {get_param("trust")}張
        - 主力動向: {get_param("analysis")}

        請直接輸出 Markdown 報告，包含：
        1. **AI 綜合戰力** (0-100分)
        2. **趨勢訊號** (強烈看多/謹慎看多/觀望/看空)
        3. **核心邏輯剖析**:
           - 估值與成長性 (PEG觀點)
           - 籌碼博弈 (土洋是否合流?)
        4. **實戰操作建議** (具體進出策略)

        請保持「避險基金報告」的專業語氣，果斷且直擊重點。
        """

        try:
            # 5. Call Gemini
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                )
            )
            content = response.text
            
            # 6. Parse Result (Simple Regex)
            score_match = re.search(r'AI 綜合戰力\D*(\d+)', content)
            score = int(score_match.group(1)) if score_match else 75
            
            verdict_match = re.search(r'趨勢訊號.*?\*\*([^*]+)\*\*', content)
            verdict = verdict_match.group(1).strip() if verdict_match else "AI 分析完成"

            # 7. Return JSON
            out_json = {
                "score": score,
                "verdict": verdict,
                "report": content
            }
            self.wfile.write(json.dumps(out_json).encode('utf-8'))

        except Exception as e:
            # Error Handling
            self.wfile.write(json.dumps({
                "score": 0,
                "verdict": "System Error",
                "report": f"⚠️ AI Analysis Failed: {str(e)}"
            }).encode('utf-8'))
