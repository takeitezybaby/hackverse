import React from 'react';
import { ResourceItem } from '../types';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  Legend, 
  BarChart, 
  Bar 
} from 'recharts';
import { BarChart3, TrendingUp, Layers, Zap, ShieldCheck } from 'lucide-react';

interface ResourceAnalyticsChartProps {
  resources: ResourceItem[];
}

export const ResourceAnalyticsChart: React.FC<ResourceAnalyticsChartProps> = ({ resources }) => {
  // Aggregate hourly forecast data across all resources for Recharts comparison
  const timeLabels = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'];

  const comparativeData = timeLabels.map((time) => {
    const row: Record<string, any> = { time };
    resources.forEach((res) => {
      const forecastItem = res.hourlyForecast.find((f) => f.time === time);
      row[res.name] = forecastItem ? forecastItem.occupancy : 0;
    });
    return row;
  });

  const capacityBarData = resources.map((r) => ({
    name: r.name,
    Current: r.capacityCurrent,
    Max: r.capacityMax,
    OccupancyPercent: r.currentOccupancy,
  }));

  const lineColors = ['#0284c7', '#e11d48', '#059669', '#d97706', '#9333ea'];

  return (
    <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 shadow-xs my-6 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-zinc-100 dark:border-zinc-800">
        <div>
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
              <BarChart3 className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-medium block">
                Digital Twin Analytics
              </span>
              <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
                24-Hour Campus Congestion & Capacity Forecast
              </h2>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-zinc-500">
          <span className="px-2.5 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-[11px]">
            Comparative Recharts Engine
          </span>
        </div>
      </div>

      {/* Main Comparative Line Chart */}
      <div className="p-4 rounded-lg bg-zinc-50/50 dark:bg-zinc-950/50 border border-zinc-200 dark:border-zinc-800 space-y-3">
        <h3 className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          Predicted Occupancy Trajectories Across All Campus Hotspots (%)
        </h3>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={comparativeData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" className="dark:stroke-zinc-800" />
              <XAxis dataKey="time" stroke="#71717a" fontSize={11} />
              <YAxis stroke="#71717a" fontSize={11} domain={[0, 100]} unit="%" />
              <Tooltip
                contentStyle={{ 
                  backgroundColor: '#18181b', 
                  borderColor: '#27272a', 
                  borderRadius: '8px', 
                  fontSize: '12px',
                  color: '#f4f4f5'
                }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              {resources.map((res, index) => (
                <Line
                  key={res.id}
                  type="monotone"
                  dataKey={res.name}
                  stroke={lineColors[index % lineColors.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bar Chart: Current vs Max Capacity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
        
        <div className="p-4 rounded-lg bg-zinc-50/50 dark:bg-zinc-950/50 border border-zinc-200 dark:border-zinc-800 space-y-3">
          <h3 className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            Active Occupants vs Maximum Seat Capacity
          </h3>
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={capacityBarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" className="dark:stroke-zinc-800" />
                <XAxis dataKey="name" stroke="#71717a" fontSize={10} interval={0} />
                <YAxis stroke="#71717a" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px', color: '#f4f4f5' }} />
                <Bar dataKey="Current" fill="#0284c7" radius={[4, 4, 0, 0]} name="Active Occupants" />
                <Bar dataKey="Max" fill="#a1a1aa" radius={[4, 4, 0, 0]} name="Max Seats" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Load-Balancing Metric Summary Card */}
        <div className="p-5 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700/80 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold">
                Schedule Optimizer Efficiency
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-mono">
                Active Optimization
              </span>
            </div>
            <h4 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
              92% Peak Flattening Score
            </h4>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 leading-relaxed">
              By redirecting 1,420 student schedule habits away from peak hours (18:00 Gym & Library surges), overall campus congestion spikes were reduced by <strong className="text-emerald-600 dark:text-emerald-400 font-mono">28%</strong> today.
            </p>
          </div>

          <div className="space-y-2 pt-2 border-t border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400">
            <div className="flex justify-between items-center">
              <span>Gym Queue Wait Time:</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">-25 minutes</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Library Desk Availability:</span>
              <span className="font-mono text-cyan-600 dark:text-cyan-400 font-semibold">+42% seat availability</span>
            </div>
            <div className="flex justify-between items-center">
              <span>North Cafeteria Surge Line:</span>
              <span className="font-mono text-amber-600 dark:text-amber-400 font-semibold">Reduced from 22m to 4m</span>
            </div>
          </div>
        </div>

      </div>

    </section>
  );
};
