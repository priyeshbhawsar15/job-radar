import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { MOCK_BOARDS } from '../data/mockData';

export const Boards: React.FC = () => {
  const navigate = useNavigate();
  const [boards, setBoards] = useState<BoardItem[]>(MOCK_BOARDS);

  useEffect(() => {
    const fetchApiBoards = async () => {
      try {
        const res = await fetch('/api/v1/boards');
        if (res.ok) {
          const apiBoards: any[] = await res.json();
          if (apiBoards && apiBoards.length > 0) {
            const mapped: BoardItem[] = apiBoards.map((b) => ({
              id: b.board_id,
              name: b.name,
              adapter: b.family,
              url: b.target_url || 'https://example.com/careers',
              state: b.status === 'active' ? 'reviewed' : b.status,
              rev: 'rev-01',
              runs: 10,
              success: b.consecutive_parser_failures > 0 ? 50 : 100,
              missing: b.consecutive_parser_failures >= 3 ? ['listing readiness descriptor', 'reviewed detail route allowlist'] : [],
              next: b.schedule_cron || '06:00 IST',
            }));

            const existingIds = new Set(MOCK_BOARDS.map((x) => x.id));
            const fresh = mapped.filter((x) => !existingIds.has(x.id));
            setBoards([...MOCK_BOARDS, ...fresh]);
          }
        }
      } catch (e) {
        console.error('API boards fetch error:', e);
      }
    };
    fetchApiBoards();
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Boards Index
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Boards
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
            Reviewed board configuration, readiness, missing fields, and observed run health.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/runs"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <span>Runs</span>
          </Link>
        </div>
      </header>

      {/* Notice Banner */}
      <div className="p-3.5 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs">
        Board cards are static representative configuration snapshots. An enabled production board requires a reviewed revision and all mandatory controls.
      </div>

      {/* Boards Card Grid */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {boards.map((b) => (
          <Link
            key={b.id}
            to={`/boards/${b.id}`}
            className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all flex flex-col justify-between space-y-4 group shadow-xs"
          >
            <div>
              <div className="flex items-start justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
                <div>
                  <p className="text-[10px] uppercase font-bold text-teal-600 dark:text-teal-400 font-mono">
                    {b.adapter}
                  </p>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white mt-0.5 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                    {b.name}
                  </h2>
                </div>
                <StatusBadge status={b.state} />
              </div>

              <p className="text-xs font-mono text-slate-500 dark:text-slate-400 truncate mt-3">
                {b.url}
              </p>

              <div className="grid grid-cols-2 gap-4 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80">
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  <b className="block text-xl font-bold font-mono text-slate-900 dark:text-white">{b.runs}</b>
                  observed runs
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  <b className="block text-xl font-bold font-mono text-slate-900 dark:text-white">{b.success}%</b>
                  completion
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80">
              <p
                className={`text-xs font-mono font-medium ${
                  b.missing.length > 0
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-slate-500 dark:text-slate-400'
                }`}
              >
                {b.missing.length > 0
                  ? `${b.missing.length} mandatory field${b.missing.length > 1 ? 's' : ''} missing`
                  : `Next due: ${b.next}`}
              </p>
            </div>
          </Link>
        ))}
      </section>
    </div>
  );
};
