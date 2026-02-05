import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

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

    const { market_status, chips, currency, sector_flow } = data;

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <header className="mb-6">
                <h2 className="text-3xl font-bold text-text">Market Dashboard (大盤資金流向)</h2>
                <p className="text-muted text-sm">Last Updated: {data.last_updated}</p>
            </header>

            {/* Top Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* TAIEX Card */}
                <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                    <h3 className="text-muted text-sm font-semibold mb-1">TAIEX (加權指數)</h3>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-bold text-text">{market_status?.taiex_close?.toLocaleString()}</span>
                        <span className={`text-lg font-bold ${market_status?.change >= 0 ? "text-red-500" : "text-green-500"}`}>
                            {market_status?.change > 0 ? "+" : ""}{market_status?.change} ({market_status?.change_percent}%)
                        </span>
                    </div>
                </div>

                {/* Futures Card */}
                <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                    <h3 className="text-muted text-sm font-semibold mb-1">Futures Net OI (外資期貨空單)</h3>
                    <div className="flex flex-col">
                        <span className={`text-3xl font-bold ${chips?.futures_color === 'red' ? 'text-red-500' : 'text-green-500'}`}>
                            {chips?.futures_net_oi?.toLocaleString()} 口
                        </span>
                        <span className="text-sm font-medium text-text mt-1 px-2 py-0.5 bg-gray-700/50 rounded w-fit">
                            Status: {chips?.futures_status}
                        </span>
                    </div>
                </div>

                {/* Currency Card */}
                <div className="bg-card p-4 rounded-xl shadow-lg border border-border">
                    <h3 className="text-muted text-sm font-semibold mb-1">USD/TWD (台幣匯率)</h3>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-bold text-text">{currency?.usd_twd}</span>
                        <span className="text-sm font-medium text-muted mb-1">({currency?.trend})</span>
                    </div>
                </div>
            </div>

            {/* Main Chart Area */}
            <div className="bg-card p-6 rounded-xl shadow-lg border border-border">
                <h3 className="text-xl font-bold text-text mb-4">Sector Capital Flow (類股資金流向)</h3>
                <div className="h-[500px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={sector_flow} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                            <XAxis type="number" hide />
                            <YAxis dataKey="name" type="category" width={130} tick={{ fill: '#e5e7eb', fontSize: 12 }} />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                                itemStyle={{ color: '#f3f4f6' }}
                                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                            />
                            <Bar dataKey="ratio" radius={[0, 4, 4, 0]} barSize={32}>
                                {sector_flow?.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.trend === 'Hot' ? '#ef4444' : entry.trend === 'Cool' ? '#3b82f6' : '#6b7280'} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}

export default MacroView;
