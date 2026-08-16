import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, Edit3, AlertTriangle, CheckCircle, ExternalLink, ChevronRight, Play } from 'lucide-react';

export const BoardDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [board, setBoard] = useState<any | null>(null);
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [triggering, setTriggering] = useState<boolean>(false);
  const [toastMsg, setToastMsg] = useState<string>('');

  const loadData = () => {
    if (!id) return;
    Promise.all([
      fetch('/api/v1/boards').then((res) => (res.ok ? res.json() : [])),
      fetch('/api/v1/runs').then((res) => (res.ok ? res.json() : []))
    ])
      .then(([boards, runs]) => {
        const found = boards.find((b: any) => b.board_id === id || b.name.toLowerCase() === id.toLowerCase());
        if (found) {
          const boardRunsForThisBoard = runs.filter((r: any) => r.board_id === found.board_id);
          const successCount = boardRunsForThisBoard.filter((r: any) => r.outcome === 'success').length;
          const totalRuns = boardRunsForThisBoard.length;
          const successRate = totalRuns > 0 ? Math.round((successCount / totalRuns) * 100) : 0;

          setBoard({
            id: found.board_id,
            name: found.name,
            adapter: found.family,
            url: found.target_url || found.url || '',
            state: found.status === 'active' ? 'reviewed' : found.status,
            rev: 'rev-01',
            runs: totalRuns,
            success: successRate,
            missing: found.consecutive_parser_failures >= 3 ? ['consecutive parser failures threshold exceeded'] : [],
            next: found.schedule_cron || '06:00 IST',
          });

          setRecentRuns(boardRunsForThisBoard.map((br: any) => ({
            runTime: br.created_at || 'Recently',
            outcome: br.outcome + ' (' + br.stage + ')',
            boardRunId: br.run_id,
            parentRunId: br.pipeline_id
          })));
        }
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleRunBoard = async () => {
    if (!board) return;
    setTriggering(true);
    try {
      const res = await fetch('/api/v1/runs/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ board_id: board.id }),
      });
      if (res.ok) {
        setToastMsg('Run triggered successfully for ' + board.name + '!');
        setTimeout(() => {
          setToastMsg('');
          loadData();
        }, 2000);
      } else {
        alert('Failed to trigger run.');
      }
    } catch (e) {
      console.error(e);
      alert('Error triggering run.');
    } finally {
      setTriggering(false);
    }
  };

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
          <button
            onClick={handleRunBoard}
            disabled={triggering}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{triggering ? 'Executing...' : 'Run Board'}</span>
          </button>
          <Link
            to={'/boards/' + board.id + '/config'}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
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

      {/* Trigger Notification Toast */}
      {toastMsg && (
        <div className="p-4 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs font-semibold flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-teal-500" />
          <span>{toastMsg}</span>
        </div>
      )}

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
                {board.missing.map((item: string, idx: number) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="mt-4 p-3.5 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" />
              <div>
                <b>All representative mandatory configuration fields are present.</b> Target URL & filter active.
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
              <span className="block text-[11px] text-slate-400 mt-0.5">active configuration</span>
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
                to={'/board-runs/' + r.boardRunId}
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
              No runs executed yet for this board.
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
