import React, { useState } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { Plus, AlertTriangle, FileCode } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Boards: React.FC = () => {
  const [boards] = useState([
    {
      id: 'board-greenhouse-01',
      name: 'Stripe Engineering',
      family: 'greenhouse',
      targetUrl: 'https://boards.greenhouse.io/stripe',
      status: 'active',
      revision: 4,
      failures: 0,
      maxFailures: 3,
      scheduleCron: '0 */6 * * *',
      lastRun: '10 mins ago'
    },
    {
      id: 'board-lever-02',
      name: 'Datadog Product & Eng',
      family: 'lever',
      targetUrl: 'https://jobs.lever.co/datadog',
      status: 'active',
      revision: 2,
      failures: 0,
      maxFailures: 3,
      scheduleCron: '0 */12 * * *',
      lastRun: '45 mins ago'
    },
    {
      id: 'board-ashby-03',
      name: 'Linear Core Team',
      family: 'ashby',
      targetUrl: 'https://jobs.ashbyhq.com/linear',
      status: 'active',
      revision: 1,
      failures: 0,
      maxFailures: 3,
      scheduleCron: '0 0 * * *',
      lastRun: '2 hours ago'
    },
    {
      id: 'board-workday-04',
      name: 'Vercel Infrastructure',
      family: 'workday',
      targetUrl: 'https://vercel.wd1.myworkdayjobs.com/Careers',
      status: 'held',
      revision: 1,
      failures: 1,
      maxFailures: 3,
      scheduleCron: '0 */4 * * *',
      lastRun: '5 hours ago'
    }
  ]);

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
        {boards.map((board) => (
          <div
            key={board.id}
            className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-slate-900 dark:text-white text-base">{board.name}</h3>
                  <span className="text-xs text-slate-400 font-mono">{board.id}</span>
                </div>
                <StatusBadge status={board.status} />
              </div>

              <div className="mt-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1.5 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Family Adapter:</span>
                  <span className="font-semibold text-slate-700 dark:text-slate-300 uppercase">{board.family}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Target URL:</span>
                  <a
                    href={board.targetUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-teal-600 dark:text-teal-400 truncate max-w-[200px] hover:underline"
                  >
                    {board.targetUrl}
                  </a>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Active Revision:</span>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Rev {board.revision}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Schedule (Cron):</span>
                  <span className="text-slate-700 dark:text-slate-300">{board.scheduleCron}</span>
                </div>
              </div>
            </div>

            {/* Failure Counter Bar */}
            <div className="pt-2">
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-500 font-medium">Consecutive Parser Failures:</span>
                <span className="font-mono font-semibold text-slate-700 dark:text-slate-300">
                  {board.failures} / {board.maxFailures}
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    board.failures >= board.maxFailures
                      ? 'bg-rose-500'
                      : board.failures > 0
                      ? 'bg-amber-500'
                      : 'bg-teal-500'
                  }`}
                  style={{ width: `${(board.failures / board.maxFailures) * 100}%` }}
                />
              </div>
              {board.failures >= board.maxFailures && (
                <div className="mt-2 flex items-center gap-1.5 text-xs text-rose-600 dark:text-rose-400 font-medium">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Auto-held due to consecutive parser failures. Revision update required.</span>
                </div>
              )}
            </div>

            {/* Card Footer Actions */}
            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-slate-400 font-mono">Last run: {board.lastRun}</span>
              <Link
                to={`/boards/config/${board.id}`}
                className="inline-flex items-center gap-1 text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>Edit Config</span>
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
