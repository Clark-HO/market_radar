import { useState, useEffect } from 'react';
import axios from 'axios';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, Line } from 'recharts';
import { AlertTriangle, TrendingUp, TrendingDown, DollarSign, Activity, Sparkles } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

function StockScan({ ticker }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [debouncedTicker, setDebouncedTicker] = useState(ticker);

    // Debounce Ticker
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedTicker(ticker);
        }, 800);
        return () => clearTimeout(handler);
    }, [ticker]);

    useEffect(() => {
        if (!debouncedTicker) return;

        let isMounted = true;
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            setData(null);

            try {
                console.log(`Fetching dashboard for ${debouncedTicker}...`);

                // Single Request for EVERYTHING
                const response = await axios.get(`${API_BASE}/stock/${debouncedTicker}/dashboard`, { timeout: 30000 });

                if (!isMounted) return;

                if (response.data) {
                    setData(response.data);
                    if (!response.data.valuation && !response.data.revenue) {
                        setError("查無此股資料，請確認代號。");
                    }
                }

            } catch (err) {
                console.error(err);
                if (isMounted) setError("連線逾時或系統忙碌中。");
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchData();

        return () => { isMounted = false; };
    }, [debouncedTicker]);

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

    const { valuation, revenue } = data || {};

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* AI Diagnosis Card */}
            {data?.analysis && (
                <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-2xl relative overflow-hidden bg-gradient-to-br from-surface to-accent/5">
                    <div className="absolute top-0 right-0 p-8 opacity-5">
                        <Sparkles className="w-48 h-48" />
                    </div>

                    <div className="flex flex-col md:flex-row gap-8 relative z-10">
                        {/* Score Section */}
                        <div className="flex flex-col items-center justify-center min-w-[200px] border-b md:border-b-0 md:border-r border-white/10 pb-6 md:pb-0 md:pr-6">
                            <div className="text-sm text-secondary font-medium mb-2 tracking-widest uppercase flex items-center gap-2">
                                <Sparkles className="w-4 h-4" /> AI 智能診斷
                            </div>
                            <div className={`text-6xl font-black ${data.analysis.score >= 80 ? 'text-red-400' : data.analysis.score >= 60 ? 'text-orange-400' : 'text-green-400'}`}>
                                {data.analysis.score}
                            </div>
                            <div className="text-xl font-bold mt-2 text-text">{data.analysis.verdict}</div>
                            <div className="text-xs text-muted mt-1">綜合多空評分 (0-100)</div>
                        </div>

                        {/* Report Body */}
                        <div className="flex-1 space-y-3">
                            {data.analysis.report.split('\n').map((line, idx) => {
                                if (line.startsWith('###')) return <h3 key={idx} className="text-lg font-bold text-primary mt-2">{line.replace('###', '').trim()}</h3>;
                                if (line.startsWith('####')) return <h4 key={idx} className="text-md font-bold text-secondary mt-1">{line.replace('####', '').trim()}</h4>;
                                if (line.startsWith('-')) return <li key={idx} className="text-sm text-gray-300 ml-4 list-disc">{line.replace('-', '').trim()}</li>;
                                if (line.startsWith('>')) return <p key={idx} className="text-xs text-muted italic border-l-2 border-muted pl-2">{line.replace('>', '').trim()}</p>;
                                if (line.trim() === '') return <div key={idx} className="h-1"></div>;
                                return <p key={idx} className="text-sm text-gray-300 leading-relaxed">{line.replace(/\*\*/g, '')}</p>;
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* Top Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg hover:border-accent/20 transition-all">
                    <h3 className="text-muted text-sm font-medium mb-1">籌碼透視 - 聰明錢</h3>
                    <div className="flex items-end gap-2">
                        <span className={`text-3xl font-bold ${data?.chips?.analysis === 'Accumulating' ? 'text-red-400' : data?.chips?.analysis === 'Selling' ? 'text-green-400' : 'text-text'}`}>
                            {data?.chips?.analysis === 'Accumulating' ? "主力買進" : data?.chips?.analysis === 'Selling' ? "主力調節" : "觀望中"}
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
            </div>

            {/* Revenue Chart (History) */}
            <div className="bg-surface p-6 rounded-xl border border-white/5 shadow-lg">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-secondary" />
                    近 12 個月營收趨勢
                </h3>
                <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={revenue?.history?.length > 0 ? revenue.history : (revenue ? [{ name: revenue.date, value: revenue.revenue }] : [])}>
                            <XAxis
                                dataKey="date"
                                tickFormatter={(val) => val.slice(-2)}
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
                    {(!revenue?.history || revenue.history.length === 0) && <div className="text-center text-muted text-sm mt-[-100px]">暫無歷史數據</div>}
                </div>
            </div>
        </div>
    );
}

export default StockScan;
