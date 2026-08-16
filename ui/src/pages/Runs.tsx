import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';

export const Runs: React.FC = () => {
  const [runs, setRuns] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/runs').then((res) => (res.ok ? res.json() : [])),
      fetch('/api/v1/jobs').then((res) => (res.ok ? res.json() : []))
    ])
      .then(([rData, jData]) => {
        setRuns(rData);
        setJobs(jData);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const totalRuns = runs.length;
  const totalJobs = jobs.length;
  const acceptedJobs = jobs.filter((j) => j.job_ops_status === 'accepted' || !j.job_ops_status).length;
  const heldJobs = jobs.filter((j) => j.job_ops_status === 'held').length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Pipeline Runs
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Pipeline run history
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
            Detailed run data is retained for seven days. Select a run to inspect boards, safe logs, and extracted jobs.
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
        <b>Live REST API Data.</b> Pipeline execution runs, extracted candidate counts, and status telemetry are loaded directly from the database.
      </div>

      {/* Dynamic Top 5 Metrics Summary Cards */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Retained runs</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">{totalRuns}</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">7-day window</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Jobs extracted</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">{totalJobs}</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">normalized records</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Job Ops accepted</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">{acceptedJobs}</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">receipt status</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Held</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">{heldJobs}</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">review gate</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs col-span-2 sm:col-span-1">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Retention</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">7d</b>
          <span className="block text-[11px] text-slate-400 mt-0.5">auto-purge policy</span>
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
          {loading ? (
            <div className="p-8 text-center text-slate-400 font-mono text-xs">Loading execution runs...</div>
          ) : runs.length > 0 ? (
            runs.map((r) => (
              <Link
                key={r.run_id}
                to={'/runs/' + r.run_id}
                className="grid grid-cols-1 sm:grid-cols-4 items-center gap-4 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all group shadow-xs"
              >
                <div>
                  <b className="block text-sm font-bold text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                    {r.board_name}
                  </b>
                  <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                    {r.run_id.slice(0, 8)}... · {r.created_at ? new Date(r.created_at).toLocaleTimeString() : 'Recently'}
                  </span>
                </div>

                <div>
                  <StatusBadge status={r.outcome === 'success' ? 'completed' : r.outcome} />
                </div>

                <div className="text-xs text-slate-500 dark:text-slate-400">
                  <b className="block text-base font-bold font-mono text-slate-900 dark:text-white">{r.extracted_count}</b>
                  extracted
                </div>

                <div className="text-xs text-slate-500 dark:text-slate-400">
                  <b className="block text-base font-bold font-mono text-slate-900 dark:text-white">{r.extracted_count}</b>
                  accepted
                </div>
              </Link>
            ))
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              No pipeline runs recorded yet. Click "Run Pipeline" to execute a scan tick.
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
