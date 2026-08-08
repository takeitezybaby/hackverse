import React from 'react';
import { Wifi, Activity, Zap, Server, ShieldCheck, RefreshCw } from 'lucide-react';

export const WifiApTelemetry: React.FC = () => {
  const apNodes = [
    { id: 'AP-LIB-01', location: 'Main Library 1st Floor Cafe', connectedDevices: 142, throughputMbps: 380, status: 'Optimal', channel: 36 },
    { id: 'AP-LIB-02', location: 'Main Library 2nd Floor Study', connectedDevices: 188, throughputMbps: 180, status: 'High Load', channel: 149 },
    { id: 'AP-GYM-01', location: 'Campus Gym Power Racks', connectedDevices: 110, throughputMbps: 210, status: 'Balanced', channel: 44 },
    { id: 'AP-CAF-01', location: 'North Cafeteria Dining Hall', connectedDevices: 64, throughputMbps: 450, status: 'Optimal', channel: 157 },
    { id: 'AP-SCI-01', location: 'Science Hub Study Pods', connectedDevices: 42, throughputMbps: 580, status: 'Light Load', channel: 52 },
    { id: 'AP-STU-01', location: 'Student Center Atrium', connectedDevices: 156, throughputMbps: 290, status: 'Balanced', channel: 161 },
  ];

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-3xl p-5 md:p-6 shadow-2xl my-6 space-y-6">
      
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-2xl bg-cyan-950 border border-cyan-800 text-cyan-400">
            <Wifi className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 font-semibold block">
              IoT Grid • Layer 5 Network Ping Density
            </span>
            <h2 className="text-xl font-bold text-white tracking-tight">
              WiFi Access Point (AP) Load Balancing
            </h2>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 bg-emerald-950/60 px-3 py-1.5 rounded-xl border border-emerald-800/80">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          <span>Dynamic Power Balancing Active</span>
        </div>
      </div>

      {/* AP Nodes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {apNodes.map((node) => (
          <div key={node.id} className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-cyan-400 font-bold">{node.id}</span>
              <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold ${
                node.status === 'High Load' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                node.status === 'Light Load' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                'bg-slate-800 text-slate-300'
              }`}>
                {node.status}
              </span>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-white">{node.location}</h4>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">Channel {node.channel} • 5GHz Mesh</p>
            </div>

            <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs font-mono">
              <div>
                <span className="text-slate-500 text-[10px] block">Clients</span>
                <span className="font-bold text-slate-200">{node.connectedDevices} Active</span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">Bandwidth</span>
                <span className="font-bold text-emerald-400">{node.throughputMbps} Mbps</span>
              </div>
            </div>
          </div>
        ))}
      </div>

    </section>
  );
};
