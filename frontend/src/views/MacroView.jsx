import React, { useEffect, useState } from 'react';
import {
    ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';

function MacroView() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch("/macro_data.json");
                const jsonData = await response.json();
                setData(jsonData);
                setLoading(false);
            } catch (error) {
                console.error("Failed to fetch macro data", error);
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    if (loading) return <div className="p-10 text-center text-text">Loading Market Data...</div>;
    if (!data) return <div className="p-10 text-center text-red-500">Failed to load data.</div>;

    const { market_status, history, institutional, sector_flow, chips, currency } = data;

    // Helper for Colors (TW: Red=Up/Buy, Green=Down/Sell)
    const getChangeColor = (val) => val >= 0 ? "text-red-500" : "text-green-500";
    const getBgColor = (val) => val >= 0 ? "bg-red-500/10 border-red-500/30" : "bg-green-500/10 border-green-500/30";

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <header className="flex justify-between items-end mb-2">
                <div>
                    <h2 className="text-3xl font-bold text-text">Market Dashboard (大盤資金流向)</h2>
                    <p className="text-muted text-sm">Last Updated: {data.last_updated}</p>
                </div>
            </header>

            {/* 1. Daily Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                    <h3 className="text-muted text-xs uppercase font-bold">TAIEX Index</h3>
                    <div className="flex flex-col items-start gap-1 mt-1">
                        <span className="text-2xl font-bold text-text">{market_status.taiex_close.toLocaleString()}</span>
                        <span className={`text-sm font-bold ${getChangeColor(market_status.change)}`}>
                            {market_status.change} ({market_status.change_percent}%)
                        </span>
                    </div>
                </div>
                <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                    <h3 className="text-muted text-xs uppercase font-bold">Daily Volume (成交金額)</h3>
                    <p className="text-2xl font-bold text-text mt-1">
                        {Math.round(market_status.volume).toLocaleString()} <span className="text-sm text-muted">億</span>
                    </p>
                </div>
                <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                    <h3 className="text-muted text-xs uppercase font-bold">Intraday High (最高)</h3>
                    <p className="text-2xl font-bold text-red-400 mt-1">{market_status.high.toLocaleString()}</p>
                </div>
                <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                    <h3 className="text-muted text-xs uppercase font-bold">Intraday Low (最低)</h3>
                    <p className="text-2xl font-bold text-green-400 mt-1">{market_status.low.toLocaleString()}</p>
                </div>
            </div>

            {/* 2. Institutional Flow Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {institutional?.map((inst, idx) => (
                    <div key={idx} className={`p-4 rounded-xl shadow-lg border border-border ${getBgColor(inst.net)}`}>
                        <h3 className="text-text font-bold text-lg mb-1">{inst.name}</h3>
                        <div className="flex justify-between items-center">
                            <span className="text-muted text-sm">今日買賣超</span>
                            <span className={`text-2xl font-bold ${getChangeColor(inst.net)}`}>
                                {inst.net > 0 ? "+" : ""}{inst.net} <span className="text-sm">億</span>
                            </span>
                        </div>
                    </div>
                ))}
            </div>

            {/* 3. Mixed Chart (Price + Volume) */}
            <div className="bg-card p-6 rounded-xl shadow-lg border border-border">
                <h3 className="text-xl font-bold text-text mb-4">TAIEX 20-Day Trend (量價走勢)</h3>
                <div className="h-80 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={history}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                            <XAxis
                                dataKey="date"
                                tick={{ fill: '#888', fontSize: 12 }}
                                tickFormatter={(val) => val.slice(5)} // Show MM-DD
                            />
                            {/* Left Axis: Price */}
                            <YAxis
                                yAxisId="left"
                                domain={['auto', 'auto']}
                                tick={{ fill: '#eee', fontSize: 12 }}
                                orientation="left"
                            />
                            {/* Right Axis: Volume */}
                            <YAxis
                                yAxisId="right"
                                orientation="right"
                                tick={{ fill: '#888', fontSize: 12 }}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1e1e1e', border: '1px solid #444' }}
                                itemStyle={{ color: '#eee' }}
                            />
                            <Legend />
                            <Bar yAxisId="right" dataKey="volume" name="成交金額(億)" fill="#3b82f6" opacity={0.5} barSize={20} />
                            <Line yAxisId="left" type="monotone" dataKey="close" name="收盤價" stroke="#f43f5e" strokeWidth={2} dot={false} />
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* 4. Bottom Grid: Sector & Derivatives */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Futures & Currency */}
                <div className="space-y-4">
                    {/* Futures Card */}
                    <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                        <div className="flex justify-between items-center">
                            <h3 className="text-muted text-sm font-semibold">Futures Net OI (外資期貨空單)</h3>
                            <span className="px-2 py-0.5 rounded bg-gray-700 text-xs text-text">{chips.futures_status}</span>
                        </div>
                        <p className={`text-3xl font-bold mt-2 ${chips.futures_color === 'red' ? 'text-red-500' : 'text-green-500'}`}>
                            {chips.futures_net_oi.toLocaleString()} <span className="text-lg text-muted">口</span>
                        </p>
                    </div>
                    {/* Currency Card */}
                    <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                        <div className="flex justify-between items-center">
                            <h3 className="text-muted text-sm font-semibold">USD/TWD (匯率)</h3>
                            <span className="text-xs text-muted">Trend: {currency.trend}</span>
                        </div>
                        <p className="text-3xl font-bold text-text mt-2">{currency.usd_twd}</p>
                    </div>
                </div>

                {/* Sector Flow */}
                <div className="bg-card p-6 rounded-xl shadow-lg border border-border">
                    <h3 className="text-xl font-bold text-text mb-4">Sector Capital Flow (類股資金流向)</h3>
                    <div className="space-y-4">
                        {sector_flow?.map((sector, idx) => {
                            let barColor = "bg-gray-500";
                            if (sector.trend === "Hot") barColor = "bg-red-500";
                            if (sector.trend === "Cool") barColor = "bg-blue-500";
                            return (
                                <div key={idx} className="flex flex-col gap-1">
                                    <div className="flex justify-between items-end">
                                        <span className="text-sm font-medium text-gray-200">{sector.name}</span>
                                        <span className={`text-sm font-bold ${sector.trend === 'Hot' ? 'text-red-400' : 'text-gray-400'}`}>
                                            {sector.ratio}%
                                        </span>
                                    </div>
                                    <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                                        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${sector.ratio}%` }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default MacroView;
