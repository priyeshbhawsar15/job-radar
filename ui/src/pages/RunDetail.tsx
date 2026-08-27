import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, ChevronRight } from 'lucide-react';

export const RunDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<any | null>(null);
  const [runJobs, setRunJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!id) return;
    fetch('/api/v1/runs/board-runs/' + id)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setRun(data.board_run);
          setRunJobs(data.extracted_jobs || []);
        }
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading run details...</div>;
  }

  if (!run) {
    return (
      <div className="p-8 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Pipeline Run Not Found</h2>
        <p className="text-sm text-slate-500">The requested run ID "{id}" could not be found.</p>
        <Link to="/runs" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 text-white font-medium text-xs">
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Pipeline Runs</span>
        </Link>
      </div>
    );
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
            {run.board_name} Run Detail
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 font-mono">
            {run.run_id} · {run.created_at || 'Recently'} · stage: {run.stage}
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
        <Link to="/runs" className="hover:underline">Run history</Link> / {run.run_id}
      </p>

      {/* Top Metrics Summary Bar */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400 font-medium">New Discovered</span>
          <b className="block text-2xl font-bold font-mono text-teal-600 dark:text-teal-400 mt-1">
            {run.new_discovered_count ?? 0}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5">first-seen jobs</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400 font-medium">Re-observed</span>
          <b className="block text-2xl font-bold font-mono text-slate-600 dark:text-slate-300 mt-1">
            {run.re_observed_count ?? 0}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5">duplicate jobs</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400 font-medium">Board Target</span>
          <b className="block text-lg font-bold text-slate-900 dark:text-white mt-1">
            {run.board_name}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5 uppercase font-mono">{run.family}</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400 font-medium">Extracted Jobs</span>
          <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {run.extracted_count}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5">bounded candidates</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400 font-medium">Stage</span>
          <b className="block text-lg font-bold capitalize text-slate-900 dark:text-white mt-1">
            {run.stage}
          </b>
          <span className="block text-[11px] text-slate-400 mt-0.5">execution state</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="block text-xs text-slate-500 dark:text-slate-400 font-medium">Outcome</span>
          <div className="mt-1">
            <StatusBadge status={run.outcome === 'success' ? 'completed' : run.outcome} />
          </div>
          <span className="block text-[11px] text-slate-400 mt-0.5 font-mono">{run.error_code || 'no error'}</span>
        </div>
      </section>

      {/* Extracted Jobs Stack for this Run */}
      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Extracted jobs from this run ({runJobs.length})</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Jobs parsed and normalized during this board run execution.</p>
          </div>
          <Link
            to="/jobs"
            className="inline-flex items-center gap-1 text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
          >
            <span>All jobs</span>
          </Link>
        </div>

        <div className="space-y-3">
          {runJobs.length > 0 ? (
            runJobs.map((j) => (
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
                  {j.india_eligible === false ? (
                    <StatusBadge
                      status="rejected"
                      label="Rejected · Non-India"
                      size="sm"
                      title={j.india_exclusion_reason ? `Rejected: ${j.india_exclusion_reason}` : 'Rejected · Non-India'}
                    />
                  ) : (
                    <StatusBadge status="healthy" label="Accepted" size="sm" />
                  )}
                  {j.observation_outcome === 'discovered' && (
                    <span className="px-2 py-1 rounded-md text-[11px] font-semibold bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300">
                      Discovered
                    </span>
                  )}
                  {j.observation_outcome === 're_observed' && (
                    <span className="px-2 py-1 rounded-md text-[11px] font-semibold bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                      Re-observed
                    </span>
                  )}
                  {j.detail_enrichment_status === 'failed' && (
                    <StatusBadge
                      status="failed"
                      label={`Enrichment failed: ${j.detail_enrichment_error_code || 'unknown'}`}
                      size="sm"
                    />
                  )}
                  <StatusBadge status={j.job_ops_status || 'accepted'} size="sm" />
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-teal-500 transition-colors" />
                </div>
              </Link>
            ))
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
