from pydantic import BaseModel
from typing import Optional, List

class StockInfo(BaseModel):
    stock_id: str
    name: str

class DailyQuote(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class PERadar(BaseModel):
    stock_id: str
    current_pe: float
    sector_pe: float
    pe_score: float # > 1.2 Premium, < 0.8 Undervalued
    status: str # "High Premium", "Undervalued", "Fair Value"

class RevenueData(BaseModel):
    month: str
    revenue: float
    mom_percent: float
    yoy_percent: float
