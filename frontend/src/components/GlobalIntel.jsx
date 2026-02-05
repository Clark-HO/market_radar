import React, { useState, useEffect } from 'react';
import { Calendar, TrendingUp, AlertTriangle, Zap, Clock, Activity, ArrowRight, TrendingDown, HelpCircle, X } from 'lucide-react';

const GlobalIntel = () => {
    const [data, setData] = useState(null);
    const [selectedEvent, setSelectedEvent] = useState(null);
    const [showLegend, setShowLegend] = useState(false);

    useEffect(() => {
        // Fetch from local public folder (Vercel Root)
        fetch('/global_data.json')
            .then(res => res.json())
            .then(d => {
                setData(d);
                if (d.events && d.events.length > 0) {
                    // Default select the first "Imminent" event
                    const imminent = d.events.find(e => e.status === 'Imminent');
                    setSelectedEvent(imminent || d.events[0]);
                }
            })
            .catch(err => console.error("Failed to load global data", err));
    }, []);


    if (!data) return (
        <div className="flex flex-col items-center justify-center p-20 text-muted animate-pulse">
            <Activity className="w-10 h-10 mb-4 text-secondary" />
            <div>正在建立全球戰情連線...</div>
        </div>
    );

    return (
        <div className="min-h-screen text-white p-3 md:p-6 animate-in fade-in duration-500 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-end mb-6 md:mb-8 border-b border-white/10 pb-4 md:pb-6">
                <div>
                    <h1 className="text-2xl md:text-3xl lg:text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-500 tracking-tight flex items-center gap-3">
                        <Activity className="w-6 h-6 md:w-8 md:h-8 text-blue-400" />
                        全球戰情室 (Global Intel)
                    </h1>
                    <p className="text-slate-400 text-xs md:text-sm mt-2 font-light tracking-wide">
                        美台供應鏈連動分析 • 科技盛會戰略地圖
                    </p>
                </div>
                <div className="text-right mt-4 md:mt-0 w-full md:w-auto">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] md:text-xs text-slate-400 font-mono w-full md:w-auto justify-center md:justify-start">
                        <span className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-green-500 animate-pulse"></span>
                        更新時間: {data.last_updated}
                    </div>
                </div>
            </div>

            {/* 1. Timeline Scroller */}
            <div className="relative mb-6 md:mb-8 group">
                <div className="absolute left-0 top-0 bottom-0 w-8 md:w-20 bg-gradient-to-r from-background to-transparent z-10 pointer-events-none"></div>
                <div className="absolute right-0 top-0 bottom-0 w-8 md:w-20 bg-gradient-to-l from-background to-transparent z-10 pointer-events-none"></div>

                <div className="flex overflow-x-auto space-x-4 md:space-x-6 pb-6 md:pb-8 px-2 md:px-4 scrollbar-none snap-x snap-mandatory">
                    {data.events.map((evt, idx) => {
                        const isSelected = selectedEvent && selectedEvent.event === evt.event;
                        const isImminent = evt.status === 'Imminent';

                        // Translate Status
                        let statusText = evt.status;
                        if (evt.status === "Imminent") statusText = "倒數中";
                        if (evt.status === "Upcoming") statusText = "即將到來";
                        if (evt.status === "Ongoing") statusText = "進行中";
                        if (evt.status === "Finished") statusText = "已結束";

                        return (
                            <div
                                key={idx}
                                onClick={() => setSelectedEvent(evt)}
                                className={`
                    min-w-[260px] md:min-w-[300px] p-4 md:p-5 rounded-2xl cursor-pointer transition-all duration-300 snap-center
                    border relative overflow-hidden group/card
                    ${isSelected
                                        ? 'bg-blue-950/30 border-blue-500/50 shadow-[0_0_30px_rgba(59,130,246,0.2)] scale-[1.02]'
                                        : 'bg-surface border-white/5 hover:bg-white/5 hover:border-white/20'
                                    }
                `}
                            >
                                {/* Glow Effect */}
                                {isSelected && <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent pointer-events-none" />}

                                <div className="flex justify-between items-start mb-3 relative z-10">
                                    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${isImminent ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30'
                                        : evt.status === 'Ongoing' ? 'bg-green-500/20 text-green-500 border border-green-500/30'
                                            : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                        }`}>
                                        {statusText}
                                    </span>
                                    <span className={`text-xs font-mono flex items-center gap-1.5 ${isImminent ? 'text-yellow-500 font-bold' : 'text-slate-500'}`}>
                                        <Clock size={12} /> 倒數 {evt.days_to_go} 天
                                    </span>
                                </div>

                                <h3 className={`font-bold text-base md:text-lg truncate mb-1 relative z-10 ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                                    {evt.event}
                                </h3>
                                <div className="text-xs text-slate-500 font-mono mb-3 relative z-10">{evt.date}</div>

                                <div className="text-xs text-slate-400 border-t border-white/5 pt-3 line-clamp-2 relative z-10 group-hover/card:text-slate-300 transition-colors">
                                    {evt.theme}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* 2. Main Matrix Area */}
            {selectedEvent && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8 animate-in slide-in-from-bottom-5 duration-700">

                    {/* Info Card */}
                    <div className="lg:col-span-3 bg-surface p-6 md:p-8 rounded-2xl md:rounded-3xl border border-white/5 relative overflow-hidden">
                        {/* Background Decoration */}
                        <div className="absolute top-0 right-0 -mt-20 -mr-20 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>

                        <div className="relative z-10">
                            <h2 className="text-2xl md:text-3xl font-bold mb-4 flex items-center gap-3 text-white">
                                <Calendar className="text-blue-400 w-6 h-6 md:w-8 md:h-8" />
                                {selectedEvent.event}
                            </h2>
                            <p className="text-slate-300 mb-6 text-sm md:text-lg leading-relaxed max-w-4xl">{selectedEvent.description}</p>

                            <div className="flex flex-wrap gap-3 md:gap-4">
                                <div className="bg-black/40 px-4 md:px-5 py-2 md:py-3 rounded-xl border border-white/5 flex flex-col flex-1 md:flex-none">
                                    <span className="text-slate-500 text-[10px] uppercase tracking-widest mb-1">核心主題</span>
                                    <span className="text-blue-200 font-medium text-sm md:text-base">{selectedEvent.theme}</span>
                                </div>
                                <div className="bg-black/40 px-4 md:px-5 py-2 md:py-3 rounded-xl border border-white/5 flex flex-col flex-1 md:flex-none">
                                    <span className="text-slate-500 text-[10px] uppercase tracking-widest mb-1">展會日期</span>
                                    <span className="text-slate-200 font-mono text-sm md:text-base">{selectedEvent.date} ~ {selectedEvent.end_date}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Supply Chain Chains */}
                    <div className="lg:col-span-3 space-y-4 md:space-y-6">
                        <div className="flex items-center gap-3 mb-4 md:mb-6">
                            <h3 className="text-lg md:text-xl font-bold text-slate-200 border-l-4 border-blue-500 pl-4">
                                供應鏈戰略地圖
                            </h3>
                            <button
                                onClick={() => setShowLegend(true)}
                                className="flex items-center gap-1 text-[10px] md:text-xs font-normal text-slate-400 hover:text-white px-2 py-1 bg-white/5 hover:bg-white/10 rounded transition-colors"
                            >
                                <HelpCircle size={12} />
                                <span>指標說明</span>
                            </button>
                            <span className="text-[10px] md:text-xs font-normal text-slate-500 px-2 py-1 bg-white/5 rounded">美股領頭羊 ➔ 台廠受惠股</span>
                        </div>


                        {selectedEvent.chains.map((chain, cIdx) => (
                            <div key={cIdx} className="bg-surface/50 rounded-2xl p-4 md:p-6 border border-white/5 hover:border-white/10 transition-colors flex flex-col lg:flex-row gap-6 lg:gap-8 items-stretch group">

                                {/* US Leader */}
                                <div className="lg:w-1/4 bg-black/20 rounded-xl p-4 md:p-5 flex flex-row lg:flex-col items-center lg:items-start justify-between lg:justify-center border-l-2 border-blue-500 relative overflow-hidden gap-4">
                                    <div className="absolute top-0 right-0 p-4 opacity-5 hidden lg:block">
                                        <span className="text-6xl font-black text-white">{chain.us_stock.symbol[0]}</span>
                                    </div>

                                    <div className="flex flex-col">
                                        <div className="text-[10px] text-blue-400 uppercase tracking-widest mb-1 lg:mb-2 font-bold z-10">美股指標</div>
                                        <div className="text-xl md:text-2xl font-black text-white z-10">{chain.us_stock.name}</div>
                                        <div className="text-xs md:text-sm text-slate-400 mb-0 lg:mb-3 z-10 font-mono">{chain.us_stock.symbol}</div>
                                    </div>

                                    <div className={`text-lg md:text-xl font-mono font-bold flex items-center gap-2 z-10 ${chain.us_stock.change >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                                        {chain.us_stock.price}
                                        <span className={`text-xs md:text-sm px-1.5 py-0.5 rounded ${chain.us_stock.change >= 0 ? 'bg-red-500/20' : 'bg-green-500/20'}`}>
                                            {chain.us_stock.change > 0 ? '+' : ''}{chain.us_stock.change}%
                                        </span>
                                    </div>
                                </div>

                                {/* Arrow (Desktop) */}
                                <div className="hidden lg:flex flex-col justify-center items-center text-slate-600 opacity-50 group-hover:opacity-100 transition-opacity group-hover:translate-x-1 duration-300">
                                    <ArrowRight size={24} />
                                </div>

                                {/* Arrow (Mobile) */}
                                <div className="lg:hidden flex justify-center -my-2 opacity-30">
                                    <TrendingDown size={20} />
                                </div>

                                {/* TW Followers */}
                                <div className="lg:w-3/4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
                                    {chain.tw_stocks.map((tw, tIdx) => {
                                        // Signal Color Logic
                                        let signalBorder = "border-white/5";
                                        let signalBg = "bg-white/5";
                                        let signalIcon = null;
                                        let signalText = tw.signal;

                                        // Translate Signals
                                        if (tw.signal.includes("Lagging")) { // Buy Opp
                                            signalBorder = "border-green-500/50";
                                            signalBg = "bg-green-500/10";
                                            signalIcon = <Zap size={14} className="text-green-400 animate-pulse" />;
                                            signalText = "⚡ 補漲機會";
                                        } else if (tw.signal.includes("Risk")) {
                                            signalBorder = "border-red-500/50";
                                            signalBg = "bg-red-500/10";
                                            signalIcon = <AlertTriangle size={14} className="text-red-400" />;
                                            signalText = "⚠️ 風險警示";
                                        } else if (tw.signal.includes("Rally")) {
                                            signalBorder = "border-orange-500/50";
                                            signalBg = "bg-orange-500/10";
                                            signalIcon = <TrendingUp size={14} className="text-orange-400" />;
                                            signalText = "🔥 同步噴出";
                                        } else {
                                            signalText = "無顯著訊號";
                                        }

                                        return (
                                            <div key={tIdx} className={`p-3 md:p-4 rounded-xl border ${signalBorder} ${signalBg} relative group/tw hover:scale-105 transition-transform duration-300`}>
                                                <div className="flex justify-between items-start mb-2">
                                                    <div className="flex items-center gap-2">
                                                        <div className="font-bold text-base md:text-lg text-white">{tw.ticker}</div>
                                                        {signalIcon}
                                                    </div>
                                                    <div className={`text-sm font-mono font-bold ${tw.change >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                                                        {tw.change > 0 ? '+' : ''}{tw.change}%
                                                    </div>
                                                </div>

                                                <div className="flex justify-between items-end">
                                                    <div className="text-[10px] md:text-xs text-slate-500">{chain.tw_sector}</div>
                                                    <div className="font-mono text-slate-300 text-sm">{tw.price}</div>
                                                </div>

                                                {tw.signal !== 'Neutral' && (
                                                    <div className="absolute top-0 right-0 -mt-2 -mr-2 bg-slate-900/90 backdrop-blur text-[10px] px-2 py-0.5 rounded-full border border-slate-700 shadow-xl z-20 whitespace-nowrap">
                                                        {signalText}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>

                            </div>
                        ))}
                    </div>

                </div>
            )}

            {/* Legend Modal */}
            {showLegend && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200" onClick={() => setShowLegend(false)}>
                    <div className="bg-neutral-900 border border-white/10 rounded-2xl max-w-md w-full p-6 relative shadow-2xl animate-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
                        <button
                            onClick={() => setShowLegend(false)}
                            className="absolute top-4 right-4 text-slate-400 hover:text-white"
                        >
                            <X size={20} />
                        </button>
                        <h3 className="text-lg font-bold mb-6 flex items-center gap-2 text-white">
                            <Activity size={20} className="text-blue-400" /> 信號指標說明
                        </h3>

                        <div className="space-y-4">
                            {/* Lagging */}
                            <div className="flex gap-4 p-3 rounded-xl bg-green-500/5 border border-green-500/20">
                                <div className="mt-1">
                                    <Zap size={20} className="text-green-400" />
                                </div>
                                <div>
                                    <div className="text-green-400 font-bold mb-1">⚡ 補漲機會 (Lagging)</div>
                                    <div className="text-xs text-slate-300 mb-2">美股大漲 (&gt;2%) 但台股尚未跟上 (&lt;1%)。短線可能存在補漲空間。</div>
                                    <div className="text-[10px] text-slate-500 font-mono bg-black/20 p-1 rounded inline-block">策略: 觀察開低走高</div>
                                </div>
                            </div>

                            {/* Rally */}
                            <div className="flex gap-4 p-3 rounded-xl bg-orange-500/5 border border-orange-500/20">
                                <div className="mt-1">
                                    <TrendingUp size={20} className="text-orange-400" />
                                </div>
                                <div>
                                    <div className="text-orange-400 font-bold mb-1">🔥 同步噴出 (Sympathy Rally)</div>
                                    <div className="text-xs text-slate-300 mb-2">美台同步大漲 (&gt;2%)。資金全面湧入該題材，多頭氣勢最強。</div>
                                    <div className="text-[10px] text-slate-500 font-mono bg-black/20 p-1 rounded inline-block">策略: 順勢操作</div>
                                </div>
                            </div>

                            {/* Risk */}
                            <div className="flex gap-4 p-3 rounded-xl bg-red-500/5 border border-red-500/20">
                                <div className="mt-1">
                                    <AlertTriangle size={20} className="text-red-400" />
                                </div>
                                <div>
                                    <div className="text-red-400 font-bold mb-1">⚠️ 風險警示 (Risk Alert)</div>
                                    <div className="text-xs text-slate-300 mb-2">美股領頭羊重挫 (&lt;-2%)。台股供應鏈面臨補跌或外資提款壓力。</div>
                                    <div className="text-[10px] text-slate-500 font-mono bg-black/20 p-1 rounded inline-block">策略: 保守觀望</div>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 text-[10px] text-center text-slate-600">
                            * 訊號由系統即時計算美台股連動性後產生，僅供參考。
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default GlobalIntel;
