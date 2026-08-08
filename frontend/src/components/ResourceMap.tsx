import React, { useState } from 'react';
import { ResourceItem } from '../types';
import { ResourceCard } from './ResourceCard';
import { Building2, Filter, Zap } from 'lucide-react';

interface ResourceMapProps {
  resources: ResourceItem[];
  onSelectResource: (resource: ResourceItem) => void;
}

export const ResourceMap: React.FC<ResourceMapProps> = ({ resources, onSelectResource }) => {
  const [filterState, setFilterState] = useState<string>('all');

  const filteredResources = resources.filter((res) => {
    if (filterState === 'all') return true;
    if (filterState === 'green') return res.stateBucket === 'empty' || res.currentOccupancy < 50;
    if (filterState === 'yellow') return res.stateBucket === 'moderate' || (res.currentOccupancy >= 50 && res.currentOccupancy <= 80);
    if (filterState === 'orange') return res.stateBucket === 'full' || res.stateBucket === 'red' || (res.currentOccupancy > 80 && res.currentOccupancy <= 95);
    if (filterState === 'red') return res.stateBucket === 'overflow' || res.stateBucket === 'purple' || res.currentOccupancy > 95;
    return true;
  });

  const emptyCount = resources.filter((r) => r.currentOccupancy < 50).length;
  const moderateCount = resources.filter((r) => r.currentOccupancy >= 50 && r.currentOccupancy <= 80).length;
  const fullCount = resources.filter((r) => r.currentOccupancy > 80 && r.currentOccupancy <= 95).length;
  const overflowCount = resources.filter((r) => r.currentOccupancy > 95).length;

  return (
    <section className="space-y-3">
      
      {/* Section Header & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1 pb-2">
        <div>
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2 tracking-tight">
            <Building2 className="w-4 h-4 text-zinc-500" />
            Live Campus Resource Grid
          </h2>
        </div>

        {/* State Bucket Filter Chips */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <button
            onClick={() => setFilterState('all')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              filterState === 'all'
                ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
            }`}
          >
            All ({resources.length})
          </button>

          <button
            onClick={() => setFilterState('green')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex items-center gap-1.5 ${
              filterState === 'green'
                ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-800'
                : 'bg-zinc-100 dark:bg-zinc-800 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Soft Green ({emptyCount})
          </button>

          <button
            onClick={() => setFilterState('yellow')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex items-center gap-1.5 ${
              filterState === 'yellow'
                ? 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-800'
                : 'bg-zinc-100 dark:bg-zinc-800 text-amber-700 dark:text-amber-400 hover:bg-amber-50'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            Soft Yellow ({moderateCount})
          </button>

          <button
            onClick={() => setFilterState('orange')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex items-center gap-1.5 ${
              filterState === 'orange'
                ? 'bg-orange-100 dark:bg-orange-950 text-orange-800 dark:text-orange-200 border border-orange-300 dark:border-orange-800'
                : 'bg-zinc-100 dark:bg-zinc-800 text-orange-700 dark:text-orange-400 hover:bg-orange-50'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
            Soft Orange ({fullCount})
          </button>

          <button
            onClick={() => setFilterState('red')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex items-center gap-1.5 ${
              filterState === 'red'
                ? 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-200 border border-rose-300 dark:border-rose-800'
                : 'bg-zinc-100 dark:bg-zinc-800 text-rose-700 dark:text-rose-400 hover:bg-rose-50'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            Muted Red ({overflowCount})
          </button>
        </div>
      </div>

      {/* Grid of Resource Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {filteredResources.map((resource) => (
          <ResourceCard
            key={resource.id}
            resource={resource}
            onSelect={onSelectResource}
          />
        ))}
      </div>

    </section>
  );
};
