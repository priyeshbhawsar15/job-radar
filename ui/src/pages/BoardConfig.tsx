import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, Save, ShieldAlert } from 'lucide-react';
import { getBoard } from '../data/mockData';
import type { BoardItem } from '../data/mockData';

export const BoardConfig: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [board, setBoard] = useState<BoardItem | null>(null);
  const [url, setUrl] = useState<string>('');
  const [cron, setCron] = useState<string>('Daily · 06:00 Asia/Kolkata');
  const [readiness, setReadiness] = useState<string>('ready-listing-v2');

  useEffect(() => {
    if (!id || id === 'new') {
      setBoard({
        id: 'new-board',
        name: 'New Board',
        adapter: 'greenhouse',
        url: 'https://boards.greenhouse.io/example',
        state: 'draft',
        rev: 'rev-01',
        runs: 0,
        success: 100,
        missing: ['reviewed readiness descriptor', 'reviewed detail route allowlist'],
        next: 'Draft'
      });
    } else {
      const b = getBoard(id);
      if (b) {
        setBoard(b);
        setUrl(b.url);
        if (b.missing.includes('reviewed readiness descriptor')) {
          setReadiness('Missing — required');
        }
      } else {
        setBoard({
          id,
          name: id,
          adapter: 'custom',
          url: 'https://example.com/careers',
          state: 'draft',
          rev: 'rev-01',
          runs: 0,
          success: 100,
          missing: [],
          next: 'Review required'
        });
      }
    }
  }, [id]);

  if (!board) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading configuration...</div>;
  }

  const requiredFields = [
    'adapter family',
    'public listing link',
    'detail route allowlist',
    'pagination cap',
    'readiness descriptor',
    'resource policy'
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert('Static prototype: configuration is not saved.');
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Configuration
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Edit {board.name} configuration
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Static form only. Saving, review, state transitions, secret values, and source enablement are intentionally unavailable.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/boards/${board.id}`)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Cancel</span>
          </button>
        </div>
      </header>

      {/* Breadcrumb path */}
      <p className="text-xs text-slate-500 dark:text-slate-400">
        <Link to="/boards" className="hover:underline">Boards</Link> /{' '}
        <Link to={`/boards/${board.id}`} className="hover:underline">{board.name}</Link> / configuration
      </p>

      {/* Main Grid: Form + Status Matrix */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form Card */}
        <form
          onSubmit={handleSubmit}
          className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4"
        >
          {/* Review Gate Notice */}
          <div className="p-3.5 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs flex items-start gap-2.5">
            <ShieldAlert className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" />
            <div>
              <b>Review gate:</b> edits create a draft revision in the real design; an editor cannot self-review or enable it.
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Board ID
            </label>
            <input
              type="text"
              value={board.id}
              readOnly
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-950 text-slate-500 font-mono text-xs cursor-not-allowed"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Adapter family
            </label>
            <select
              value={board.adapter}
              onChange={(e) => setBoard({ ...board, adapter: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              <option value={board.adapter}>{board.adapter}</option>
              <option value="greenhouse">greenhouse</option>
              <option value="lever">lever</option>
              <option value="ashby">ashby</option>
              <option value="workday">workday</option>
              <option value="careerpage">careerpage</option>
              <option value="custom">custom</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Public listing URL
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Schedule / timezone
            </label>
            <input
              type="text"
              value={cron}
              onChange={(e) => setCron(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Reviewed readiness descriptor
            </label>
            <input
              type="text"
              value={readiness}
              onChange={(e) => setReadiness(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <button
            type="submit"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold shadow-xs transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>Save draft (demo)</span>
          </button>
        </form>

        {/* Required Configuration Status Matrix */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Required configuration status
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Typed fields are validated server-side in the approved system design.
            </p>
          </div>

          <div className="space-y-3">
            {requiredFields.map((field) => {
              const prefix = field.split(' ')[0];
              const isMissing = board.missing.some((m) => m.toLowerCase().includes(prefix));
              return (
                <div
                  key={field}
                  className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between shadow-xs"
                >
                  <b className="text-xs font-bold text-slate-900 dark:text-white capitalize">{field}</b>
                  <StatusBadge status={isMissing ? 'draft' : 'reviewed'} size="sm" />
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
};
