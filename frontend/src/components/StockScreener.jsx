import React, { useState, useMemo } from 'react';
import { Star, Zap, TrendingUp, Award, Target, Compass, X } from 'lucide-react';

export default function StockScreener({ stocks = {}, currentTicker, onSelectTicker }) {
  const [activeStrategy, setActiveStrategy] = useState(null);
  const [watchlist, setWatchlist] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('market_radar_watchlist') || '["2330", "2317", "2454"]');
    } catch {
      return ["2330", "2317", "2454"];
    }
  });

  const stockList = useMemo(() => Object.values(stocks), [stocks]);

  const filteredStocks = useMemo(() => {
    if (!activeStrategy || stockList.length === 0) return [];
    switch (activeStrategy) {
      case 'watchlist':
        return stockList.filter(s => watchlist.includes(s.stock_id));
      case 'smart_money':
        return stockList.filter(s => (s.chips?.foreign_net || 0) > 0 && (s.chips?.trust_net || 0) > 0);
      case 'growth':
        return stockList.filter(s => (s.revenue?.yoy || 0) > 15 && (s.revenue?.mom || 0) > 0);
      case 'undervalued':
        return stockList.filter(s => s.valuation?.status === 'Undervalued' || (s.valuation?.current_pe > 0 && s.valuation?.current_pe < (s.valuation?.sector_pe || 20)));
      case 'trust_top':
        return [...stockList].sort((a, b) => (b.chips?.trust_net || 0) - (a.chips?.trust_net || 0)).slice(0, 8);
      default:
        return [];
    }
  }, [activeStrategy, stockList, watchlist]);

  return (
    <div className="bg-neutral-900/80 backdrop-blur-md p-4 rounded-2xl border border-white/10 shadow-lg space-y-3 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <Compass className="w-4 h-4 text-emerald-400" />
          <span>選股雷達快篩</span>
        </div>
        {activeStrategy && (
          <button 
            onClick={() => setActiveStrategy(null)}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <span>關閉清單</span>
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveStrategy(activeStrategy === 'watchlist' ? null : 'watchlist')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
            activeStrategy === 'watchlist' 
              ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-md' 
              : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
          }`}
        >
          <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
          <span>我的自選 ({watchlist.length})</span>
        </button>

        <button
          onClick={() => setActiveStrategy(activeStrategy === 'smart_money' ? null : 'smart_money')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
            activeStrategy === 'smart_money' 
              ? 'bg-red-500/20 border-red-500/50 text-red-300 shadow-md' 
              : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
          }`}
        >
          <Zap className="w-3.5 h-3.5 text-red-400" />
          <span>🚀 主力雙買 (外資+投信)</span>
        </button>

        <button
          onClick={() => setActiveStrategy(activeStrategy === 'growth' ? null : 'growth')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
            activeStrategy === 'growth' 
              ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-md' 
              : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
          }`}
        >
          <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
          <span>📈 營收暴衝 (YoY &gt; 15%)</span>
        </button>

        <button
          onClick={() => setActiveStrategy(activeStrategy === 'undervalued' ? null : 'undervalued')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
            activeStrategy === 'undervalued' 
              ? 'bg-blue-500/20 border-blue-500/50 text-blue-300 shadow-md' 
              : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
          }`}
        >
          <Award className="w-3.5 h-3.5 text-blue-400" />
          <span>💎 價值低估</span>
        </button>

        <button
          onClick={() => setActiveStrategy(activeStrategy === 'trust_top' ? null : 'trust_top')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
            activeStrategy === 'trust_top' 
              ? 'bg-purple-500/20 border-purple-500/50 text-purple-300 shadow-md' 
              : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
          }`}
        >
          <Target className="w-3.5 h-3.5 text-purple-400" />
          <span>🏆 投信重倉 Top</span>
        </button>
      </div>

      {activeStrategy && (
        <div className="pt-2 border-t border-white/5">
          <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-white/10">
            {filteredStocks.length === 0 ? (
              <div className="text-xs text-slate-400 py-2">目前條件下尚無符合個股</div>
            ) : (
              filteredStocks.map(stock => {
                const isCurrent = stock.stock_id === currentTicker;
                return (
                  <button
                    key={stock.stock_id}
                    onClick={() => onSelectTicker && onSelectTicker(stock.stock_id)}
                    className={`shrink-0 flex items-center gap-2 px-3 py-2 rounded-xl border text-left transition-all ${
                      isCurrent 
                        ? 'bg-emerald-500/20 border-emerald-500/60 text-white shadow-md' 
                        : 'bg-white/5 border-white/5 text-slate-300 hover:border-white/20 hover:bg-white/10'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-xs">{stock.stock_name}</span>
                        <span className="text-[10px] text-slate-400 font-mono">{stock.stock_id}</span>
                      </div>
                      <div className="text-xs font-semibold text-white mt-0.5">
                        ${stock.valuation?.price || stock.Price || '-'}
                      </div>
                    </div>
                    {stock.chips?.trust_net > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-mono">
                        +{stock.chips.trust_net}
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
