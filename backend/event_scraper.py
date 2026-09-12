"""
Event Scraper — 自動抓取科技展會日期，結合台灣供應鏈模板產生 events.json

策略：
  1. 供應鏈對應關係相對穩定（年年差不多），用模板維護
  2. 展會日期每年變動，用爬蟲從官網 / 可靠來源抓取
  3. 若爬蟲失敗，用去年日期 +1 年做估計值
  4. 整合進 GitHub Actions 週排程（每週一跑一次）
"""

import json
import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVENTS_JSON_PATH = os.path.join(BASE_DIR, "events.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

# --- 1. Supply Chain Templates (stable year-over-year) ---
# These map each conference to its relevant US/TW stock ecosystem.
# Only the dates change yearly; the supply chains are relatively constant.

CONFERENCE_TEMPLATES = [
    {
        "id": "ces",
        "event": "CES 消費電子展",
        "theme": "AI 硬體 / 智慧家庭 / 電動車",
        "description": "全球最大消費電子展。聚焦 AI PC、穿戴裝置與車用電子新品發表。",
        "scrape_url": "https://www.ces.tech/",
        "typical_month": 1,  # January
        "typical_duration_days": 4,
        "supply_chain": [
            {"us_symbol": "NVDA", "us_name": "輝達", "tw_tickers": ["2330", "2454", "3231"], "tw_sector": "AI 晶片"},
            {"us_symbol": "INTC", "us_name": "英特爾", "tw_tickers": ["2357", "2353"], "tw_sector": "PC 供應鏈"}
        ]
    },
    {
        "id": "mwc",
        "event": "MWC 世界行動通訊大會",
        "theme": "6G / Wi-Fi 7 / 邊緣 AI",
        "description": "全球最大通訊展。聚焦非地面網路 (NTN) 與終端 AI 應用。觀察網通設備升級潮。",
        "scrape_url": "https://www.mwcbarcelona.com/",
        "typical_month": 2,  # Late February
        "typical_duration_days": 4,
        "supply_chain": [
            {"us_symbol": "QCOM", "us_name": "高通", "tw_tickers": ["2454", "2379", "3105"], "tw_sector": "IC 設計"},
            {"us_symbol": "AVGO", "us_name": "博通", "tw_tickers": ["5388", "6285"], "tw_sector": "網通設備"}
        ]
    },
    {
        "id": "gtc",
        "event": "NVIDIA GTC 大會",
        "theme": "Blackwell Ultra / Rubin GPU / AI 推論",
        "description": "AI 界的伍茲塔克。黃仁勳揭曉下一代 AI 推論晶片與 Sovereign AI 戰略。",
        "scrape_url": "https://www.nvidia.com/gtc/",
        "typical_month": 3,  # March
        "typical_duration_days": 4,
        "supply_chain": [
            {"us_symbol": "NVDA", "us_name": "輝達", "tw_tickers": ["2330", "2382", "3231", "6669"], "tw_sector": "AI 伺服器"},
            {"us_symbol": "SMCI", "us_name": "美超微", "tw_tickers": ["2376", "2324"], "tw_sector": "伺服器代工"}
        ]
    },
    {
        "id": "google_io",
        "event": "Google I/O 開發者大會",
        "theme": "Gemini / Android / AI Agent",
        "description": "Google 軟體火力展示。關注 Pixel 手機的 AI 整合與各種 Agent 應用。",
        "scrape_url": "https://io.google/",
        "typical_month": 5,  # May
        "typical_duration_days": 2,
        "supply_chain": [
            {"us_symbol": "GOOGL", "us_name": "Alphabet", "tw_tickers": ["2357", "2498"], "tw_sector": "安卓生態系"}
        ]
    },
    {
        "id": "computex",
        "event": "Computex 台北國際電腦展",
        "theme": "AI PC / Copilot+ / 伺服器",
        "description": "台灣主場優勢。AMD, Intel, Qualcomm 執行長齊聚台北，發布 AI PC 新品。",
        "scrape_url": "https://www.computextaipei.com.tw/",
        "typical_month": 6,  # June
        "typical_duration_days": 5,
        "supply_chain": [
            {"us_symbol": "MSFT", "us_name": "微軟", "tw_tickers": ["2353", "2357", "2301"], "tw_sector": "AI PC 供應鏈"},
            {"us_symbol": "AMD", "us_name": "超微", "tw_tickers": ["2330", "3711"], "tw_sector": "HPC 運算"}
        ]
    },
    {
        "id": "wwdc",
        "event": "Apple WWDC 開發者大會",
        "theme": "iOS / macOS / Siri LLM",
        "description": "蘋果 AI 戰略關鍵時刻。預期發布裝置端 (On-device) AI 新功能。",
        "scrape_url": "https://developer.apple.com/wwdc/",
        "typical_month": 6,  # June
        "typical_duration_days": 5,
        "supply_chain": [
            {"us_symbol": "AAPL", "us_name": "蘋果", "tw_tickers": ["2317", "3008", "4938"], "tw_sector": "蘋果供應鏈"}
        ]
    },
    {
        "id": "ifa",
        "event": "IFA 柏林消費電子展",
        "theme": "家電 / IoT / 穿戴裝置",
        "description": "歐洲最大消費電子展。聚焦智慧家庭、穿戴裝置與永續科技。",
        "scrape_url": "https://www.ifa-berlin.com/",
        "typical_month": 9,  # September
        "typical_duration_days": 5,
        "supply_chain": [
            {"us_symbol": "GOOGL", "us_name": "Alphabet", "tw_tickers": ["2317", "2357"], "tw_sector": "消費電子"}
        ]
    }
]


# --- 2. Date Scraping Functions ---

def _extract_dates_from_text(text, year):
    """
    Try to find date patterns like:
    - 'January 7-10, 2027'
    - 'Jan 7 – 10, 2027'
    - 'March 18-21, 2027'
    - '2027.03.18 - 2027.03.21'
    - '6/2 - 6/6'
    Returns (start_date, end_date) or None.
    """
    # Pattern 1: 'Month D-D, YYYY' or 'Month D – D, YYYY'
    pattern1 = r'(January|February|March|April|May|June|July|August|September|October|November|December|' \
               r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s*[-–—]\s*(\d{1,2}),?\s*(\d{4})'
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        month_str, start_day, end_day, yr = match.groups()
        try:
            start = datetime.datetime.strptime(f"{month_str} {start_day} {yr}", "%B %d %Y").date()
        except ValueError:
            start = datetime.datetime.strptime(f"{month_str} {start_day} {yr}", "%b %d %Y").date()
        end = start.replace(day=int(end_day))
        return start, end

    # Pattern 2: 'YYYY-MM-DD' or 'YYYY.MM.DD'
    pattern2 = r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s*[-–—]\s*(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})'
    match = re.search(pattern2, text)
    if match:
        y1, m1, d1, y2, m2, d2 = [int(x) for x in match.groups()]
        return datetime.date(y1, m1, d1), datetime.date(y2, m2, d2)

    # Pattern 3: 'Month D - Month D, YYYY'
    pattern3 = r'(January|February|March|April|May|June|July|August|September|October|November|December|' \
               r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s*[-–—]\s*' \
               r'(January|February|March|April|May|June|July|August|September|October|November|December|' \
               r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s*(\d{4})'
    match = re.search(pattern3, text, re.IGNORECASE)
    if match:
        m1_str, d1, m2_str, d2, yr = match.groups()
        try:
            start = datetime.datetime.strptime(f"{m1_str} {d1} {yr}", "%B %d %Y").date()
            end = datetime.datetime.strptime(f"{m2_str} {d2} {yr}", "%B %d %Y").date()
        except ValueError:
            start = datetime.datetime.strptime(f"{m1_str} {d1} {yr}", "%b %d %Y").date()
            end = datetime.datetime.strptime(f"{m2_str} {d2} {yr}", "%b %d %Y").date()
        return start, end

    return None


def scrape_conference_dates(conf, target_year):
    """
    Try to scrape dates for a conference from its official website.
    Returns (start_date, end_date) or None on failure.
    """
    url = conf.get("scrape_url")
    conf_id = conf.get("id", "unknown")

    if not url:
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get all visible text
        page_text = soup.get_text(separator=" ", strip=True)

        # Look for dates mentioning the target year
        result = _extract_dates_from_text(page_text, target_year)
        if result:
            start, end = result
            if start.year == target_year:
                print(f"   ✅ [{conf_id}] Scraped: {start} ~ {end}")
                return start, end

        # Also check meta tags, title, and og:description
        for meta in soup.find_all("meta"):
            content = meta.get("content", "")
            result = _extract_dates_from_text(content, target_year)
            if result:
                start, end = result
                if start.year == target_year:
                    print(f"   ✅ [{conf_id}] Scraped from meta: {start} ~ {end}")
                    return start, end

        print(f"   ⚠️ [{conf_id}] No {target_year} dates found on {url}")
        return None

    except Exception as e:
        print(f"   ⚠️ [{conf_id}] Scrape failed: {e}")
        return None


def estimate_dates(conf, target_year):
    """
    Estimate conference dates based on typical month and duration.
    Uses the first Monday of the typical month as a heuristic.
    """
    month = conf["typical_month"]
    duration = conf.get("typical_duration_days", 4)

    # Find the first Monday of that month
    first_day = datetime.date(target_year, month, 1)
    # Shift to first Monday (weekday 0 = Monday)
    days_until_monday = (7 - first_day.weekday()) % 7
    if days_until_monday == 0 and first_day.weekday() != 0:
        days_until_monday = 7
    first_monday = first_day + datetime.timedelta(days=max(days_until_monday, 0))
    if first_monday.day == 1 and first_monday.weekday() == 0:
        pass  # It's already Monday the 1st
    elif first_monday.day > 7:
        first_monday = first_day  # fallback

    # For most conferences, use the 2nd or 3rd week
    start = first_monday + datetime.timedelta(days=7)  # 2nd week
    end = start + datetime.timedelta(days=duration - 1)

    return start, end


# --- 3. Main Pipeline ---

def generate_events(target_year=None):
    """
    Main function: scrape dates + merge with supply chain templates → events.json
    """
    if target_year is None:
        now = datetime.datetime.now()
        target_year = now.year
        # If we're in Q4, also look for next year's events
        current_month = now.month

    print(f"[Event Scraper] Scanning conferences for {target_year}...")

    events = []
    years_to_scan = [target_year]
    # If it's after September, also scan next year
    if datetime.datetime.now().month >= 9:
        years_to_scan.append(target_year + 1)

    for year in years_to_scan:
        for conf in CONFERENCE_TEMPLATES:
            # Try scraping first
            result = scrape_conference_dates(conf, year)

            if result:
                start_date, end_date = result
            else:
                # Fallback to estimated dates
                start_date, end_date = estimate_dates(conf, year)
                print(f"   📅 [{conf['id']}] Using estimated dates: {start_date} ~ {end_date}")

            # Build event entry (same structure as events.json)
            event = {
                "event": f"{conf['event']} {year}",
                "date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "theme": conf["theme"],
                "description": conf["description"],
                "supply_chain": conf["supply_chain"]
            }
            events.append(event)

    # Sort by date
    events.sort(key=lambda e: e["date"])

    # Save
    with open(EVENTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    print(f"✅ [Event Scraper] Generated {len(events)} events → {EVENTS_JSON_PATH}")
    return events


if __name__ == "__main__":
    generate_events()
