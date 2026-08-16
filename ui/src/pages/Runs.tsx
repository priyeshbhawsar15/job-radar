import React, { useState, useEffect } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { Filter, RotateCw, Calendar, ChevronRight, X } from 'lucide-react';

export const Runs: React.FC = () => {
  const [filter, setFilter] = useState<string>('all');
  const [selectedRun, setSelectedRun] = useState<any | null>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchRuns = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/runs');
      if (res.ok) {
        const data = await res.json();
        setRuns(data);
      }
    } catch (e) {
      console.error('Failed to fetch runs', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 4000);
    return () => clearInterval(interval);
  }, []);

  const filteredRuns = filter === 'all'
    ? runs
    : runs.filter(r => r.outcome === filter || r.stage === filter);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Pipeline Runs History</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Historical execution logs and attempt diagnostics subject to 7-day retention.
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 text-xs font-mono">
          <Calendar className="w-3.5 h-3.5" />
          <span>7-Day Purger Active</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Filter Status:</span>
          <div className="flex items-center gap-1.5 ml-2">
            {['all', 'success', 'provider_failure', 'in_progress'].map((statusKey) => (
              <button
                key={statusKey}
                onClick={() => setFilter(statusKey)}
                className={`px-3 py-1 rounded-md text-xs font-medium capitalize transition-colors ${
                  filter === statusKey
                    ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {statusKey.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={fetchRuns}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          title="Refresh List"
        >
          <RotateCw className="w-4 h-4" />
        </button>
      </div>

      {/* Main Runs Table */}
      <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-3">Run ID</th>
                <th className="py-3 px-3">Board</th>
                <th className="py-3 px-3">Triggered At</th>
                <th className="py-3 px-3">Stage</th>
                <th className="py-3 px-3">Jobs Extracted</th>
                <th className="py-3 px-3">Outcome</th>
                <th className="py-3 px-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
              {filteredRuns.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400 font-mono">
                    {loading ? 'Loading pipeline runs...' : 'No runs recorded yet. Click "Manual Pipeline Trigger" to execute.'}
                  </td>
                </tr>
              ) : (
                filteredRuns.map((run) => (
                  <tr
                    key={run.run_id}
                    onClick={() => setSelectedRun(run)}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-3 font-mono font-medium text-teal-600 dark:text-teal-400">
                      {run.run_id.slice(0, 8)}...
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="font-semibold text-slate-900 dark:text-white block">{run.board_name}</span>
                      <span className="text-[10px] text-slate-400 font-mono">{run.family}</span>
                    </td>
                    <td className="py-3.5 px-3 text-slate-500 font-mono">
                      {run.created_at ? new Date(run.created_at).toLocaleTimeString() : '-'}
                    </td>
                    <td className="py-3.5 px-3 uppercase text-[10px] font-mono text-slate-500">{run.stage}</td>
                    <td className="py-3.5 px-3 font-mono font-semibold text-slate-900 dark:text-white">{run.extracted_count}</td>
                    <td className="py-3.5 px-3">
                      <StatusBadge status={run.outcome === 'success' ? 'completed' : run.outcome === 'in_progress' ? 'running' : 'failed'} size="sm" />
                    </td>
                    <td className="py-3.5 px-3 text-right">
                      <ChevronRight className="w-4 h-4 text-slate-400 ml-auto" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Run Detail Modal/Drawer */}
      {selectedRun && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="w-full max-w-xl bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white">Run Details: {selectedRun.run_id}</h3>
                <span className="text-xs text-slate-500 font-mono">{selectedRun.board_name} ({selectedRun.family})</span>
              </div>
              <button
                onClick={() => setSelectedRun(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
                  <span className="text-slate-400 block text-[10px] uppercase">Outcome</span>
                  <span className="font-semibold text-slate-900 dark:text-white">{selectedRun.outcome}</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
                  <span className="text-slate-400 block text-[10px] uppercase">Candidates Extracted</span>
                  <span className="font-semibold text-slate-900 dark:text-white">{selectedRun.extracted_count}</span>
                </div>
              </div>

              {selectedRun.error_code && (
                <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/50 text-xs font-mono text-rose-800 dark:text-rose-300">
                  <span className="font-semibold block mb-1">Error Diagnostic:</span>
                  {selectedRun.error_code}
                </div>
              )}
            </div>

            <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30 text-right">
              <button
                onClick={() => setSelectedRun(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
