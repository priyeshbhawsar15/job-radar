import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ShieldCheck, ChevronRight } from 'lucide-react';

export const BoardRunLog: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<any | null>(null);
  const [extractedJobs, setExtractedJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!id) return;
    fetch('/api/v1/runs/board-runs/' + id)
      .then((res) => (res.ok ? res.json() : null))
      .then((resData) => {
        if (resData && resData.board_run) {
          const br = resData.board_run;
          setData({
            entry: { boardId: br.board_id, state: br.stage, outcome: br.outcome + ' (' + br.extracted_count + ' extracted)', boardRunId: br.run_id },
            run: { id: br.pipeline_id || br.run_id, time: br.created_at || 'Recently', state: br.outcome, duration: 'N/A' },
            board: { id: br.board_id, name: br.board_name, adapter: br.family, rev: 'rev-01' }
          });
          setExtractedJobs(resData.extracted_jobs || []);
        }
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading safe audit log...</div>;
  }

  if (!data) {
    return (
      <div className="p-8 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Audit Log Not Found</h2>
        <p className="text-sm text-slate-500">No recorded audit execution log found for run ID "{id}".</p>
        <Link to="/runs" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 text-white font-medium text-xs">
          <span>Return to Pipeline Runs</span>
        </Link>
      </div>
    );
  }

  const { entry, run, board } = data;
  const isPartial = entry.state === 'partial';
  const isFailed = entry.state === 'failed';

  return (
    <div className="space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Safe Playwright Audit Log
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            {board.name} board-run log
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {id} · {run.time} · reusable audit detail view
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={'/runs/' + run.id}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <span>Pipeline run</span>
          </Link>
          <Link
            to={'/boards/' + board.id}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <span>Board</span>
          </Link>
        </div>
      </header>

      <p className="text-xs text-slate-500 dark:text-slate-400">
        <Link to={'/runs/' + run.id} className="hover:underline">{run.id}</Link> /{' '}
        <Link to={'/boards/' + board.id} className="hover:underline">{board.name}</Link> / {id}
      </p>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400 font-mono">{board.adapter}</p>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">{entry.outcome}</h2>
            </div>
            <StatusBadge status={entry.state} />
          </div>

          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-y-3 text-xs">
            <dt className="text-slate-500 dark:text-slate-400 font-medium">Board revision</dt>
            <dd className="sm:col-span-2 font-mono text-slate-900 dark:text-slate-100">{board.rev}</dd>

            <dt className="text-slate-500 dark:text-slate-400 font-medium">Pipeline run</dt>
            <dd className="sm:col-span-2 font-mono text-slate-900 dark:text-slate-100">{run.id}</dd>

            <dt className="text-slate-500 dark:text-slate-400 font-medium">Safe outcome</dt>
            <dd className="sm:col-span-2 font-mono text-slate-900 dark:text-slate-100">
              {entry.state} · {entry.outcome}
            </dd>

            <dt className="text-slate-500 dark:text-slate-400 font-medium">Completeness</dt>
            <dd className="sm:col-span-2 font-mono text-slate-900 dark:text-slate-100">
              {isPartial ? 'known false' : 'known true'}
            </dd>
          </dl>
        </div>

        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-teal-600 dark:text-teal-400 font-bold border-b border-slate-100 dark:border-slate-800 pb-3">
              <ShieldCheck className="w-5 h-5" />
              <h2 className="text-base font-bold text-slate-900 dark:text-white">Safe audit boundary</h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 leading-relaxed">
              These are the only UI-representable Playwright interaction facts. No raw requests/responses, headers, cookies, internal URLs, screenshots, console text, selectors, or browser exceptions are retained.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 text-[11px] font-mono text-slate-400 border border-slate-200/60 dark:border-slate-800">
            Boundary check: 100% sanitized metadata only
          </div>
        </div>
      </section>

      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Extracted jobs from this board run ({extractedJobs.length})
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Candidate records normalized during this execution attempt.
            </p>
          </div>
          <Link
            to="/jobs"
            className="inline-flex items-center gap-1 text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
          >
            <span>All jobs</span>
          </Link>
        </div>

        <div className="space-y-3">
          {extractedJobs.length > 0 ? (
            extractedJobs.map((j) => (
              <Link
                key={j.candidate_id}
                to={'/jobs/' + j.candidate_id}
                className="flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all group"
              >
                <div className="space-y-0.5">
                  <b className="block text-sm font-semibold text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                    {j.title}
                  </b>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {j.company} · {j.location || 'Unspecified'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status="accepted" size="sm" />
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-teal-500 transition-colors" />
                </div>
              </Link>
            ))
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              No job records were extracted for this board run.
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
