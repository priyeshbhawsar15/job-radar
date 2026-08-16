import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { MOCK_RUNS } from '../data/mockData';

export const Runs: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunItem[]>(MOCK_RUNS);

  useEffect(() => {
    // Fetch live runs from API if available and merge
    const fetchApiRuns = async () => {
      try {
        const res = await fetch('/api/v1/runs');
        if (res.ok) {
          const apiRuns: any[] = await res.json();
          if (apiRuns && apiRuns.length > 0) {
            const mapped: RunItem[] = apiRuns.map((r) => ({
              id: r.pipeline_id || r.run_id,
              time: r.created_at ? new Date(r.created_at).toLocaleString() : 'Just now',
              state: r.outcome === 'success' ? 'completed' : r.outcome === 'in_progress' ? 'partial' : 'failed',
              duration: '1m 20s',
              boards: 1,
              completed: 1,
              extracted: r.extracted_count || 0,
              accepted: r.extracted_count || 0,
              held: 0,
              boardRuns: [
                {
                  boardId: r.board_id,
                  state: r.outcome === 'success' ? 'completed' : 'failed',
                  outcome: `${r.extracted_count || 0} extracted`,
                  boardRunId: r.run_id,
                },
              ],
              jobs: [],
            }));

            const existingIds = new Set(MOCK_RUNS.map((x) => x.id));
            const fresh = mapped.filter((x) => !existingIds.has(x.id));
            setRuns([...MOCK_RUNS, ...fresh]);
          }
        }
      } catch (e) {
        console.error('API runs fetch error:', e);
      }
    };
    fetchApiRuns();
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · static prototype
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Pipeline run history
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
            Detailed run data is retained for seven days. Select a run to inspect boards, safe logs, and Job Ops outcomes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/boards"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <span>Boards</span>
          </Link>
          <Link
            to="/jobs"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <span>Jobs</span>
          </Link>
        </div>
      </header>

      {/* Notice Banner */}
      <div className="p-3.5 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs">
        <b>Static data.</b> Manual runs, schedules, Playwright, and Job Ops are connected to local endpoints. Audit entries intentionally contain safe metadata only.
      </div>

      {/* Top 5 Metrics Summary Cards */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Retained runs</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">18</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">7-day window</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Jobs extracted</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">246</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">normalized records</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Job Ops accepted</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">181</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">receipt-backed mock status</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Held</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">14</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">safe review gate</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs col-span-2 sm:col-span-1">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Next purge</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">12</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">records in 1d 8h</span>
        </div>
      </section>

      {/* Main Pipeline Runs Card & Stack */}
      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Pipeline runs</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Newest first</p>
          </div>
          <Link
            to="/boards"
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            View boards
          </Link>
        </div>

        <div className="space-y-3">
          {runs.map((r) => (
            <Link
              key={r.id}
              to={`/runs/${r.id}`}
              className="grid grid-cols-1 sm:grid-cols-4 items-center gap-4 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all group shadow-xs"
            >
              <div>
                <b className="block text-sm font-bold text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                  {r.time}
                </b>
                <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                  {r.id} · {r.duration}
                </span>
              </div>

              <div>
                <StatusBadge status={r.state} />
              </div>

              <div className="text-xs text-slate-500 dark:text-slate-400">
                <b className="block text-base font-bold font-mono text-slate-900 dark:text-white">{r.extracted}</b>
                extracted
              </div>

              <div className="text-xs text-slate-500 dark:text-slate-400">
                <b className="block text-base font-bold font-mono text-slate-900 dark:text-white">{r.accepted}</b>
                accepted
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
};
