import requests
import pandas as pd
from datetime import datetime

def test_futures_oi():
    print("\n🕵️‍♂️ [1/3] 正在測試期交所 (Futures OI) 抓取...")
    url = "https://www.taifex.com.tw/cht/3/futContractsDate"
    
    # 這是關鍵的偽裝表頭
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    try:
        r = requests.get(url, headers=headers)
        print(f"   📡 HTTP 狀態碼: {r.status_code}")
        
        if r.status_code != 200:
            print("   ❌ 被擋了！期交所拒絕連線。")
            return

        # 嘗試解析表格
        dfs = pd.read_html(r.text)
        print(f"   📊 抓到了 {len(dfs)} 個表格")
        
        if len(dfs) > 0:
            df = dfs[0]
            # 印出前幾行看看長怎樣
            print("   👀 表格預覽 (前 5 行):")
            print(df.head())
            
            # 尋找外資
            # 這裡我們印出包含 '外資' 的那一列，看看數據在哪裡
            mask = df.astype(str).apply(lambda x: x.str.contains('外資').any(), axis=1)
            target_rows = df[mask]
            
            if not target_rows.empty:
                print("\n   🎯 找到 '外資' 相關列：")
                print(target_rows)
                print("\n   💡 請檢查上表中，'未平倉餘額' (Net OI) 是在第幾欄？")
            else:
                print("   ❌ 表格裡找不到 '外資' 字樣，可能是表格結構變了。")
        else:
            print("   ❌ 抓不到任何表格，可能網頁內容是用 JavaScript 動態跑的。")

    except Exception as e:
        print(f"   ❌ 發生錯誤: {e}")

def test_t86_smart_money():
    print("\n🕵️‍♂️ [2/3] 正在測試證交所 (T86 Smart Money) 抓取...")
    url = "https://www.twse.com.tw/rwd/zh/fund/T86?selectType=ALL&response=json"
    
    try:
        r = requests.get(url)
        print(f"   📡 HTTP 狀態碼: {r.status_code}")
        
        data = r.json()
        if data.get('stat') == 'OK':
            print("   ✅ T86 資料抓取成功！")
            sample = data['data'][0]
            print(f"   👀 第一筆資料範例 (台積電?): {sample}")
            print(f"   👉 欄位數量: {len(sample)}")
            print("   💡 請確認：第 4 欄是外資買賣超嗎？ 第 10 欄是投信嗎？")
        else:
            print(f"   ❌ 資料狀態不對: {data.get('stat')} (可能是休市或過於頻繁)")
            
    except Exception as e:
        print(f"   ❌ 發生錯誤: {e}")

if __name__ == "__main__":
    test_futures_oi()
    test_t86_smart_money()