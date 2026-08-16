import React, { useState } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { Filter, RotateCw, Calendar, ChevronRight, X } from 'lucide-react';

export const Runs: React.FC = () => {
  const [filter, setFilter] = useState<string>('all');
  const [selectedRun, setSelectedRun] = useState<any | null>(null);

  const runs = [
    {
      id: 'run-8f92a01',
      board: 'Stripe Engineering',
      family: 'Greenhouse',
      requestType: 'scheduled',
      triggeredAt: '2026-08-16T09:30:00Z',
      duration: '1.42s',
      status: 'completed',
      rawPayloadSize: '1.2 MB',
      candidatesExtracted: 14,
      attempts: [
        { attempt: 1, duration: '1.42s', status: 'success', error: null }
      ]
    },
    {
      id: 'run-7b41c09',
      board: 'Datadog Product',
      family: 'Lever',
      requestType: 'manual',
      triggeredAt: '2026-08-16T08:45:00Z',
      duration: '2.10s',
      status: 'completed',
      rawPayloadSize: '2.4 MB',
      candidatesExtracted: 28,
      attempts: [
        { attempt: 1, duration: '2.10s', status: 'success', error: null }
      ]
    },
    {
      id: 'run-6d12e88',
      board: 'Linear Core',
      family: 'Ashby',
      requestType: 'scheduled',
      triggeredAt: '2026-08-16T07:15:00Z',
      duration: '0.88s',
      status: 'completed',
      rawPayloadSize: '0.6 MB',
      candidatesExtracted: 6,
      attempts: [
        { attempt: 1, duration: '0.88s', status: 'success', error: null }
      ]
    },
    {
      id: 'run-5e01f34',
      board: 'Vercel Infrastructure',
      family: 'Workday',
      requestType: 'scheduled',
      triggeredAt: '2026-08-16T04:20:00Z',
      duration: '5.20s',
      status: 'failed',
      rawPayloadSize: '0.0 MB',
      candidatesExtracted: 0,
      attempts: [
        { attempt: 1, duration: '2.50s', status: 'error', error: 'Timeout waiting for selector .job-list' },
        { attempt: 2, duration: '2.70s', status: 'error', error: 'Selector missing in rendered DOM' }
      ]
    }
  ];

  const filteredRuns = filter === 'all'
    ? runs
    : runs.filter(r => r.status === filter);

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
            {['all', 'completed', 'failed', 'running'].map((statusKey) => (
              <button
                key={statusKey}
                onClick={() => setFilter(statusKey)}
                className={`px-3 py-1 rounded-md text-xs font-medium capitalize transition-colors ${
                  filter === statusKey
                    ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {statusKey}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => window.location.reload()}
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
                <th className="py-3 px-3">Trigger</th>
                <th className="py-3 px-3">Triggered At</th>
                <th className="py-3 px-3">Duration</th>
                <th className="py-3 px-3">Jobs Found</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
              {filteredRuns.map((run) => (
                <tr
                  key={run.id}
                  onClick={() => setSelectedRun(run)}
                  className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 cursor-pointer transition-colors"
                >
                  <td className="py-3.5 px-3 font-mono font-medium text-teal-600 dark:text-teal-400">{run.id}</td>
                  <td className="py-3.5 px-3">
                    <span className="font-semibold text-slate-900 dark:text-white block">{run.board}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{run.family}</span>
                  </td>
                  <td className="py-3.5 px-3 uppercase text-[10px] font-mono text-slate-500">{run.requestType}</td>
                  <td className="py-3.5 px-3 text-slate-500 font-mono">
                    {new Date(run.triggeredAt).toLocaleTimeString()}
                  </td>
                  <td className="py-3.5 px-3 font-mono text-slate-600 dark:text-slate-400">{run.duration}</td>
                  <td className="py-3.5 px-3 font-mono font-semibold text-slate-900 dark:text-white">{run.candidatesExtracted}</td>
                  <td className="py-3.5 px-3">
                    <StatusBadge status={run.status} size="sm" />
                  </td>
                  <td className="py-3.5 px-3 text-right">
                    <ChevronRight className="w-4 h-4 text-slate-400 ml-auto" />
                  </td>
                </tr>
              ))}
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
                <h3 className="font-semibold text-slate-900 dark:text-white">Run Details: {selectedRun.id}</h3>
                <span className="text-xs text-slate-500 font-mono">{selectedRun.board} ({selectedRun.family})</span>
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
                  <span className="text-slate-400 block text-[10px] uppercase">Payload Size</span>
                  <span className="font-semibold text-slate-900 dark:text-white">{selectedRun.rawPayloadSize}</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
                  <span className="text-slate-400 block text-[10px] uppercase">Candidates Extracted</span>
                  <span className="font-semibold text-slate-900 dark:text-white">{selectedRun.candidatesExtracted}</span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Execution Attempts Log
                </h4>
                <div className="space-y-2">
                  {selectedRun.attempts.map((att: any) => (
                    <div
                      key={att.attempt}
                      className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 text-xs font-mono"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-slate-900 dark:text-white">Attempt #{att.attempt}</span>
                        <StatusBadge status={att.status} size="sm" />
                      </div>
                      <div className="text-slate-500 text-[11px]">Duration: {att.duration}</div>
                      {att.error && (
                        <div className="mt-2 p-2 rounded bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300 text-[11px] border border-rose-200 dark:border-rose-800/50">
                          {att.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
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
