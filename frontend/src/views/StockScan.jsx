import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { 
    AlertTriangle, TrendingUp, TrendingDown, DollarSign, Activity, 
    Sparkles, Star, ShieldAlert, Target, Award, Zap, Compass, CheckCircle2 
} from 'lucide-react';

function StockScan({ ticker }) {
    const [allStocks, setAllStocks] = useState({});
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [selectedTicker, setSelectedTicker] = useState(ticker || '');
    const [activeStrategy, setActiveStrategy] = useState(null); // 'watchlist' | 'smart_money' | 'growth' | 'undervalued' | 'trust_top'
    const [watchlist, setWatchlist] = useState(() => {
        try {
            return JSON.parse(localStorage.getItem('market_radar_watchlist') || '["2330", "2317", "2454"]');
        } catch {
            return ["2330", "2317", "2454"];
        }
    });

    // AI State
    const [aiReport, setAiReport] = useState(null);
    const [aiLoading, setAiLoading] = useState(false);
    const [targets, setTargets] = useState({ buy: "--", sell: "--", stop_loss: "--", win_rate: "--" });

    // Sync from parent ticker prop
    useEffect(() => {
        if (ticker) {
            setSelectedTicker(ticker);
        }
    }, [ticker]);

    // Save Watchlist
    const toggleWatchlist = (code) => {
        setWatchlist(prev => {
            const next = prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code];
            localStorage.setItem('market_radar_watchlist', JSON.stringify(next));
            return next;
        });
    };

    // 1. Initial Load of stock_data.json
    useEffect(() => {
        let isMounted = true;
        const fetchDB = async () => {
            try {
                const response = await axios.get('/stock_data.json');
                if (!isMounted) return;
                let fullData = response.data;
                if (typeof fullData === 'string') {
                    fullData = JSON.parse(fullData);
                }
                if (fullData && typeof fullData === 'object') {
                    setAllStocks(fullData);
                    // If no ticker selected, default to 2330 or first stock
                    if (!selectedTicker) {
                        const defaultCode = fullData['2330'] ? '2330' : Object.keys(fullData)[0];
                        if (defaultCode) setSelectedTicker(defaultCode);
                    }
                }
            } catch (err) {
                console.error("Failed to load stock database:", err);
            }
        };
        fetchDB();
        return () => { isMounted = false; };
    }, []);

    // 2. Select Active Stock Data
    useEffect(() => {
        if (!selectedTicker || Object.keys(allStocks).length === 0) return;

        setLoading(true);
        setError(null);
        setAiReport(null);
        setTargets({ buy: "--", sell: "--", stop_loss: "--", win_rate: "--" });

        const targetData = allStocks[selectedTicker] ||
            Object.values(allStocks).find(s => s?.stock_name?.includes(selectedTicker) || s?.stock_id === selectedTicker);

        if (targetData) {
            setData(targetData);
        } else {
            setError(`??????? (${selectedTicker})`);
        }
        setLoading(false);
    }, [selectedTicker, allStocks]);

    // 3. AI Quant Fetch
    useEffect(() => {
        if (!data || !data.stock_id) return;
        if (aiReport) return;

        let isMounted = true;
        const controller = new AbortController();
        setAiLoading(true);

        const fetchAI = async () => {
            try {
                const pe = data.valuation?.current_pe || 0;
                const sectorPe = data.valuation?.sector_pe || "N/A";
                const currentPrice = data.valuation?.price || data.Price || "N/A";
                const currentChange = data.change || data.Change || "N/A";
                const foreignNet = data.chips?.foreign_net || 0;
                const trustNet = data.chips?.trust_net || 0;
                const revYoy = data.revenue?.yoy || "N/A";
                const revMom = data.revenue?.mom || "N/A";

                const res = await axios.get('/api/analyze', {
                    params: {
                        stock_id: data.stock_id,
                        stock_name: data.stock_name,
                        pe: pe,
                        sector_pe: sectorPe,
                        price: currentPrice,
                        change: currentChange,
                        foreign_net: foreignNet,
                        trust_net: trustNet,
                        yoy: revYoy,
                        mom: revMom
                    },
                    signal: controller.signal
                });

                if (!isMounted) return;
                if (res.data) {
                    setAiReport(res.data);
                    setTargets({
                        buy: res.data.buy_price || "--",
                        sell: res.data.sell_price || "--",
                        stop_loss: res.data.stop_loss || "--",
                        win_rate: res.data.win_rate || (res.data.score ? `${res.data.score}%` : "--")
                    });
                }
            } catch (e) {
                if (!isMounted) return;
                if (e.name !== 'CanceledError') {
                    setAiReport({ report: "?? AI ???????????????????", verdict: "????" });
                }
            } finally {
                if (isMounted) setAiLoading(false);
            }
        };

        fetchAI();
        return () => { isMounted = false; controller.abort(); };
    }, [data]);

    // Strategy Screener Calculations
    const screenerResults = useMemo(() => {
        const stocksList = Object.values(allStocks);
        if (stocksList.length === 0) return [];

        switch (activeStrategy) {
            case 'watchlist':
                return stocksList.filter(s => watchlist.includes(s.stock_id));
            case 'smart_money':
                // ?? > 0 ? ?? > 0
                return stocksList.filter(s => (s.chips?.foreign_net || 0) > 0 && (s.chips?.trust_net || 0) > 0);
            case 'growth':
                // ?? YoY > 15% ? MoM > 0
                return stocksList.filter(s => (s.revenue?.yoy || 0) > 15 && (s.revenue?.mom || 0) > 0);
            case 'undervalued':
                // PE < sector_pe ? status ? Undervalued
                return stocksList.filter(s => s.valuation?.status === 'Undervalued' || (s.valuation?.current_pe > 0 && s.valuation?.current_pe < (s.valuation?.sector_pe || 20)));
            case 'trust_top':
                // ?????? Top 8
                return [...stocksList].sort((a, b) => (b.chips?.trust_net || 0) - (a.chips?.trust_net || 0)).slice(0, 8);
            default:
                return [];
        }
    }, [activeStrategy, allStocks, watchlist]);

    // Construct Pseudo Technical MA Data based on valuation and history
    const technicalData = useMemo(() => {
        if (!data) return [];
        const basePrice = data.valuation?.price || 100;
        const pts = [];
        // Generate a 20-day visual simulation curve based on current momentum
        const momRatio = (data.revenue?.mom || 0) / 100;
        for (let i = 19; i >= 0; i--) {
            const dayOffset = (19 - i);
            const noise = Math.sin(dayOffset * 0.8) * (basePrice * 0.02);
            const trend = (dayOffset - 10) * (basePrice * (momRatio > 0 ? 0.004 : -0.002));
            const p = Math.round((basePrice - trend + noise) * 10) / 10;
            const ma20 = Math.round((basePrice * 0.98 + (noise * 0.4)) * 10) / 10;
            const ma60 = Math.round((basePrice * 0.96) * 10) / 10;
            pts.push({
                day: `D-${i}`,
                price: i === 0 ? basePrice : p,
                MA20: ma20,
                MA60: ma60
            });
        }
        return pts;
    }, [data]);

    if (loading) return (
        <div className="flex flex-col items-center justify-center p-20 text-muted opacity-80">
            <Activity className="w-10 h-10 animate-spin mb-4 text-primary" />
            <span className="animate-pulse">????????????...</span>
        </div>
    );

    if (error) return (
        <div className="flex flex-col items-center justify-center p-20 text-danger">
            <AlertTriangle className="w-10 h-10 mb-2" />
            <span>{error}</span>
        </div>
    );

    const { valuation, revenue } = data || {};
    const price = valuation?.price || 0;
    const isFavorited = data ? watchlist.includes(data.stock_id) : false;

    return (
        <div className="space-y-6">

            {/* 1. Strategy Screener Filter Bar */}
            <div className="bg-surface/80 backdrop-blur-md p-4 rounded-2xl border border-white/10 shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-semibold text-text">
                        <Compass className="w-4 h-4 text-primary" />
                        <span>??????</span>
                    </div>
                    {activeStrategy && (
                        <button 
                            onClick={() => setActiveStrategy(null)}
                            className="text-xs text-muted hover:text-white transition-colors"
                        >
                            ?????? ?
                        </button>
                    )}
                </div>

                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => setActiveStrategy(activeStrategy === 'watchlist' ? null : 'watchlist')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                            activeStrategy === 'watchlist' 
                                ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-lg shadow-amber-500/10' 
                                : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
                        }`}
                    >
                        <Star className={`w-3.5 h-3.5 ${activeStrategy === 'watchlist' ? 'fill-amber-400 text-amber-400' : 'text-amber-400'}`} />
                        <span>???? ({watchlist.length})</span>
                    </button>

                    <button
                        onClick={() => setActiveStrategy(activeStrategy === 'smart_money' ? null : 'smart_money')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                            activeStrategy === 'smart_money' 
                                ? 'bg-red-500/20 border-red-500/50 text-red-300 shadow-lg shadow-red-500/10' 
                                : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
                        }`}
                    >
                        <Zap className="w-3.5 h-3.5 text-red-400" />
                        <span>?? ???? (??+??)</span>
                    </button>

                    <button
                        onClick={() => setActiveStrategy(activeStrategy === 'growth' ? null : 'growth')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                            activeStrategy === 'growth' 
                                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-lg shadow-emerald-500/10' 
                                : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
                        }`}
                    >
                        <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                        <span>?? ???? (YoY &gt; 15%)</span>
                    </button>

                    <button
                        onClick={() => setActiveStrategy(activeStrategy === 'undervalued' ? null : 'undervalued')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                            activeStrategy === 'undervalued' 
                                ? 'bg-blue-500/20 border-blue-500/50 text-blue-300 shadow-lg shadow-blue-500/10' 
                                : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
                        }`}
                    >
                        <Award className="w-3.5 h-3.5 text-blue-400" />
                        <span>?? ???? (PE????)</span>
                    </button>

                    <button
                        onClick={() => setActiveStrategy(activeStrategy === 'trust_top' ? null : 'trust_top')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                            activeStrategy === 'trust_top' 
                                ? 'bg-purple-500/20 border-purple-500/50 text-purple-300 shadow-lg shadow-purple-500/10' 
                                : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
                        }`}
                    >
                        <Target className="w-3.5 h-3.5 text-purple-400" />
                        <span>?? ???? Top</span>
                    </button>
                </div>

                {/* Screener Results Horizontal Carousel */}
                {activeStrategy && (
                    <div className="pt-2 border-t border-white/5">
                        <div className="flex gap-2.5 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-white/10">
                            {screenerResults.length === 0 ? (
                                <div className="text-xs text-muted py-2 px-1">???????????</div>
                            ) : (
                                screenerResults.map(stock => {
                                    const isCurrent = stock.stock_id === data?.stock_id;
                                    return (
                                        <button
                                            key={stock.stock_id}
                                            onClick={() => setSelectedTicker(stock.stock_id)}
                                            className={`shrink-0 flex items-center gap-2.5 px-3 py-2 rounded-xl border text-left transition-all ${
                                                isCurrent 
                                                    ? 'bg-primary/20 border-primary text-white shadow-md' 
                                                    : 'bg-neutral-900/60 border-white/5 text-slate-300 hover:border-white/20 hover:bg-neutral-800'
                                            }`}
                                        >
                                            <div>
                                                <div className="flex items-center gap-1.5">
                                                    <span className="font-bold text-xs">{stock.stock_name}</span>
                                                    <span className="text-[10px] text-muted">{stock.stock_id}</span>
                                                </div>
                                                <div className="text-xs font-semibold text-text mt-0.5">
                                                    ${stock.valuation?.price || stock.Price || '-'}
                                                </div>
                                            </div>
                                            {stock.chips?.trust_net > 0 && (
                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-mono">
                                                    ??+{stock.chips.trust_net}
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

            {/* 2. Stock Header Profile & Star */}
            {data && (
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface p-6 rounded-2xl border border-white/5 shadow-lg">
                    <div className="flex items-center gap-4">
                        <div>
                            <div className="flex items-center gap-2.5">
                                <h1 className="text-3xl font-extrabold text-text tracking-tight">
                                    {data.stock_name}
                                </h1>
                                <span className="text-lg font-mono text-muted px-2 py-0.5 rounded-lg bg-white/5 border border-white/10">
                                    {data.stock_id}
                                </span>
                                <button
                                    onClick={() => toggleWatchlist(data.stock_id)}
                                    className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                                    title={isFavorited ? "??????" : "?????"}
                                >
                                    <Star className={`w-5 h-5 transition-transform active:scale-125 ${isFavorited ? 'fill-amber-400 text-amber-400' : 'text-slate-500 hover:text-slate-300'}`} />
                                </button>
                            </div>
                            <p className="text-sm text-muted mt-1">
                                ?????????? ? ??????
                            </p>
                        </div>
                    </div>

                    <div className="flex items-baseline gap-3">
                        <span className="text-4xl font-extrabold text-text font-mono">
                            ${price ? price.toFixed(1) : "-"}
                        </span>
                        <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-white/5 border border-white/10 text-muted">
                            {valuation?.status === 'Undervalued' ? "??????" : "????"}
                        </span>
                    </div>
                </div>
            )}

            {/* 3. Deep Quant AI Hedge Fund Analysis Card */}
            <div className="bg-gradient-to-br from-surface to-neutral-950 p-6 rounded-2xl border border-primary/20 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-80 h-80 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 relative z-10">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-xl bg-primary/10 border border-primary/30 text-primary">
                            <Sparkles className="w-6 h-6 animate-pulse" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                ???? AI ???????
                                {aiLoading && <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary animate-pulse">???...</span>}
                            </h2>
                            <p className="text-xs text-muted">????????????????????</p>
                        </div>
                    </div>

                    {aiReport && (
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-muted">AI ?????</span>
                            <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                                aiReport.verdict?.includes('?') ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                                aiReport.verdict?.includes('?') ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                                'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                            }`}>
                                {aiReport.verdict || "????"}
                            </span>
                        </div>
                    )}
                </div>

                {/* 4 Quant Metric Pillars */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6 relative z-10">
                    <div className="bg-neutral-900/80 p-3.5 rounded-xl border border-white/5">
                        <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
                            <Target className="w-3.5 h-3.5 text-emerald-400" />
                            <span>??????</span>
                        </div>
                        <div className="text-base md:text-lg font-mono font-bold text-emerald-400">
                            {targets.buy}
                        </div>
                    </div>

                    <div className="bg-neutral-900/80 p-3.5 rounded-xl border border-white/5">
                        <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
                            <TrendingUp className="w-3.5 h-3.5 text-red-400" />
                            <span>?????</span>
                        </div>
                        <div className="text-base md:text-lg font-mono font-bold text-red-400">
                            {targets.sell}
                        </div>
                    </div>

                    <div className="bg-neutral-900/80 p-3.5 rounded-xl border border-white/5">
                        <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
                            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                            <span>?????</span>
                        </div>
                        <div className="text-base md:text-lg font-mono font-bold text-amber-400">
                            {targets.stop_loss}
                        </div>
                    </div>

                    <div className="bg-neutral-900/80 p-3.5 rounded-xl border border-white/5">
                        <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
                            <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                            <span>??????</span>
                        </div>
                        <div className="text-base md:text-lg font-mono font-bold text-blue-400">
                            {targets.win_rate}
                        </div>
                    </div>
                </div>

                {/* Detailed Analysis Text */}
                <div className="bg-neutral-900/50 p-5 rounded-xl border border-white/5 text-sm text-slate-300 leading-relaxed relative z-10 whitespace-pre-wrap">
                    {aiLoading ? (
                        <div className="flex items-center gap-2 text-muted py-4">
                            <Activity className="w-4 h-4 animate-spin text-primary" />
                            <span>?????????????????...</span>
                        </div>
                    ) : (
                        aiReport?.report || aiReport?.content || "??????"
                    )}
                </div>
            </div>

            {/* 4. Three Fundamental & Technical Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* Valuation */}
                <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg">
                    <h3 className="text-muted text-sm font-medium mb-1">??????? (PE)</h3>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-bold text-text">{valuation?.current_pe?.toFixed(1) || "-"}</span>
                        <span className="text-sm text-muted mb-1">?</span>
                    </div>
                    <div className={`mt-4 inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                        valuation?.status === 'Undervalued' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                        valuation?.status === 'High Premium' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                        'bg-gray-500/10 text-gray-400 border-gray-500/20'
                    }`}>
                        {valuation?.status === 'Undervalued' ? "?? ????" :
                            valuation?.status === 'High Premium' ? "?? ????" :
                            valuation?.status === 'Fair Value' ? "?? ????" : "???..."}
                    </div>
                    <p className="mt-2 text-xs text-muted">???????: {valuation?.sector_pe?.toFixed(2) || "20.0"} ?</p>
                </div>

                {/* Revenue Momentum */}
                <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg">
                    <h3 className="text-muted text-sm font-medium mb-1">???? (???)</h3>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-bold text-text">{revenue?.revenue ? (revenue.revenue / 100000000).toFixed(1) : "-"}</span>
                        <span className="text-sm text-muted mb-1">? TWD</span>
                    </div>
                    <div className="mt-4 flex gap-4">
                        <div className={`flex items-center gap-1 text-sm ${revenue?.mom > 0 ? 'text-red-400' : 'text-green-400'}`}>
                            {revenue?.mom > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                            <span>?? {revenue?.mom}%</span>
                        </div>
                        <div className={`flex items-center gap-1 text-sm ${revenue?.yoy > 0 ? 'text-red-400' : 'text-green-400'}`}>
                            <span>?? {revenue?.yoy}%</span>
                        </div>
                    </div>
                </div>

                {/* Smart Money Chips */}
                <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg">
                    <h3 className="text-muted text-sm font-medium mb-1">????????</h3>
                    <div className="flex items-end gap-2">
                        <span className={`text-3xl font-bold ${((data?.chips?.foreign_net || 0) + (data?.chips?.trust_net || 0)) > 0 ? 'text-red-400' : 'text-green-400'}`}>
                            {((data?.chips?.foreign_net || 0) + (data?.chips?.trust_net || 0)) > 0 ? "????" : "????"}
                        </span>
                    </div>
                    <div className="mt-4 text-xs text-muted space-y-1">
                        <div>
                            ?????: <span className={data?.chips?.foreign_net > 0 ? 'text-red-400 font-mono' : 'text-green-400 font-mono'}>
                                {data?.chips?.foreign_net > 0 ? '+' : ''}{data?.chips?.foreign_net?.toLocaleString() || 0} ?
                            </span>
                        </div>
                        <div>
                            ?????: <span className={data?.chips?.trust_net > 0 ? 'text-red-400 font-mono' : 'text-green-400 font-mono'}>
                                {data?.chips?.trust_net > 0 ? '+' : ''}{data?.chips?.trust_net?.toLocaleString() || 0} ?
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 5. Technical Trend & MA Chart */}
            <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-emerald-400" />
                        ??????? (20MA / 60MA)
                    </h3>
                    <div className="flex items-center gap-3 text-xs">
                        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-emerald-400 inline-block"></span>???</span>
                        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-amber-400 inline-block"></span>20MA ??</span>
                        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-400 inline-block"></span>60MA ??</span>
                    </div>
                </div>
                <div style={{ width: '100%', height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={technicalData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" opacity={0.5} />
                            <XAxis dataKey="day" stroke="#71717a" fontSize={11} tickLine={false} />
                            <YAxis domain={['auto', 'auto']} stroke="#71717a" fontSize={11} tickLine={false} />
                            <Tooltip contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', color: '#f4f4f5' }} />
                            <Line type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2.5} dot={false} name="??" />
                            <Line type="monotone" dataKey="MA20" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="20MA" />
                            <Line type="monotone" dataKey="MA60" stroke="#a855f7" strokeWidth={1.5} dot={false} name="60MA" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* 6. Revenue Bar Chart */}
            <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-secondary" />
                    ? 12 ??????
                </h3>
                <div style={{ width: '100%', height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={revenue?.history?.length > 0 ? revenue.history : (revenue ? [{ date: revenue.date, revenue: revenue.revenue }] : [])}>
                            <XAxis
                                dataKey="date"
                                tickFormatter={(val) => typeof val === 'string' ? val.slice(-2) : String(val ?? '')}
                                stroke="#71717a"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                stroke="#71717a"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(value) => `${(value / 100000000).toFixed(0)}?`}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', color: '#f4f4f5' }}
                                cursor={{ fill: '#27272a' }}
                                formatter={(val) => [`${(val / 100000000).toFixed(2)}?`, "??"]}
                            />
                            <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={36} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

        </div>
    );
}

export default StockScan;
