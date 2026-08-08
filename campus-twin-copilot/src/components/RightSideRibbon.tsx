import React from 'react';
import { 
  Sparkles, 
  BarChart3, 
  Code2, 
  Radio, 
  SlidersHorizontal, 
  Zap, 
  Wifi,
  HelpCircle
} from 'lucide-react';

interface RightSideRibbonProps {
  onOpenCopilotDrawer: () => void;
  onOpenApiModal: () => void;
  isSimulating: boolean;
  onToggleSimulation: () => void;
  activeView: 'dashboard' | 'telemetry' | 'analytics';
  setActiveView: (view: 'dashboard' | 'telemetry' | 'analytics') => void;
  unreadCopilotMessagesCount?: number;
}

export const RightSideRibbon: React.FC<RightSideRibbonProps> = ({
  onOpenCopilotDrawer,
  onOpenApiModal,
  isSimulating,
  onToggleSimulation,
  activeView,
  setActiveView,
  unreadCopilotMessagesCount = 1,
}) => {
  return (
    <aside className="fixed right-0 top-14 bottom-0 w-12 bg-white dark:bg-zinc-900 border-l border-zinc-200 dark:border-zinc-800 flex flex-col items-center justify-between py-4 z-20 shadow-xs transition-colors hidden sm:flex">
      
      {/* Top Navigation Icons */}
      <div className="flex flex-col items-center space-y-4">
        
        {/* Copilot Drawer Trigger */}
        <button
          onClick={onOpenCopilotDrawer}
          className="relative group p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 transition-colors"
          title="Open Campus Copilot RAG Assistant"
        >
          <Sparkles className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          {unreadCopilotMessagesCount > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-cyan-500 animate-ping"></span>
          )}
          <span className="absolute right-14 top-1/2 -translate-y-1/2 px-2 py-1 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-[11px] font-medium rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-md">
            Copilot RAG Chat
          </span>
        </button>

        <div className="w-6 h-px bg-zinc-200 dark:border-zinc-800 my-1"></div>

        {/* Dashboard View */}
        <button
          onClick={() => setActiveView('dashboard')}
          className={`relative group p-2 rounded-lg transition-colors ${
            activeView === 'dashboard'
              ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
              : 'text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
          }`}
          title="Main Resource Dashboard"
        >
          <SlidersHorizontal className="w-4 h-4" />
          <span className="absolute right-14 top-1/2 -translate-y-1/2 px-2 py-1 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-[11px] font-medium rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-md">
            Main Grid View
          </span>
        </button>

        {/* Analytics Forecast View */}
        <button
          onClick={() => setActiveView('analytics')}
          className={`relative group p-2 rounded-lg transition-colors ${
            activeView === 'analytics'
              ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
              : 'text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
          }`}
          title="Campus Analytics & Forecast Charts"
        >
          <BarChart3 className="w-4 h-4" />
          <span className="absolute right-14 top-1/2 -translate-y-1/2 px-2 py-1 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-[11px] font-medium rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-md">
            24-hr Analytics
          </span>
        </button>

        {/* WiFi Telemetry Stream View */}
        <button
          onClick={() => setActiveView('telemetry')}
          className={`relative group p-2 rounded-lg transition-colors ${
            activeView === 'telemetry'
              ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
              : 'text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
          }`}
          title="Layer 5 WiFi AP Telemetry"
        >
          <Wifi className="w-4 h-4" />
          <span className="absolute right-14 top-1/2 -translate-y-1/2 px-2 py-1 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-[11px] font-medium rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-md">
            AP Telemetry Stream
          </span>
        </button>

      </div>

      {/* Bottom Utility Controls */}
      <div className="flex flex-col items-center space-y-3">
        
        {/* FastAPI Modal Trigger */}
        <button
          onClick={onOpenApiModal}
          className="relative group p-2 rounded-lg text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          title="FastAPI Integration Modal"
        >
          <Code2 className="w-4 h-4" />
          <span className="absolute right-14 top-1/2 -translate-y-1/2 px-2 py-1 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-[11px] font-medium rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-md">
            FastAPI Docs & Endpoints
          </span>
        </button>

        {/* Simulation Toggle */}
        <button
          onClick={onToggleSimulation}
          className={`relative group p-2 rounded-lg transition-colors ${
            isSimulating
              ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400'
              : 'text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200'
          }`}
          title={isSimulating ? "Simulation Active (Simulating Telemetry Pulse)" : "Simulation Paused"}
        >
          <Radio className={`w-4 h-4 ${isSimulating ? 'animate-pulse' : ''}`} />
          <span className="absolute right-14 top-1/2 -translate-y-1/2 px-2 py-1 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-[11px] font-medium rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-md">
            {isSimulating ? 'Pause Simulation' : 'Resume Telemetry Sim'}
          </span>
        </button>

      </div>

    </aside>
  );
};
