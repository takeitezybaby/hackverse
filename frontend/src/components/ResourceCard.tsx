import React from 'react';
import { ResourceItem, CongestionState } from '../types';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Wifi, 
  Volume2, 
  Clock, 
  ArrowUpRight
} from 'lucide-react';

interface ResourceCardProps {
  resource: ResourceItem;
  onSelect: (resource: ResourceItem) => void;
}

export const ResourceCard: React.FC<ResourceCardProps> = ({ resource, onSelect }) => {
  // Pastel Indicators matching exact requirement:
  // Green (Empty <50%), Yellow (Moderate 50-80%), Orange (Full 80-95%), Red (Overflow >95%)
  const getStateConfig = (state: CongestionState, occupancy: number) => {
    if (occupancy < 50 || state === 'empty' || state === 'green') {
      return {
        label: 'Empty (<50%)',
        badgeBg: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800',
        dotBg: 'bg-emerald-500',
        progressBar: 'bg-emerald-500/80',
        accentText: 'text-emerald-600 dark:text-emerald-400',
      };
    } else if (occupancy <= 80 || state === 'moderate' || state === 'yellow') {
      return {
        label: 'Moderate (50-80%)',
        badgeBg: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800',
        dotBg: 'bg-amber-500',
        progressBar: 'bg-amber-500/80',
        accentText: 'text-amber-600 dark:text-amber-400',
      };
    } else if (occupancy <= 95 || state === 'full' || state === 'red' || state === 'orange') {
      return {
        label: 'Full (80-95%)',
        badgeBg: 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950/50 dark:text-orange-300 dark:border-orange-800',
        dotBg: 'bg-orange-500',
        progressBar: 'bg-orange-500/80',
        accentText: 'text-orange-600 dark:text-orange-400',
      };
    } else {
      return {
        label: 'Overflow (>95%)',
        badgeBg: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800',
        dotBg: 'bg-rose-500',
        progressBar: 'bg-rose-500/80',
        accentText: 'text-rose-600 dark:text-rose-400',
      };
    }
  };

  const stateConfig = getStateConfig(resource.stateBucket, resource.currentOccupancy);

  const getTrendIcon = (trend: ResourceItem['trend']) => {
    if (trend === 'up') return <TrendingUp className="w-3.5 h-3.5 text-zinc-500" />;
    if (trend === 'down') return <TrendingDown className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />;
    return <Minus className="w-3.5 h-3.5 text-zinc-400" />;
  };

  return (
    <div
      onClick={() => onSelect(resource)}
      className="group bg-white dark:bg-zinc-900/90 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 transition-all duration-200 hover:border-zinc-400 dark:hover:border-zinc-600 cursor-pointer shadow-xs flex flex-col justify-between"
    >
      <div>
        {/* Header Row */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 dark:text-zinc-500 font-medium">
              {resource.category.replace('_', ' ')}
            </span>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors flex items-center gap-1.5">
              {resource.name}
            </h3>
          </div>

          <button 
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
            title="View detail breakdown"
          >
            <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        </div>

        {/* Occupancy Big Metric */}
        <div className="flex items-baseline justify-between mb-3">
          <div className="flex items-baseline space-x-1.5">
            <span className={`text-2xl font-bold font-mono tracking-tight ${stateConfig.accentText}`}>
              {resource.currentOccupancy}%
            </span>
            <span className="text-[11px] text-zinc-500 dark:text-zinc-400 font-mono">
              ({resource.capacityCurrent}/{resource.capacityMax})
            </span>
          </div>

          <div className="flex items-center space-x-1 text-[11px] text-zinc-500 dark:text-zinc-400 font-mono">
            {getTrendIcon(resource.trend)}
            <span>{resource.trendValue}</span>
          </div>
        </div>

        {/* Pastel State Badge & Clean Progress Bar */}
        <div className="space-y-1.5 mb-3">
          <div className="flex justify-between items-center text-[11px]">
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-medium ${stateConfig.badgeBg}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${stateConfig.dotBg}`}></span>
              {stateConfig.label}
            </span>
            <span className="text-[10px] font-mono text-zinc-400">
              Peak: {resource.peakHours}
            </span>
          </div>

          <div className="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${stateConfig.progressBar}`}
              style={{ width: `${Math.min(resource.currentOccupancy, 100)}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Card Footer Telemetry */}
      <div className="pt-2.5 border-t border-zinc-100 dark:border-zinc-800/80 grid grid-cols-3 gap-1 text-[11px] text-zinc-500 dark:text-zinc-400 font-mono">
        <div className="flex items-center space-x-1" title="WiFi AP Count">
          <Wifi className="w-3 h-3 text-zinc-400" />
          <span>{resource.wifiApNodesCount} APs</span>
        </div>
        <div className="flex items-center space-x-1" title="Throughput Speed">
          <span>{resource.averageSpeedMbps} Mbps</span>
        </div>
        <div className="flex items-center space-x-1 justify-end" title="Ambient Sound">
          <Volume2 className="w-3 h-3 text-zinc-400" />
          <span>{resource.noiseLevelDb} dB</span>
        </div>
      </div>
    </div>
  );
};
