import pandas as pd
from backend.scrapers.twse import TWSEScraper
from backend.models.stock_data import PERadar

class ValuationService:
    def __init__(self):
        self.scraper = TWSEScraper()

    def get_valuation(self, stock_id: str) -> PERadar:
        # 1. Fetch Sector P/E (All stocks)
        df = self.scraper.fetch_sector_pe()
        
        if df is None or df.empty:
            return None
        
        # 2. Filter for specific stock
        # Columns in BWESS: "證券代號", "證券名稱", "殖利率(%)", "股利年度", "本益比", "股價淨值比", "財報年/季"
        # Note: Columns might be in Chinese.
        
        # Normalize columns just in case
        # Example 2330
        record = df[df['證券代號'] == stock_id]
        
        if record.empty:
            return None
            
        record = record.iloc[0]
        
        try:
            pe_str = record['本益比'].replace(',', '')
            pe = float(pe_str) if pe_str != '-' else 0.0
            
            # 3. Calculate Sector Average
            # Need to know which sector it belongs to.
            # For V1, let's calculate the average of the WHOLE market or try to infer sector?
            # Or just use a dummy sector PE for now if we don't have sector mapping.
            # Real implementation needs a Stock -> Sector mapping table.
            
            sector_pe = 20.0 # Placeholder or calculate mean of positive PEs
            
            # Simple average of all stocks
            # sector_pe = df[df['本益比'] != '-']['本益比'].astype(str).str.replace(',', '').astype(float).mean()

            score = pe / sector_pe if sector_pe > 0 else 0
            
            status = "Fair Value"
            if score > 1.2:
                status = "High Premium"
            elif score < 0.8:
                status = "Undervalued"
                
            return PERadar(
                stock_id=stock_id,
                current_pe=pe,
                sector_pe=sector_pe,
                pe_score=score,
                status=status
            )
            
        except Exception as e:
            print(f"Error calculating valuation: {e}")
            return None
