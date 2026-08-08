import React from 'react';
import { 
  LayoutDashboard, 
  Layers, 
  MapPin, 
  Calendar, 
  Bot, 
  Wifi, 
  BarChart3, 
  Zap, 
  Sliders, 
  Database,
  HelpCircle,
  ExternalLink
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onTriggerPeakHour: () => void;
  onResetSimulation: () => void;
  onOpenApiModal: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  onTriggerPeakHour,
  onResetSimulation,
  onOpenApiModal,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Twin Overview', icon: LayoutDashboard },
    { id: 'resources', label: 'Live Resource Map', icon: MapPin, badge: '5 Hotspots' },
    { id: 'itinerary', label: 'Your Day Copilot', icon: Calendar, badge: 'Action Needed' },
    { id: 'rag_chat', label: 'watsonx RAG Assistant', icon: Bot, badge: 'AI Online' },
    { id: 'wifi_nodes', label: 'WiFi AP Telemetry', icon: Wifi },
    { id: 'analytics', label: 'Resource Forecasts', icon: BarChart3 },
  ];

  return (
    <aside className="w-full lg:w-64 bg-slate-900/95 border-r border-slate-800 flex flex-col justify-between p-4 shrink-0 font-sans">
      
      {/* Top Section */}
      <div className="space-y-6">
        
        {/* Campus Layer Switcher */}
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-2 px-2 font-semibold">
            Digital Twin Layers
          </div>
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-950 to-slate-900 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono ${
                        isActive
                          ? 'bg-cyan-900 text-cyan-200'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Live Simulation Controls */}
        <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
            <span className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              Scenario Sandbox
            </span>
            <span className="text-[10px] text-slate-500 font-mono">Layer 5</span>
          </div>

          <p className="text-[11px] text-slate-400 leading-relaxed">
            Test how the Digital Twin copilot re-balances student schedules when congestion surges.
          </p>

          <div className="space-y-1.5 pt-1">
            <button
              onClick={onTriggerPeakHour}
              className="w-full text-xs py-2 px-3 rounded-lg bg-gradient-to-r from-amber-600/30 to-rose-600/30 hover:from-amber-600/40 hover:to-rose-600/40 text-amber-200 border border-amber-500/40 transition-all font-medium flex items-center justify-center gap-2"
            >
              <Zap className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
              Simulate 18:00 Peak Rush
            </button>

            <button
              onClick={onResetSimulation}
              className="w-full text-xs py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700/80 text-slate-300 border border-slate-700 transition-all text-center"
            >
              Reset Twin State
            </button>
          </div>
        </div>

        {/* FastAPI / Backend Integration Status */}
        <div 
          onClick={onOpenApiModal}
          className="p-3 rounded-xl bg-indigo-950/30 hover:bg-indigo-950/50 border border-indigo-900/50 cursor-pointer group transition-all"
        >
          <div className="flex items-center justify-between text-xs text-indigo-300 font-semibold mb-1">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-indigo-400" />
              FastAPI Schema
            </span>
            <ExternalLink className="w-3 h-3 text-indigo-400 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <p className="text-[11px] text-slate-400 leading-tight">
            Bound to <code className="text-indigo-300 font-mono text-[10px]">/forecast</code> and <code className="text-indigo-300 font-mono text-[10px]">/report/daily/u_042</code>.
          </p>
        </div>

      </div>

      {/* Bottom Footer Info */}
      <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-500 space-y-2">
        <div className="flex items-center justify-between">
          <span>Campus IoT Grid:</span>
          <span className="text-emerald-400 font-mono">99.8% Online</span>
        </div>
        <div className="flex items-center justify-between">
          <span>watsonx Agent:</span>
          <span className="text-cyan-400 font-mono">Active</span>
        </div>
        <div className="text-[10px] text-slate-600 pt-1 text-center">
          IBM Digital Twin Architecture
        </div>
      </div>

    </aside>
  );
};
