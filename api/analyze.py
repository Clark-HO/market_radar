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
            pe_num = float(pe_val) if pe_val not in ['N/A', '??', ''] else 20.0
        except:
            pe_num = 20.0
            
        try:
            price_num = float(current_price) if current_price not in ['N/A', '??', ''] else 100.0
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
            verdict = '????'
            score = 88
            win_rate = '82%'
            bias = '???????????????????????????'
        elif pe_num < 18 or is_trust_buying:
            verdict = '????'
            score = 78
            win_rate = '72%'
            bias = '????????????????????????'
        elif pe_num > 28:
            verdict = '????'
            score = 45
            win_rate = '38%'
            bias = '??????????????????????????'
        else:
            verdict = '????'
            score = 65
            win_rate = '55%'
            bias = '???????????????????????'

        buy_low = round(price_num * 0.95, 1)
        buy_high = round(price_num * 0.98, 1)
        sell_low = round(price_num * 1.08, 1)
        sell_high = round(price_num * 1.15, 1)
        stop_loss = round(price_num * 0.92, 1)

        content = (
            f"#### ?? ??????\n"
            f"- **???????**: ?????? {current_price} ?????? {pe_val} ? (????? {sector_pe} ?)?????? YoY ? {yoy}%???? MoM ? {mom}%?{bias}\n"
            f"- **??????**: ????? {current_change}?????? {f_net:+.0f} ??????? {t_net:+.0f} ??"
            + ("?????????????????????" if is_smart_money_buy else "???????????????????????") +
            f"\n\n#### ?? ???? & ????\n"
            f"- **????**: ???????????????????????????????????\n"
            f"- **????**: ??? {buy_low} ~ {buy_high} ????????????? {sell_low} ~ {sell_high}?????????? {stop_loss} ??"
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
                "report": "? API ?????????????"
            })
            return

        if not re.match(r'^[0-9A-Za-z]{2,6}$', stock_id):
            self._send_json({
                "score": 0, "verdict": "Input Error",
                "report": "?? ???????????? 4 ??????"
            }, 400)
            return

        current_price = get_param("price", "??")
        current_change = get_param("change", "??")
        pe = get_param("pe", "N/A")
        sector_pe = get_param("sector_pe", "N/A")
        foreign_net = get_param("foreign_net", "0")
        trust_net = get_param("trust_net", "0")
        yoy = get_param("yoy", "N/A")
        mom = get_param("mom", "N/A")
        
        try:
            if current_price not in ["??", "N/A"]:
                current_price = str(float(current_price))
        except:
            current_price = "??"
            
        try:
            if pe != "N/A":
                pe = str(float(pe))
        except:
            pe = "N/A"
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        prompt = (
            f"??????????{today}?????????????????????????????????????????????????????????????????????????\n\n"
            f"### ????????????\n"
            f"- ?????{stock_id}\n"
            f"- ???{current_price} ? (?????{current_change})\n"
            f"- ?????(PE)?{pe} ? (????????{sector_pe} ?)\n"
            f"- ????????{foreign_net} ?\n"
            f"- ????????{trust_net} ?\n"
            f"- ????????(YoY)?{yoy}%\n"
            f"- ????????(MoM)?{mom}%\n\n"
            f"### ???? (Strict JSON ONLY)?\n"
            f"??????? JSON ???**??** Markdown ?????????\n"
            f"{{\n"
            f'  "buy_price": "[???????? 980 - 1010]",\n'
            f'  "sell_price": "[??????? 1120 - 1160]",\n'
            f'  "stop_loss": "[????????? 930]",\n'
            f'  "score": 0-100,\n'
            f'  "win_rate": "[?????? 78%]",\n'
            f'  "verdict": "[???? / ???? / ???? / ????]",\n'
            f'  "content": "[??????]"\n'
            f"}}\n\n"
            f"### Content ???????\n"
            f"#### ?? ??????\n"
            f"- **???????**: (????? {pe} vs ?? {sector_pe}????? YoY {yoy}% ??????)\n"
            f"- **??????**: (???? {foreign_net} ? ??? {trust_net} ? ??????????)\n\n"
            f"#### ?? ???? & ????\n"
            f"- **????**: (???? 1~2 ??????????)\n"
            f"- **??????**: (??????????????????)\n"
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
