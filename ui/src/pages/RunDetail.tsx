import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, PlaySquare, ChevronRight } from 'lucide-react';
import { getRun, getBoard, getJob, MOCK_RUNS } from '../data/mockData';

export const RunDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<RunItem | null>(null);

  useEffect(() => {
    if (!id) return;
    const mock = getRun(id);
    if (mock) {
      setRun(mock);
    } else {
      // Fallback if requested ID isn't in mock data
      setRun(MOCK_RUNS[0]);
    }
  }, [id]);

  if (!run) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading run details...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Pipeline Run Detail
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Pipeline run detail
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 font-mono">
            {run.id} · {run.time} · {run.duration}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/runs')}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>
        </div>
      </header>

      {/* Breadcrumbs */}
      <p className="text-xs text-slate-500 dark:text-slate-400">
        <Link to="/runs" className="hover:underline">Run history</Link> / {run.id}
      </p>

      {/* Top Metrics Summary Bar */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Board outcomes</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {run.completed}/{run.boards}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5">completed</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Extracted</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {run.extracted}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5">bounded candidates</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Accepted</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {run.accepted}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5">Job Ops mock receipts</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400">Held</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {run.held}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5">no dispatch</span>
        </div>
      </section>

      {/* Board Runs Contribution Grid */}
      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Board runs</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Select a board run to inspect its safe audit timeline.
            </p>
          </div>
          <StatusBadge status={run.state} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {run.boardRuns.map((br, idx) => {
            const b = getBoard(br.boardId) || { name: br.boardId, adapter: 'unknown' };
            return (
              <Link
                key={idx}
                to={`/board-runs/${br.boardRunId}`}
                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all flex flex-col justify-between space-y-3 group"
              >
                <div>
                  <p className="text-[10px] uppercase font-mono font-bold text-teal-600 dark:text-teal-400">
                    {b.adapter}
                  </p>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white mt-0.5 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                    {b.name}
                  </h3>
                  <p className="text-xs text-slate-500 font-mono mt-1">{br.outcome}</p>
                </div>
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                  <StatusBadge status={br.state} size="sm" />
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-teal-500 transition-colors" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Extracted Jobs Stack */}
      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Extracted jobs</h2>
          <Link
            to="/jobs"
            className="inline-flex items-center gap-1 text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
          >
            <span>All jobs</span>
          </Link>
        </div>

        <div className="space-y-3">
          {run.jobs.length > 0 ? (
            run.jobs.map((jobId) => {
              const j = getJob(jobId);
              if (!j) return null;
              return (
                <Link
                  key={jobId}
                  to={`/jobs/${jobId}`}
                  className="flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all group"
                >
                  <div className="space-y-0.5">
                    <b className="block text-sm font-semibold text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                      {j.title}
                    </b>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {j.company} · {j.location}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={j.ops} size="sm" />
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-teal-500 transition-colors" />
                  </div>
                </Link>
              );
            })
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              No job records were extracted for this run.
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
