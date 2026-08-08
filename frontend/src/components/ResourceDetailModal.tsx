import React from 'react';
import { ResourceItem } from '../types';
import { X, Wifi, Users, Volume2, TrendingUp, Sparkles, Building, BarChart2, ShieldCheck } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

interface ResourceDetailModalProps {
  resource: ResourceItem | null;
  onClose: () => void;
  onAskRagAssistant: (query: string) => void;
}

export const ResourceDetailModal: React.FC<ResourceDetailModalProps> = ({
  resource,
  onClose,
  onAskRagAssistant,
}) => {
  if (!resource) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 text-slate-200 relative">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors border border-slate-700"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-start gap-4 mb-6">
          <div className="p-3.5 rounded-2xl bg-cyan-950 border border-cyan-800 text-cyan-400">
            <Building className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-semibold">
                Digital Twin Node • {resource.category}
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">{resource.name}</h2>
            <p className="text-xs text-slate-400 mt-1">
              Current Occupancy: <span className="font-bold text-white font-mono">{resource.currentOccupancy}%</span> ({resource.capacityCurrent} / {resource.capacityMax} active capacity)
            </p>
          </div>
        </div>

        {/* Metrics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6 p-4 rounded-2xl bg-slate-950/80 border border-slate-800/80 text-xs">
          <div>
            <span className="text-slate-400 text-[11px] block">State Bucket</span>
            <span className="font-bold font-mono text-cyan-300 uppercase">{resource.stateBucket}</span>
          </div>
          <div>
            <span className="text-slate-400 text-[11px] block">Peak Forecast</span>
            <span className="font-bold font-mono text-amber-300">{resource.peakHours}</span>
          </div>
          <div>
            <span className="text-slate-400 text-[11px] block">WiFi Access Points</span>
            <span className="font-bold font-mono text-emerald-300">{resource.wifiApNodesCount} APs ({resource.averageSpeedMbps} Mbps)</span>
          </div>
          <div>
            <span className="text-slate-400 text-[11px] block">Ambient Sound</span>
            <span className="font-bold font-mono text-slate-200">{resource.noiseLevelDb} dB</span>
          </div>
        </div>

        {/* Hourly Forecast Curve (Recharts) */}
        <div className="mb-6 p-4 rounded-2xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-cyan-400" />
              24-Hour Predicted vs Historical Occupancy %
            </h3>
            <span className="text-[10px] font-mono text-slate-400">Layer 2 Forecast Model</span>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={resource.hourlyForecast} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorOccupancy" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorHist" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#64748b" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#64748b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} domain={[0, 100]} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', fontSize: '12px' }}
                  itemStyle={{ color: '#38bdf8' }}
                />
                <Area type="monotone" dataKey="occupancy" name="Predicted %" stroke="#38bdf8" fillOpacity={1} fill="url(#colorOccupancy)" strokeWidth={2} />
                <Area type="monotone" dataKey="historicalAvg" name="Historical Avg %" stroke="#64748b" fillOpacity={1} fill="url(#colorHist)" strokeWidth={1.5} strokeDasharray="4 4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Floor Breakdown */}
        <div className="mb-6">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-3">
            Zone & Floor Breakdown
          </h3>
          <div className="space-y-2">
            {resource.floors.map((floor, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between text-xs">
                <div>
                  <span className="font-semibold text-slate-200">{floor.name}</span>
                  <span className="text-[11px] text-slate-400 block mt-0.5">
                    {floor.availableSeats} available desks/stations remaining
                  </span>
                </div>
                <div className="text-right font-mono">
                  <span className={`font-bold ${floor.occupancy > 90 ? 'text-rose-400' : floor.occupancy > 70 ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {floor.occupancy}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Assistant Call-to-action */}
        <div className="p-4 rounded-2xl bg-cyan-950/30 border border-cyan-800/60 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-3 text-xs">
            <Sparkles className="w-5 h-5 text-cyan-400 shrink-0" />
            <div>
              <p className="font-semibold text-cyan-200">Ask Copilot RAG Agent</p>
              <p className="text-slate-400 text-[11px]">Get real-time recommendation for best time or seat in {resource.name}</p>
            </div>
          </div>
          <button
            onClick={() => {
              onClose();
              onAskRagAssistant(`When is the best quiet time to study in ${resource.name} today?`);
            }}
            className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-colors shrink-0"
          >
            Ask Assistant Now
          </button>
        </div>

      </div>
    </div>
  );
};
