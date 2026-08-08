import React, { useState } from 'react';
import { DayScheduleEntry } from '../types';
import { 
  Calendar, 
  Sparkles, 
  Check, 
  X, 
  Edit3, 
  CheckCircle2, 
  Zap,
  Clock,
  ArrowRight
} from 'lucide-react';

interface YourDayCardProps {
  entries: DayScheduleEntry[];
  onAcceptRecommendation: (id: string) => void;
  onModifySchedule: (id: string, newTime: string, newLocation: string) => void;
  loadBalanceScore: number;
}

export const YourDayCard: React.FC<YourDayCardProps> = ({
  entries,
  onAcceptRecommendation,
  onModifySchedule,
  loadBalanceScore,
}) => {
  const [modifyingId, setModifyingId] = useState<string | null>(null);
  const [customTime, setCustomTime] = useState<string>('');
  const [customLocation, setCustomLocation] = useState<string>('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const handleAccept = (id: string) => {
    onAcceptRecommendation(id);
    setToastMessage('Schedule updated. Calendar synchronized.');
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleSaveModify = (id: string) => {
    if (customTime && customLocation) {
      onModifySchedule(id, customTime, customLocation);
      setModifyingId(null);
      setToastMessage('Custom schedule time saved.');
      setTimeout(() => setToastMessage(null), 3000);
    }
  };

  return (
    <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 shadow-xs my-4 space-y-4">
      
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-100 dark:border-zinc-800">
        <div className="flex items-center space-x-2">
          <Calendar className="w-4 h-4 text-zinc-500" />
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
            Your Day — Load-Balanced Itinerary
          </h2>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono text-zinc-500 dark:text-zinc-400">
          <span>63 mins queue time saved</span>
          <span>•</span>
          <span>Load Balance: <strong className="text-zinc-900 dark:text-zinc-100">{loadBalanceScore}%</strong></span>
        </div>
      </div>

      {toastMessage && (
        <div className="p-2.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 text-xs flex items-center justify-between font-mono">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            {toastMessage}
          </span>
          <button onClick={() => setToastMessage(null)} className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Schedule Items List */}
      <div className="space-y-3">
        {entries.map((entry) => {
          const isAccepted = entry.status === 'accepted';
          const isModified = entry.status === 'modified';

          return (
            <div
              key={entry.id}
              className={`p-4 rounded-lg border transition-colors ${
                isAccepted
                  ? 'bg-zinc-50/80 dark:bg-zinc-900/60 border-zinc-300 dark:border-zinc-700'
                  : 'bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700'
              }`}
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                
                <div className="flex-1 space-y-2.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-medium">
                      {entry.category}
                    </span>
                    {isAccepted && (
                      <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        Accepted
                      </span>
                    )}
                    {isModified && (
                      <span className="text-[11px] font-mono text-zinc-500 flex items-center gap-1">
                        Custom Modified
                      </span>
                    )}
                  </div>

                  {/* Usual Habit (Crossed Out if Congested) */}
                  <div className="text-xs text-zinc-500 dark:text-zinc-400 font-sans flex flex-wrap items-center gap-2">
                    <span className="font-medium text-zinc-400">Usual:</span>
                    <span className={entry.habit.isCongested ? 'line-through text-zinc-400 opacity-75' : 'text-zinc-700 dark:text-zinc-300'}>
                      {entry.habit.activity} at {entry.habit.time} ({entry.habit.location})
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900">
                      {entry.habit.statusText}
                    </span>
                  </div>

                  {/* System Recommended Load-Balanced Alternative */}
                  <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/80 dark:border-zinc-700/80 text-xs space-y-1">
                    <div className="flex items-center space-x-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                        Recommended: {entry.recommendation.activity} at {entry.recommendation.time}
                      </span>
                      <span className="text-zinc-500">({entry.recommendation.location})</span>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-zinc-500 dark:text-zinc-400 pt-0.5">
                      <p>{entry.recommendation.reasoning}</p>
                      <span className="font-mono text-emerald-600 dark:text-emerald-400 font-medium">
                        {entry.recommendation.statusText}
                      </span>
                    </div>
                  </div>

                </div>

                {/* Ghost / Outline Accept and Modify Buttons */}
                <div className="flex lg:flex-col items-center justify-end gap-2 shrink-0">
                  {!isAccepted && (
                    <button
                      onClick={() => handleAccept(entry.id)}
                      className="px-3 py-1.5 rounded-md border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-900 hover:text-white dark:hover:bg-zinc-100 dark:hover:text-zinc-900 text-zinc-800 dark:text-zinc-200 text-xs font-medium transition-colors flex items-center gap-1.5"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Accept
                    </button>
                  )}

                  <button
                    onClick={() => {
                      setModifyingId(modifyingId === entry.id ? null : entry.id);
                      setCustomTime(entry.recommendation.time);
                      setCustomLocation(entry.recommendation.location);
                    }}
                    className="px-3 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-xs font-medium transition-colors flex items-center gap-1.5"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Modify
                  </button>
                </div>

              </div>

              {/* Modify Inline Form */}
              {modifyingId === entry.id && (
                <div className="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div>
                    <label className="text-zinc-500 text-[10px] block mb-1">Time</label>
                    <input
                      type="text"
                      value={customTime}
                      onChange={(e) => setCustomTime(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 font-mono text-xs focus:outline-none focus:border-zinc-400"
                    />
                  </div>
                  <div>
                    <label className="text-zinc-500 text-[10px] block mb-1">Location</label>
                    <input
                      type="text"
                      value={customLocation}
                      onChange={(e) => setCustomLocation(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 text-xs focus:outline-none focus:border-zinc-400"
                    />
                  </div>
                  <div className="sm:col-span-2 flex justify-end space-x-2 pt-1">
                    <button
                      onClick={() => setModifyingId(null)}
                      className="px-2.5 py-1 rounded text-zinc-500 hover:text-zinc-800"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleSaveModify(entry.id)}
                      className="px-3 py-1 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-medium text-xs"
                    >
                      Save
                    </button>
                  </div>
                </div>
              )}

            </div>
          );
        })}
      </div>

    </section>
  );
};
