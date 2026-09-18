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

    def _generate_rule_based_fallback(self, stock_id, current_price, pe_val, sector_pe, foreign_net, trust_net, yoy, mom, current_change):
        try:
            pe_num = float(pe_val) if pe_val not in ['N/A', '未知', ''] else 20.0
        except:
            pe_num = 20.0
            
        try:
            price_num = float(current_price) if current_price not in ['N/A', '未知', ''] else 100.0
        except:
            price_num = 100.0

        try:
            f_net = float(foreign_net)
        except:
            f_net = 0.0

        try:
            t_net = float(trust_net)
        except:
            t_net = 0.0

        is_smart_money_buy = f_net > 0 and t_net > 0
        is_trust_buying = t_net > 100

        if is_smart_money_buy or (pe_num < 16 and is_trust_buying):
            verdict = '強烈看多'
            score = 88
            win_rate = '82%'
            bias = '三大法人土洋合力吃貨，且評價處於具安全邊際之估值水準。'
        elif pe_num < 18 or is_trust_buying:
            verdict = '謹慎看多'
            score = 78
            win_rate = '72%'
            bias = '投信與主力買盤進駐，估值相對同業仍具性價比優勢。'
        elif pe_num > 28:
            verdict = '轉弱看空'
            score = 45
            win_rate = '38%'
            bias = '目前評價嚴重偏離產業平均，且成長動能未達高估值預期。'
        else:
            verdict = '中立觀望'
            score = 65
            win_rate = '55%'
            bias = '估值落於同業中位數區間，目前呈現箱型整理格局。'

        buy_low = round(price_num * 0.95, 1)
        buy_high = round(price_num * 0.98, 1)
        sell_low = round(price_num * 1.08, 1)
        sell_high = round(price_num * 1.15, 1)
        stop_loss = round(price_num * 0.92, 1)

        content = (
            f"#### 🎯 核心邏輯剖析\n"
            f"- **估值與成長對決**: 目標股價現報 {current_price} 元，本益比約 {pe_val} 倍 (同業平均約 {sector_pe} 倍)。營收年增率 YoY 為 {yoy}%、月增率 MoM 為 {mom}%。{bias}\n"
            f"- **籌碼博弈解讀**: 今日漲跌為 {current_change}，外資買賣超 {f_net:+.0f} 張、投信買賣超 {t_net:+.0f} 張。"
            + ("外資與投信呈現同步作多姿態，籌碼集中度高。" if is_smart_money_buy else "內外資步調不一，後續應密切觀察投信買超延續性。") +
            f"\n\n#### 🔮 實戰預判 & 操作策略\n"
            f"- **走勢預演**: 預計短期內回測支撐後蓄勢上攻，若量能持續溫和放大，有機會挑戰波段高點。\n"
            f"- **關鍵操作**: 建議於 {buy_low} ~ {buy_high} 分批布局，波段停利目標看至 {sell_low} ~ {sell_high}。嚴格風控停損點設在 {stop_loss} 元。"
        )

        return {
            'buy_price': f"{buy_low} - {buy_high}",
            'sell_price': f"{sell_low} - {sell_high}",
            'stop_loss': str(stop_loss),
            'score': score,
            'win_rate': win_rate,
            'verdict': verdict,
            'report': content,
            'content': content
        }

    def _call_groq(self, prompt, api_key):
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

        if not re.match(r'^[0-9A-Za-z]{2,6}$', stock_id):
            self._send_json({
                "score": 0, "verdict": "Input Error",
                "report": "⚠️ 股票代號格式錯誤，請輸入 4 碼台股代號。"
            }, 400)
            return

        current_price = get_param("price", "未知")
        current_change = get_param("change", "未知")
        pe = get_param("pe", "N/A")
        sector_pe = get_param("sector_pe", "N/A")
        foreign_net = get_param("foreign_net", "0")
        trust_net = get_param("trust_net", "0")
        yoy = get_param("yoy", "N/A")
        mom = get_param("mom", "N/A")
        
        try:
            if current_price not in ["未知", "N/A"]:
                current_price = str(float(current_price))
        except:
            current_price = "未知"
            
        try:
            if pe != "N/A":
                pe = str(float(pe))
        except:
            pe = "N/A"
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        prompt = (
            f"現在是真實世界日期：{today}。請你擔任一位華爾街頂尖量化避險基金的資深操盤手，風格犀利、邏輯嚴謹，擅長從「真實三大法人籌碼」與「財報成長動能」的背離中尋找高勝率波段交易機會。\n\n"
            f"### 【目標個股即時量化指標】\n"
            f"- 股票代號：{stock_id}\n"
            f"- 現價：{current_price} 元 (今日漲跌：{current_change})\n"
            f"- 個股本益比(PE)：{pe} 倍 (同業平均本益比：{sector_pe} 倍)\n"
            f"- 外資單日買賣超：{foreign_net} 張\n"
            f"- 投信單日買賣超：{trust_net} 張\n"
            f"- 最新月營收年增率(YoY)：{yoy}%\n"
            f"- 最新月營收月增率(MoM)：{mom}%\n\n"
            f"### 輸出格式 (Strict JSON ONLY)：\n"
            f"請務必回傳標準 JSON 物件，**嚴禁** Markdown 代碼塊，格式如下：\n"
            f"{{\n"
            f'  "buy_price": "[進場布局區間，如 980 - 1010]",\n'
            f'  "sell_price": "[波段目標價，如 1120 - 1160]",\n'
            f'  "stop_loss": "[嚴格風控停損價，如 930]",\n'
            f'  "score": 0-100,\n'
            f'  "win_rate": "[預估勝率，如 78%]",\n'
            f'  "verdict": "[強烈看多 / 謹慎看多 / 中立觀望 / 轉弱看空]",\n'
            f'  "content": "[完整分析報告]"\n'
            f"}}\n\n"
            f"### Content 欄位內容指引：\n"
            f"#### 🎯 核心邏輯剖析\n"
            f"- **估值與成長對決**: (解讀本益比 {pe} vs 同業 {sector_pe}，搭配營收 YoY {yoy}% 評估安全邊際)\n"
            f"- **籌碼博弈解讀**: (分析外資 {foreign_net} 張 與投信 {trust_net} 張 之主力意圖與合力方向)\n\n"
            f"#### 🔮 實戰預判 & 操作策略\n"
            f"- **走勢預演**: (預測未來 1~2 週關鍵轉折與阻力支撐)\n"
            f"- **進出場與風控**: (明確進場區間、停利點位、嚴格停損價位)\n"
        )

        ai_data = None
        
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            try:
                ai_data = self._call_groq(prompt, groq_key)
            except Exception:
                ai_data = None

        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not ai_data and gemini_key:
            try:
                ai_data = self._call_gemini(prompt, gemini_key)
            except Exception:
                ai_data = None

        if not ai_data:
            ai_data = self._generate_rule_based_fallback(stock_id, current_price, pe, sector_pe, foreign_net, trust_net, yoy, mom, current_change)

        if 'report' not in ai_data and 'content' in ai_data:
            ai_data['report'] = ai_data['content']
            
        self._send_json(ai_data)
