import React, { useState, useEffect } from 'react';
import { TickerAlert } from '../types';
import { Sparkles, TrendingUp, AlertTriangle, Info, ChevronRight, Play, Pause } from 'lucide-react';

interface PredictionTickerProps {
  alerts: TickerAlert[];
}

export const PredictionTicker: React.FC<PredictionTickerProps> = ({ alerts }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    if (isPaused || alerts.length === 0) return;

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % alerts.length);
    }, 4500);

    return () => clearInterval(interval);
  }, [isPaused, alerts.length]);

  const currentAlert = alerts[currentIndex] || alerts[0];

  if (!currentAlert) return null;

  return (
    <div className="w-full bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-2.5 my-3 text-xs transition-all">
      <div className="flex items-center justify-between gap-3">
        
        {/* Left Badge */}
        <div className="flex items-center space-x-2 shrink-0">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-mono text-[10px] font-semibold uppercase tracking-wider">
            <Sparkles className="w-3 h-3 text-cyan-500 animate-spin" style={{ animationDuration: '8s' }} />
            Forecast Ticker
          </span>
        </div>

        {/* Center Alert Message */}
        <div className="flex-1 flex items-center space-x-2 min-w-0 font-sans">
          <span className="font-mono text-zinc-400 text-[11px] shrink-0">
            [{currentAlert.timestamp}]
          </span>
          <span className="font-semibold text-zinc-800 dark:text-zinc-200 shrink-0">
            {currentAlert.resourceName}:
          </span>
          <p className="text-zinc-600 dark:text-zinc-300 truncate text-xs">
            {currentAlert.message}
          </p>
        </div>

        {/* Right Stepper */}
        <div className="flex items-center space-x-1.5 shrink-0 text-zinc-400 font-mono text-[11px]">
          <span>{currentIndex + 1}/{alerts.length}</span>
          <button
            onClick={() => setIsPaused(!isPaused)}
            className="p-1 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 transition-colors"
            title={isPaused ? "Play ticker" : "Pause ticker"}
          >
            {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
          </button>
          <button
            onClick={() => setCurrentIndex((prev) => (prev + 1) % alerts.length)}
            className="p-1 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 transition-colors"
            title="Next forecast"
          >
            <ChevronRight className="w-3 h-3" />
          </button>
        </div>

      </div>
    </div>
  );
};
