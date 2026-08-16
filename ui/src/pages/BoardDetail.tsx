import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, Edit3, AlertTriangle, CheckCircle, ExternalLink, ChevronRight } from 'lucide-react';
import { getBoard, MOCK_RUNS } from '../data/mockData';
import type { BoardItem } from '../data/mockData';

export const BoardDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [board, setBoard] = useState<BoardItem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!id) return;
    const mock = getBoard(id);
    if (mock) {
      setBoard(mock);
      setLoading(false);
    } else {
      fetch('/api/v1/boards')
        .then((res) => (res.ok ? res.json() : []))
        .then((data: any[]) => {
          const found = data.find((b: any) => b.board_id === id || b.name.toLowerCase() === id.toLowerCase());
          if (found) {
            setBoard({
              id: found.board_id,
              name: found.name,
              adapter: found.family,
              url: found.target_url || 'https://example.com/careers',
              state: found.status === 'active' ? 'reviewed' : found.status,
              rev: 'rev-01',
              runs: 10,
              success: found.consecutive_parser_failures > 0 ? 50 : 100,
              missing: found.consecutive_parser_failures >= 3 ? ['listing readiness descriptor', 'reviewed detail route allowlist'] : [],
              next: found.schedule_cron || '06:00 IST',
            });
          }
        })
        .catch((e) => console.error(e))
        .finally(() => setLoading(false));
    }
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading board details...</div>;
  }

  if (!board) {
    return (
      <div className="p-8 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Board Configuration Not Found</h2>
        <p className="text-sm text-slate-500">The requested board ID "{id}" could not be found.</p>
        <Link to="/boards" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 text-white font-medium text-xs">
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Boards Registry</span>
        </Link>
      </div>
    );
  }

  // Find recent board runs for this board across all retained runs
  const recentRuns: { runTime: string; outcome: string; boardRunId: string; parentRunId: string }[] = [];
  MOCK_RUNS.forEach((r) => {
    r.boardRuns.forEach((br) => {
      if (br.boardId.toLowerCase() === board.id.toLowerCase()) {
        recentRuns.push({
          runTime: r.time,
          outcome: `${br.outcome} (${br.state})`,
          boardRunId: br.boardRunId,
          parentRunId: r.id,
        });
      }
    });
  });

  return (
    <div className="space-y-6">
      {/* Top Action Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Board Configuration
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            {board.name}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {board.adapter} adapter · {board.rev} · public listing configuration
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={`/boards/${board.id}/config`}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit configuration</span>
          </Link>
          <button
            onClick={() => navigate('/boards')}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>
        </div>
      </header>

      {/* Breadcrumb path */}
      <p className="text-xs text-slate-500 dark:text-slate-400">
        <Link to="/boards" className="hover:underline">Boards</Link> / {board.name}
      </p>

      {/* 2-Column Section */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Board Configuration KV Card */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Board configuration</h2>
            <StatusBadge status={board.state} />
          </div>

          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-y-3 gap-x-4 text-xs">
            <dt className="text-slate-500 dark:text-slate-400 font-medium">Public listing link</dt>
            <dd className="sm:col-span-2 font-mono break-all">
              <a
                href={board.url}
                target="_blank"
                rel="noreferrer"
                className="text-teal-600 dark:text-teal-400 hover:underline inline-flex items-center gap-1"
              >
                <span>{board.url}</span>
                <ExternalLink className="w-3.5 h-3.5 shrink-0" />
              </a>
            </dd>

            <dt className="text-slate-500 dark:text-slate-400 font-medium">Adapter family</dt>
            <dd className="sm:col-span-2 font-mono text-slate-900 dark:text-slate-100">{board.adapter}</dd>

            <dt className="text-slate-500 dark:text-slate-400 font-medium">Current revision</dt>
            <dd className="sm:col-span-2 font-mono text-slate-900 dark:text-slate-100">{board.rev}</dd>

            <dt className="text-slate-500 dark:text-slate-400 font-medium">Next admission</dt>
            <dd className="sm:col-span-2 font-mono text-slate-900 dark:text-slate-100">{board.next}</dd>
          </dl>

          {/* Missing mandatory fields box */}
          {board.missing.length > 0 ? (
            <div className="mt-4 p-4 rounded-lg bg-amber-500/10 border-l-4 border-amber-500 text-amber-900 dark:text-amber-300 text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-amber-800 dark:text-amber-200">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <span>Mandatory configuration incomplete</span>
              </div>
              <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-amber-800 dark:text-amber-300">
                {board.missing.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="mt-4 p-3.5 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" />
              <div>
                <b>All representative mandatory configuration fields are present.</b> This does not enable a live source.
              </div>
            </div>
          )}
        </div>

        {/* Run Stats Summary Card */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3">
            Run stats
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="block text-xs text-slate-500 dark:text-slate-400">Retained runs</span>
              <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">{board.runs}</b>
              <span className="block text-[11px] text-slate-400 mt-0.5">7 days</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="block text-xs text-slate-500 dark:text-slate-400">Completion</span>
              <b className="block text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">{board.success}%</b>
              <span className="block text-[11px] text-slate-400 mt-0.5">safe outcomes</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="block text-xs text-slate-500 dark:text-slate-400">Adapter</span>
              <b className="block text-xl font-bold font-mono text-slate-900 dark:text-white mt-1 uppercase">{board.adapter}</b>
              <span className="block text-[11px] text-slate-400 mt-0.5">reviewed family</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="block text-xs text-slate-500 dark:text-slate-400">State</span>
              <b className="block text-xl font-bold font-mono text-slate-900 dark:text-white mt-1 capitalize">{board.state}</b>
              <span className="block text-[11px] text-slate-400 mt-0.5">no live activation</span>
            </div>
          </div>
        </div>
      </section>

      {/* Recent Board Runs List */}
      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Recent board runs</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Safe outcomes and audit views.</p>
        </div>

        <div className="space-y-3">
          {recentRuns.length > 0 ? (
            recentRuns.map((r, idx) => (
              <Link
                key={idx}
                to={`/board-runs/${r.boardRunId}`}
                className="flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all group"
              >
                <div>
                  <b className="block text-sm font-semibold text-slate-900 dark:text-white">{r.runTime}</b>
                  <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                    {r.outcome} · {r.boardRunId}
                  </span>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-teal-500 transition-colors" />
              </Link>
            ))
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              No retained board runs in this prototype.
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
