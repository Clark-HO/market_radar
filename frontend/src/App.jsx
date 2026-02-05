import React, { useState } from 'react';
import StockScan from './views/StockScan';
import GlobalIntel from './components/GlobalIntel';
import MacroView from './views/MacroView';
import { LayoutDashboard, Globe, Menu, Search, BarChart3, Activity } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('market');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [ticker, setTicker] = useState('2330'); // Default TSMC

  return (
    <div className="flex h-screen bg-neutral-900 text-white font-sans overflow-hidden">

      {/* 1. Sidebar (Left) */}
      <div className={`${isSidebarOpen ? 'w-64' : 'w-20'} bg-neutral-950 border-r border-white/10 transition-all duration-300 flex flex-col z-20`}>

        {/* Logo Area */}
        <div className="p-6 flex items-center justify-between">
          {isSidebarOpen ? (
            <div className="flex items-center gap-2">
              <Activity className="text-blue-500 w-6 h-6" />
              <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-teal-400 truncate">
                Market Radar
              </h1>
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <Activity className="text-blue-500 w-6 h-6" />
            </div>
          )}
        </div>

        {/* Toggle Button (Absolute or relative? relative usually better) */}
        <div className={`px-4 mb-4 ${!isSidebarOpen && 'flex justify-center'}`}>
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 hover:bg-white/5 rounded-lg text-slate-400 transition-colors">
            <Menu size={20} />
          </button>
        </div>

        {/* Navigation Actions */}
        <nav className="flex-1 px-3 space-y-2 mt-2">

          <SidebarBtn
            icon={<LayoutDashboard size={24} />}
            label="Stock Scanner"
            isActive={activeTab === 'market'}
            isOpen={isSidebarOpen}
            onClick={() => setActiveTab('market')}
            color="blue"
          />

          <SidebarBtn
            icon={<BarChart3 size={24} />}
            label="Macro View"
            isActive={activeTab === 'macro'}
            isOpen={isSidebarOpen}
            onClick={() => setActiveTab('macro')}
            color="emerald"
          />

          <SidebarBtn
            icon={<Globe size={24} />}
            label="Global Intel"
            isActive={activeTab === 'global'}
            isOpen={isSidebarOpen}
            onClick={() => setActiveTab('global')}
            color="purple"
          />

        </nav>

        {/* Footer */}
        <div className="p-4 text-[10px] text-slate-600 text-center border-t border-white/5">
          {isSidebarOpen && "v3.0 Pro Edition"}
        </div>
      </div>

      {/* 2. Main Content (Right) */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-900 relative">

        {/* Top Bar (Search & Info) - Only Visible for Stock Tab usually, but good to have a permanent header */}
        {activeTab === 'market' && (
          <div className="h-16 border-b border-white/5 bg-neutral-900/50 backdrop-blur flex items-center justify-between px-6 z-10 shrink-0">
            <div className="flex items-center gap-4 w-full max-w-xl">
              <div className="relative group w-full">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                <input
                  type="text"
                  placeholder="Search Quote (e.g., 2330, TSMC)..."
                  className="w-full bg-black/20 border border-white/10 focus:border-blue-500/50 rounded-xl pl-10 pr-4 py-2 text-sm outline-none transition-all text-slate-200 placeholder-slate-600 focus:bg-black/40"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              {/* User Profile or Status could go here */}
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 opacity-80"></div>
            </div>
          </div>
        )}

        {/* Scrollable View Area */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-6 scrollbar-thin scrollbar-thumb-white/10 hover:scrollbar-thumb-white/20">
          <div className="max-w-7xl mx-auto w-full pb-20">
            {activeTab === 'market' && <StockScan ticker={ticker} />}
            {activeTab === 'macro' && <MacroView />}
            {activeTab === 'global' && <GlobalIntel />}
          </div>
        </div>

      </div>

    </div>
  );
}

// Helper Component for consistent buttons
const SidebarBtn = ({ icon, label, isActive, isOpen, onClick, color }) => {
  // Dynamic color classes
  const colorClasses = {
    blue: 'bg-blue-600 shadow-blue-900/20 text-white',
    purple: 'bg-purple-600 shadow-purple-900/20 text-white',
    emerald: 'bg-emerald-600 shadow-emerald-900/20 text-white'
  };

  const activeStyle = isActive
    ? `${colorClasses[color]} shadow-lg`
    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200';

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center p-3 rounded-xl transition-all duration-300 group ${activeStyle}`}
      title={!isOpen ? label : ''}
    >
      <div className={`${isActive ? 'scale-110' : 'group-hover:scale-110'} transition-transform duration-300`}>
        {icon}
      </div>

      <span className={`ml-3 font-medium whitespace-nowrap transition-all duration-300 overflow-hidden ${isOpen ? 'opacity-100 max-w-full' : 'opacity-0 max-w-0'}`}>
        {label}
      </span>

      {/* Active Indicator Dot (Only when closed) */}
      {!isOpen && isActive && (
        <div className={`absolute left-16 w-1.5 h-1.5 rounded-full ${color === 'blue' ? 'bg-blue-500' : color === 'purple' ? 'bg-purple-500' : 'bg-emerald-500'}`}></div>
      )}
    </button>
  )
}

export default App;
