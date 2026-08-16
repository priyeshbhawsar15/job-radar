import React, { useState, useEffect } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { Plus, AlertTriangle, FileCode } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Boards: React.FC = () => {
  const [boards, setBoards] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchBoards = async () => {
      try {
        const res = await fetch('/api/v1/boards');
        if (res.ok) {
          const data = await res.json();
          setBoards(data);
        }
      } catch (e) {
        console.error('Failed to fetch boards', e);
      } finally {
        setLoading(false);
      }
    };
    fetchBoards();
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Board Registry</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Registered target boards, parser family revisions, and failure threshold tracking.
          </p>
        </div>
        <Link
          to="/boards/config/new"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>New Board Config</span>
        </Link>
      </div>

      {/* Grid of registered boards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {loading ? (
          <div className="col-span-2 py-8 text-center text-slate-400 font-mono">Loading boards...</div>
        ) : (
          boards.map((board) => (
            <div
              key={board.board_id}
              className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-white text-base">{board.name}</h3>
                    <span className="text-xs text-slate-400 font-mono">{board.board_id}</span>
                  </div>
                  <StatusBadge status={board.status === 'active' ? 'healthy' : board.status} />
                </div>

                <div className="mt-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1.5 text-xs font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Family Adapter:</span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 uppercase">{board.family}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Target URL:</span>
                    <a
                      href={board.target_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-teal-600 dark:text-teal-400 truncate max-w-[200px] hover:underline"
                    >
                      {board.target_url}
                    </a>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Schedule (Cron):</span>
                    <span className="text-slate-700 dark:text-slate-300">{board.schedule_cron}</span>
                  </div>
                </div>
              </div>

              {/* Failure Counter Bar */}
              <div className="pt-2">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-slate-500 font-medium">Consecutive Parser Failures:</span>
                  <span className="font-mono font-semibold text-slate-700 dark:text-slate-300">
                    {board.consecutive_parser_failures} / 3
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      board.consecutive_parser_failures >= 3
                        ? 'bg-rose-500'
                        : board.consecutive_parser_failures > 0
                        ? 'bg-amber-500'
                        : 'bg-teal-500'
                    }`}
                    style={{ width: `${(board.consecutive_parser_failures / 3) * 100}%` }}
                  />
                </div>
                {board.consecutive_parser_failures >= 3 && (
                  <div className="mt-2 flex items-center gap-1.5 text-xs text-rose-600 dark:text-rose-400 font-medium">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Auto-held due to consecutive parser failures. Revision update required.</span>
                  </div>
                )}
              </div>

              {/* Card Footer Actions */}
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <span className="text-[11px] text-slate-400 font-mono">Registered</span>
                <Link
                  to={`/boards/config/${board.board_id}`}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
                >
                  <FileCode className="w-3.5 h-3.5" />
                  <span>Edit Config</span>
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
