import { useState, useEffect } from 'react';
import axios from 'axios';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { AlertTriangle, TrendingUp, TrendingDown, DollarSign, Activity, Sparkles } from 'lucide-react';


function StockScan({ ticker }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [debouncedTicker, setDebouncedTicker] = useState(ticker);

    // New State for AI (Moved to top to prevent Hook Order Error)
    const [aiReport, setAiReport] = useState(null);
    const [aiLoading, setAiLoading] = useState(false);
    const [targets, setTargets] = useState({ buy: "--", sell: "--" });

    // Debounce Ticker
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedTicker(ticker);
        }, 800);
        return () => clearTimeout(handler);
    }, [ticker]);

    // Data Fetch
    useEffect(() => {
        if (!debouncedTicker) return;

        let isMounted = true;
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            setData(null);
            // Reset AI when ticker changes
            setAiReport(null);
            setTargets({ buy: "--", sell: "--" });

            try {

                // Serverless: Fetch full database (2.5MB) from local public
                const response = await axios.get('/stock_data.json');

                if (!isMounted) return;

                let fullData = response.data;
                // Safety: Ensure it's an object
                if (typeof fullData === 'string') {
                    try { fullData = JSON.parse(fullData); } catch (e) { 
                        setError('資料格式錯誤'); 
                        return; 
                    }
                }

                if (!fullData || typeof fullData !== 'object') {
                    setError('資料格式錯誤');
                    return;
                }

                const targetData = fullData[debouncedTicker] ||
                    Object.values(fullData).find(s => s?.stock_name?.includes(debouncedTicker) || s?.stock_id === debouncedTicker);

                if (targetData) {
                    setData(targetData);
                } else {
                    setError(`查無此股資料 (${debouncedTicker})。資料庫筆數: ${Object.keys(fullData).length}`);
                }

            } catch (err) {
                console.error(err);
                if (isMounted) setError(`無法連線至雲端數據庫: ${err.message}`);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchData();

        return () => { isMounted = false; };
    }, [debouncedTicker]);

    // AI on-demand Fetch
    useEffect(() => {
        if (!data || !data.stock_id) return;
        if (aiReport) return;

        let isMounted = true;
        const controller = new AbortController();
        setAiLoading(true);

        const fetchAI = async () => {
            try {
                const pe = data.valuation?.current_pe || 0;
                const currentPrice = data.valuation?.price || data.Price || "N/A";
                const currentChange = data.change || data.Change || "N/A";

                const res = await axios.get('/api/analyze', {
                    params: {
                        stock_id: data.stock_id,
                        stock_name: data.stock_name,
                        pe: pe,
                        price: currentPrice,
                        change: currentChange
                    },
                    signal: controller.signal
                });
                if (!isMounted) return;
                if (res.data) {
                    setAiReport(res.data);
                    if (res.data.buy_price) {
                        setTargets({
                            buy: res.data.buy_price || "--",
                            sell: res.data.sell_price || "--"
                        });
                    }
                }
            } catch (e) {
                if (!isMounted) return;
                if (e.name !== 'CanceledError') {
                    setAiReport({ report: "⚠️ AI 分析暫時無法使用，請稍後再試。", verdict: "Error" });
                    setTargets({ buy: "--", sell: "--" });
                }
            } finally {
                if (isMounted) setAiLoading(false);
            }
        };

        fetchAI();

        return () => { isMounted = false; controller.abort(); };
    }, [data]);

    if (loading) return (
        <div className="flex flex-col items-center justify-center p-20 text-muted opacity-80">
            <Activity className="w-10 h-10 animate-spin mb-4 text-primary" />
            <span className="animate-pulse">正在掃描市場數據 (Dashboard API)...</span>
        </div>
    );

    if (error) return (
        <div className="flex flex-col items-center justify-center p-20 text-danger">
            <AlertTriangle className="w-10 h-10 mb-2" />
            <span>{error}</span>
        </div>
    );

    if (!data && !loading && !error) return (
        <div className="flex flex-col items-center justify-center p-20 text-slate-500">
            <Activity className="w-16 h-16 mb-4 opacity-30" />
            <p className="text-lg font-medium">輸入股票代號開始分析</p>
            <p className="text-sm mt-2 text-slate-600">例如：2330（台積電）、2317（鴻海）</p>
        </div>
    );

    const { valuation, revenue } = data || {};
    const price = valuation?.price || 0;
    // Mock change % since it's not in DB yet (can't easily add without schema change, will rely on AI or PE status)
    // Actually user asked to display it. Using PE status as proxy color/mock or just Price.

    // Check if chips data exists (not null/None)
    const showChips = data?.chips?.foreign_net !== undefined && data?.chips?.foreign_net !== null;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">

            {/* Header: Stock Info & Price */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-2">
                <div className="flex items-center gap-3">
                    <div className="text-3xl font-bold text-white tracking-tight">
                        {data?.stock_id} {data?.stock_name}
                    </div>
                    {price > 0 && (
                        <div className="flex items-baseline gap-2 bg-white/5 px-3 py-1 rounded-lg">
                            <span className="text-2xl font-mono text-blue-400">${price.toFixed(1)}</span>
                            {/* Note: Change % not available in current JSON schema, hiding to avoid fake data */}
                        </div>
                    )}
                </div>
                <div className="flex gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${aiReport?.verdict?.includes('強') ? 'bg-red-500/20 text-red-400 border-red-500/30' : 'bg-blue-500/20 text-blue-400 border-blue-500/30'}`}>
                        {aiReport?.verdict || "AI 分析中"}
                    </span>
                </div>
            </div>

            {/* AI Price Targets Block */}
            {targets.buy !== "--" && (
                <div className="flex justify-center gap-4 mt-4 mb-6">
                    {/* Buy Target (Green/Safe) */}
                    <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-3 px-6 shadow-sm text-center">
                        <p className="text-xs text-green-300 font-medium mb-1">AI 建議買進</p>
                        <p className="text-xl font-bold text-green-400">{targets.buy}</p>
                    </div>

                    {/* Sell Target (Red/Profit) */}
                    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 px-6 shadow-sm text-center">
                        <p className="text-xs text-red-300 font-medium mb-1">AI 建議賣出</p>
                        <p className="text-xl font-bold text-red-400">{targets.sell}</p>
                    </div>
                </div>
            )}

            {/* Top Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* AI Diagnosis Card */}
                <div className="md:col-span-3 bg-blue-900/20 p-6 rounded-xl border border-blue-500/30 shadow-lg relative overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="absolute top-0 right-0 p-8 opacity-10">
                        <Sparkles className="w-48 h-48 text-blue-400" />
                    </div>

                    <div className="relative z-10 w-full">
                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-blue-400" />
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                                AI 智能診斷報告
                            </span>
                        </h3>

                        {aiLoading ? (
                            <div className="flex items-center gap-2 text-blue-300 animate-pulse">
                                <Activity className="w-4 h-4 animate-spin" />
                                <span>🤖 AI 正在分析 (Gemini 1.5)...</span>
                            </div>
                        ) : (
                            <div className="bg-neutral-950/60 p-4 rounded-lg border border-white/5 text-sm md:text-base leading-relaxed text-slate-200 font-mono whitespace-pre-wrap shadow-inner w-full">
                                {aiReport?.report || "等待分析..."}
                            </div>
                        )}
                    </div>
                </div>
                {/* Valuation Card */}
                <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg relative overflow-hidden group hover:border-primary/20 transition-all">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <DollarSign className="w-24 h-24" />
                    </div>
                    <h3 className="text-muted text-sm font-medium mb-1">基本面 - 估值雷達</h3>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-bold text-text">{valuation?.current_pe ? valuation.current_pe.toFixed(2) : "N/A"}</span>
                        <span className="text-sm text-muted mb-1">倍 (本益比)</span>
                    </div>
                    <div className={`mt-4 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${valuation?.status === 'Undervalued' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                        valuation?.status === 'High Premium' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                            'bg-gray-500/10 text-gray-400 border-gray-500/20'
                        }`}>
                        {valuation?.status === 'Undervalued' ? "💎 價值低估" :
                            valuation?.status === 'High Premium' ? "🔥 溢價過高" :
                                valuation?.status === 'Fair Value' ? "⚖️ 合理評價" : "分析中..."}
                    </div>
                    <p className="mt-2 text-xs text-muted">同業平均: {valuation?.sector_pe?.toFixed(2) || "-"}倍</p>
                </div>

                {/* Revenue Momentum */}
                <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg hover:border-secondary/20 transition-all">
                    <h3 className="text-muted text-sm font-medium mb-1">營收動能 (月)</h3>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-bold text-text">{revenue?.revenue ? (revenue.revenue / 100000000).toFixed(1) : "-"}</span>
                        <span className="text-sm text-muted mb-1">億 TWD</span>
                    </div>
                    <div className="mt-4 flex gap-4">
                        <div className={`flex items-center gap-1 text-sm ${revenue?.mom > 0 ? 'text-red-400' : 'text-green-400'}`}>
                            {revenue?.mom > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                            <span>月增 {revenue?.mom}%</span>
                        </div>
                        <div className={`flex items-center gap-1 text-sm ${revenue?.yoy > 0 ? 'text-red-400' : 'text-green-400'}`}>
                            <span>年增 {revenue?.yoy}%</span>
                        </div>
                    </div>
                </div>

                {/* Chip Analysis (Real) */}
                {/* 3. Condition: Only show if data is available */}
                {showChips && (
                    <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg hover:border-accent/20 transition-all">
                        <h3 className="text-muted text-sm font-medium mb-1">籌碼透視 - 聰明錢</h3>
                        <div className="flex items-end gap-2">
                            {/* Simplified Analysis Text based on Net Buy */}
                            <span className={`text-3xl font-bold ${((data.chips.foreign_net || 0) + (data.chips.trust_net || 0)) > 0 ? 'text-red-400' : 'text-green-400'}`}>
                                {((data.chips.foreign_net || 0) + (data.chips.trust_net || 0)) > 0 ? "主力買超" : "主力賣超"}
                            </span>
                        </div>
                        <div className="mt-4 text-xs text-muted">
                            外資動向: <span className={data?.chips?.foreign_net > 0 ? 'text-red-400' : 'text-green-400'}>
                                {data?.chips?.foreign_net > 0 ? '+' : ''}{data?.chips?.foreign_net?.toLocaleString() || 0} 張
                            </span>
                            <br />
                            投信動向: <span className={data?.chips?.trust_net > 0 ? 'text-red-400' : 'text-green-400'}>
                                {data?.chips?.trust_net > 0 ? '+' : ''}{data?.chips?.trust_net?.toLocaleString() || 0} 張
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Revenue Chart (History) */}
            <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-secondary" />
                    近 12 個月營收趨勢
                </h3>
                <div style={{ width: '100%', height: 300 }}>
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
                                tickFormatter={(value) => `${(value / 100000000).toFixed(0)}億`}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', color: '#f4f4f5' }}
                                cursor={{ fill: '#27272a' }}
                                formatter={(val) => [`${(val / 100000000).toFixed(2)}億`, "營收"]}
                            />
                            <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

        </div >
    );
}

export default StockScan;
