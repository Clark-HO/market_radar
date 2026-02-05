import os
# import openai # Removed OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

def generate_rule_based_report(stock_data):
    """
    Original Expert System Logic (Fallback)
    """
    sid = stock_data.get('stock_id')
    name = stock_data.get('stock_name', sid)
    
    val = stock_data.get('valuation', {})
    pe = val.get('current_pe', 0)
    rev = stock_data.get('revenue', {})
    mom = rev.get('mom', 0)
    yoy = rev.get('yoy', 0)
    chips = stock_data.get('chips', {})
    foreign = chips.get('foreign_net', 0)
    trust = chips.get('trust_net', 0)
    
    score = 50 
    bull_factors, bear_factors = [], []
    
    # 1. Chips
    if foreign > 1000: 
        score += 15
        bull_factors.append(f"外資強力買超 ({foreign}張)。")
    elif foreign > 0:
        score += 5
        bull_factors.append("外資站在買方。")
    elif foreign < -1000:
        score -= 15
        bear_factors.append(f"外資調節 ({foreign}張)。")
        
    if trust > 100:
        score += 10
        bull_factors.append("投信進場佈局。")
        
    # 2. Revenue
    if yoy > 20:
        score += 15
        bull_factors.append(f"營收年增爆發 (+{yoy}%)。")
    elif yoy < -20:
        score -= 15
        bear_factors.append(f"營收明顯衰退 ({yoy}%)。")
        
    # 3. Valuation
    if pe > 0 and pe < 15:
        score += 10
        bull_factors.append(f"本益比 ({pe}x) 低廉。")
    elif pe > 40:
        score -= 10
        bear_factors.append(f"本益比 ({pe}x) 偏高。")
        
    # Verdict
    if score >= 80: verdict = "強力買進 (Strong Buy)"
    elif score >= 60: verdict = "偏多操作 (Bullish)"
    elif score <= 30: verdict = "保守觀望 (Bearish)"
    else: verdict = "區間震盪 (Neutral)"
    
    summary_md = f"### 🤖 Rules AI 診斷: {name} ({sid})\n\n"
    summary_md += f"**總和評分**: {score}分 - **{verdict}**\n\n"
    for f in bull_factors: summary_md += f"- 📈 {f}\n"
    for f in bear_factors: summary_md += f"- 📉 {f}\n"
    
    if not bull_factors and not bear_factors:
        summary_md += "數據平穩，無顯著訊號。\n"
        
    summary_md += "\n> *此報告由專家規則系統生成 (Rule-Based)*"
    
    return { "score": score, "verdict": verdict, "report": summary_md }

def generate_llm_report(stock_data, api_key):
    """
    Generative AI Logic via Google Gemini
    """
    try:
        genai.configure(api_key=api_key)
        
        # Use simple model string
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        sid = stock_data.get('stock_id')
        name = stock_data.get('stock_name', sid)
        
        prompt = f"""
        你現在是華爾街頂尖避險基金的資深操盤手，風格犀利、邏輯嚴謹，擅長從「籌碼面」與「基本面」的背離中尋找交易機會。

        請根據以下即時數據，進行深度交叉分析，並預判短期股價走勢。

        [股票資訊]
        代號: {sid}
        名稱: {name}

        [基本面數據]
        本益比 (PE): {stock_data.get('valuation', {}).get('current_pe', 'N/A')}x (同業平均: {stock_data.get('valuation', {}).get('sector_pe', 'N/A')}x) -> *請判斷此溢價是否由成長性支撐*
        營收月增 (MoM): {stock_data.get('revenue', {}).get('mom', 'N/A')}%
        營收年增 (YoY): {stock_data.get('revenue', {}).get('yoy', 'N/A')}% -> *這是評估股價動能的核心*

        [籌碼面數據]
        外資買賣超: {stock_data.get('chips', {}).get('foreign_net', '0')}張 (主導趨勢的關鍵力量)
        投信買賣超: {stock_data.get('chips', {}).get('trust_net', '0')}張 (內資作帳與護盤指標)
        主力動向: {stock_data.get('chips', {}).get('analysis', 'N/A')} (囤貨中/出貨中)

        ---
        **分析邏輯指引 (Thinking Process):**
        1. **估值檢測 (PEG Logic):** 用「營收年增率」去檢視「本益比」是否過高？(例如：年增 35% 支撐 28倍 PE 是合理的，反之則危險)。
        2. **籌碼動能 (Flow Analysis):** 外資與投信是否「同向」？如果外資大買且主力狀態為 Accumulating，代表趨勢確立；若外資買但主力在出貨，則為假突破。
        3. **預判結論:** 綜合以上，判斷下週走勢是「強勢噴出」、「高檔震盪」還是「拉回修正」。

        ---
        請直接輸出以下 Markdown 格式 (語氣要果斷，不要模稜兩可)：

        ### ⚡ 操盤手戰情室: {name} ({sid})
        **AI 綜合戰力**: <根據基本面與籌碼配合度給 0-100 分> 分
        **趨勢訊號**: **<強烈看多 (Strong Bull) / 謹慎看多 (Bullish) / 中立觀望 (Neutral) / 轉弱看空 (Bearish)>**

        #### 🎯 核心邏輯剖析 (Cross Analysis)
        - **估值與成長對決**: <一句話分析。例如："雖 PE 高於同業，但 35% 的高成長率完美消化了估值壓力，PEG 顯示股價仍具吸引力。">
        - **籌碼博弈解讀**: <一句話分析。例如："外資與投信同步大買 (土洋合流)，且主力處於吸籌階段，顯示大戶對後市極度看好，籌碼結構紮實。">

        #### 🔮 實戰預判 & 操作策略
        - **走勢預演**: <預測接下來會發生的事。例如："在營收創高與法人買盤堆疊下，股價極高機率突破前高，短線將沿著均線強勢上攻。">
        - **關鍵操作**: <給出具體建議。例如："只要外資買超不縮手，任何拉回皆是買點。切勿預設高點，抱緊處理。/ 留意追高風險，建議等拉回五日線再佈局。">
        """
        
        response = model.generate_content(prompt)
        content = response.text
        
        # Regex Extraction
        import re
        # Relaxed pattern for Score: Matches "**AI 綜合戰力**: 90" or "AI 綜合戰力: 90"
        score_match = re.search(r'AI 綜合戰力\D*(\d+)', content)
        score = int(score_match.group(1)) if score_match else 75
        
        # Relaxed pattern for Verdict: Matches "**趨勢訊號**: **Verdict**"
        verdict_match = re.search(r'趨勢訊號.*?\*\*([^*]+)\*\*', content)
        verdict = verdict_match.group(1).strip() if verdict_match else "AI 分析"
        
        return { "score": score, "verdict": verdict, "report": content }
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        return generate_rule_based_report(stock_data) # Fallback

def generate_ai_report(stock_data):
    """
    Hybrid Dispatcher
    """
    # Check for Gemini Key
    api_key = os.getenv("GEMINI_API_KEY") # Changed from OPENAI
    
    if api_key:
        return generate_llm_report(stock_data, api_key)
    else:
        return generate_rule_based_report(stock_data)
