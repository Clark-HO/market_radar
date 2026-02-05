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
        你是專業的主力操盤手，請根據提供的台股數據進行犀利的分析。
        
        [股票資訊]
        代號: {sid}
        名稱: {name}
        
        [基本面]
        本益比: {stock_data.get('valuation', {}).get('current_pe', 'N/A')}x (同業: {stock_data.get('valuation', {}).get('sector_pe', 'N/A')}x)
        營收月增: {stock_data.get('revenue', {}).get('mom', 'N/A')}%
        營收年增: {stock_data.get('revenue', {}).get('yoy', 'N/A')}%
        
        [籌碼面]
        外資買賣超: {stock_data.get('chips', {}).get('foreign_net', '0')}張
        投信買賣超: {stock_data.get('chips', {}).get('trust_net', '0')}張
        主力動向: {stock_data.get('chips', {}).get('analysis', 'N/A')}
        
        請直接輸出以下 Markdown 格式 (不要解釋，直接給內容)：
        
        ### 🤖 Gemini Pro 深度剖析: {name}
        AI 評分: <根據好壞給0-100分>分 - **<Strong Buy/Bullish/Neutral/Bearish>**
        
        #### 關鍵洞察
        - <Point 1>
        - <Point 2>
        
        #### 操作建議
        <一段精簡犀利的建議>
        """
        
        response = model.generate_content(prompt)
        content = response.text
        
        # Regex Extraction
        import re
        score_match = re.search(r'AI 評分.*?:.*?(\d+)', content)
        score = int(score_match.group(1)) if score_match else 75
        
        verdict_match = re.search(r'AI 評分.*?- \*\*(.*?)\*\*', content)
        verdict = verdict_match.group(1) if verdict_match else "AI 分析"
        
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
