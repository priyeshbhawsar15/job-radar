import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, ShieldCheck, Clock, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { getBoardRun, getRun, getBoard } from '../data/mockData';

export const BoardRunLog: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<any | null>(null);

  useEffect(() => {
    if (!id) return;
    const res = getBoardRun(id);
    if (res) {
      setData(res);
    } else {
      // Create fallback data if unknown ID
      setData({
        entry: { boardId: 'oracle', state: 'completed', outcome: '6 extracted', boardRunId: id },
        run: { id: 'run-240820-1802', time: '20 Aug 2026 · 18:02 IST', state: 'completed', duration: '3m 41s' },
        board: { id: 'oracle', name: 'Oracle', adapter: 'oracle', rev: 'rev-19' }
      });
    }
  }, [id]);

  if (!data) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading safe audit log...</div>;
  }

  const { entry, run, board } = data;
  const isPartial = entry.state === 'partial';
  const isFailed = entry.state === 'failed';
  const isHeld = entry.state === 'held';

  return (
    <div className="space-y-6">
      {/* Page Header */}
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
            to={`/runs/${run.id}`}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <span>Pipeline run</span>
          </Link>
          <Link
            to={`/boards/${board.id}`}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <span>Board</span>
          </Link>
        </div>
      </header>

      {/* Breadcrumbs */}
      <p className="text-xs text-slate-500 dark:text-slate-400">
        <Link to={`/runs/${run.id}`} className="hover:underline">{run.id}</Link> /{' '}
        <Link to={`/boards/${board.id}`} className="hover:underline">{board.name}</Link> / {id}
      </p>

      {/* Summary grid */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 1: Board Run Summary */}
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

        {/* Card 2: Safe Audit Boundary Banner */}
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

      {/* Execution Timeline */}
      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-6">
        <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Execution timeline</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Safe structured events</p>
        </div>

        <div className="relative border-l-2 border-slate-200 dark:border-slate-800 ml-3 pl-6 space-y-8">
          {/* Event 1 */}
          <div className="relative">
            <div className="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.6)]" />
            <time className="block text-[11px] font-bold text-slate-400 font-mono mb-1">18:02:04 IST</time>
            <b className="block text-sm font-bold text-slate-900 dark:text-white">BoardRunRequest issued</b>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Capability: cap-demo-{id} · board {board.id} · {board.rev} · policy revision p-11
            </div>
            <pre className="mt-2 text-xs font-mono p-3 rounded-lg bg-slate-950 text-teal-300 border border-slate-800 leading-relaxed overflow-x-auto">
{`request_kind=BoardRunRequest
limits=time_30s pages_3 bytes_5MiB
readiness_descriptor=reviewed`}
            </pre>
          </div>

          {/* Event 2 */}
          <div className="relative">
            <div className="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.6)]" />
            <time className="block text-[11px] font-bold text-slate-400 font-mono mb-1">18:02:05 IST</time>
            <b className="block text-sm font-bold text-slate-900 dark:text-white">Playwright request admitted</b>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Safe response: accepted · diagnostic code browser_request_accepted
            </div>
          </div>

          {/* Event 3 */}
          <div className="relative">
            <div
              className={`absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full ${
                isPartial
                  ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]'
                  : isFailed
                  ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]'
                  : 'bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.6)]'
              }`}
            />
            <time className="block text-[11px] font-bold text-slate-400 font-mono mb-1">18:02:31 IST</time>
            <b className="block text-sm font-bold text-slate-900 dark:text-white">Playwright result received</b>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Outcome: {entry.outcome} · duration 26s · candidates {entry.state === 'completed' ? 9 : 0} · safe diagnostic{' '}
              {isPartial ? 'provider_failure' : 'listing_verified'}
            </div>
            <pre className="mt-2 text-xs font-mono p-3 rounded-lg bg-slate-950 text-teal-300 border border-slate-800 leading-relaxed overflow-x-auto">
{`response_kind=BoardRunResult
outcome=${entry.outcome}
duration_ms=26000
raw_payload=not_retained`}
            </pre>
          </div>

          {/* Event 4 */}
          <div className="relative">
            <div className="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.6)]" />
            <time className="block text-[11px] font-bold text-slate-400 font-mono mb-1">18:02:32 IST</time>
            <b className="block text-sm font-bold text-slate-900 dark:text-white">Run finalized</b>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Candidate policy and Job Ops eligibility decisions are handled without exposing raw browser material.
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
