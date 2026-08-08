import React, { useState } from 'react';
import { UserProfile } from '../types';
import { 
  Radio, 
  ChevronDown, 
  Sparkles, 
  Code2, 
  RefreshCw, 
  ShieldCheck, 
  SlidersHorizontal,
  Bell,
  CheckCircle2
} from 'lucide-react';

interface HeaderProps {
  user: UserProfile;
  liveClock: string;
  isSimulating: boolean;
  setIsSimulating: React.Dispatch<React.SetStateAction<boolean>>;
  onOpenApiModal: () => void;
  onOpenCopilotDrawer: () => void;
  loadBalanceScore: number;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  liveClock,
  isSimulating,
  setIsSimulating,
  onOpenApiModal,
  onOpenCopilotDrawer,
  loadBalanceScore,
}) => {
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  return (
    <header className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 sticky top-0 z-30 px-6 py-3.5 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        
        {/* Left: Brand / Title */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center text-white dark:text-zinc-900 font-semibold text-sm shadow-xs">
            <Radio className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
                Campus Twin Copilot
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
                v2.4 Live
              </span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-zinc-500 dark:text-zinc-400">
              <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium text-[11px]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                Twin Synced
              </span>
              <span>•</span>
              <span className="font-mono text-[11px]">{liveClock}</span>
            </div>
          </div>
        </div>

        {/* Right: Actions & Profile */}
        <div className="flex items-center space-x-3">
          
          {/* Load Balance Score Pill */}
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700/80 text-xs">
            <span className="text-zinc-500 dark:text-zinc-400">Load Balance:</span>
            <span className="font-mono font-semibold text-zinc-900 dark:text-zinc-100">{loadBalanceScore}%</span>
          </div>

          {/* FastAPI Endpoint Button */}
          <button
            onClick={onOpenApiModal}
            className="hidden md:flex items-center space-x-1.5 text-xs px-2.5 py-1.5 rounded-md text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors border border-transparent hover:border-zinc-200 dark:hover:border-zinc-700 font-mono"
            title="Inspect FastAPI backend schema"
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>FastAPI Schema</span>
          </button>

          {/* Copilot Assistant Trigger Button */}
          <button
            onClick={onOpenCopilotDrawer}
            className="flex items-center space-x-1.5 text-xs px-3 py-1.5 rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-medium hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-all shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ask Copilot</span>
          </button>

          {/* User Profile Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowUserDropdown(!showUserDropdown)}
              className="flex items-center space-x-2 p-1 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors border border-transparent hover:border-zinc-200 dark:hover:border-zinc-700"
            >
              <img
                src={user.avatar}
                alt={user.name}
                className="w-7 h-7 rounded-md object-cover ring-1 ring-zinc-300 dark:ring-zinc-700"
              />
              <div className="text-left hidden sm:block">
                <div className="text-xs font-medium text-zinc-900 dark:text-zinc-100 leading-tight">
                  {user.name}
                </div>
                <div className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 leading-tight">
                  Student u_042
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
            </button>

            {showUserDropdown && (
              <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg p-3 z-50 text-xs text-zinc-700 dark:text-zinc-300">
                <div className="flex items-center space-x-3 pb-3 border-b border-zinc-100 dark:border-zinc-800 mb-2">
                  <img
                    src={user.avatar}
                    alt={user.name}
                    className="w-9 h-9 rounded-lg object-cover ring-1 ring-zinc-200 dark:ring-zinc-700"
                  />
                  <div>
                    <div className="font-semibold text-zinc-900 dark:text-zinc-100">{user.name}</div>
                    <div className="text-zinc-500 font-mono text-[11px]">{user.role}</div>
                  </div>
                </div>

                <div className="space-y-1 py-1">
                  <div className="flex justify-between items-center text-[11px] py-1 px-1">
                    <span className="text-zinc-500">Weekly Time Saved:</span>
                    <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">{user.hoursSavedThisWeek} hrs</span>
                  </div>
                  <button 
                    onClick={() => setShowUserDropdown(false)}
                    className="w-full text-left px-2 py-1.5 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center gap-2 text-zinc-700 dark:text-zinc-300"
                  >
                    <ShieldCheck className="w-3.5 h-3.5 text-zinc-400" />
                    Student Credentials & Sync
                  </button>
                  <button 
                    onClick={() => setShowUserDropdown(false)}
                    className="w-full text-left px-2 py-1.5 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center gap-2 text-zinc-700 dark:text-zinc-300"
                  >
                    <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-400" />
                    Load Balancing Rules
                  </button>
                </div>
              </div>
            )}
          </div>

        </div>

      </div>
    </header>
  );
};
