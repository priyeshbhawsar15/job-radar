import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, Save, ShieldAlert, CheckCircle } from 'lucide-react';

export const BoardConfig: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [board, setBoard] = useState<any>(null);
  const [url, setUrl] = useState<string>('');
  const [maxPages, setMaxPages] = useState<number>(3);
  const [cron, setCron] = useState<string>('0 */6 * * *');
  const [savedMsg, setSavedMsg] = useState<boolean>(false);

  useEffect(() => {
    if (!id) return;
    fetch('/api/v1/boards/' + id)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setBoard(data);
          setUrl(data.target_url || '');
          setMaxPages(data.max_pages || 3);
          setCron(data.schedule_cron || '0 */6 * * *');
        }
      })
      .catch((e) => console.error(e));
  }, [id]);

  if (!board) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading configuration...</div>;
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetch('/api/v1/boards/' + id + '/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_url: url,
        max_pages: Number(maxPages),
        schedule_cron: cron
      })
    })
      .then((res) => res.json())
      .then(() => {
        setSavedMsg(true);
        setTimeout(() => setSavedMsg(false), 3000);
      })
      .catch((err) => alert('Error saving config: ' + err));
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Configuration
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Edit {board.name} configuration
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Update extraction parameters, pagination depth, and target URLs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/boards/' + board.board_id)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Cancel</span>
          </button>
        </div>
      </header>

      {savedMsg && (
        <div className="p-3.5 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs flex items-center gap-2 font-bold">
          <CheckCircle className="w-4 h-4 text-teal-500 shrink-0" />
          <span>Configuration saved successfully! New draft revision activated.</span>
        </div>
      )}

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <form
          onSubmit={handleSubmit}
          className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4"
        >
          <div className="p-3.5 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs flex items-start gap-2.5">
            <ShieldAlert className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" />
            <div>
              <b>Configuration Gate:</b> Updates create an approved revision in the live engine database.
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Board ID
            </label>
            <input
              type="text"
              value={board.board_id}
              readOnly
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-950 text-slate-500 font-mono text-xs cursor-not-allowed"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Adapter family
            </label>
            <input
              type="text"
              value={board.family}
              readOnly
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-950 text-slate-500 font-mono text-xs cursor-not-allowed"
            />
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
              Max Pages to Extract (Pagination Depth)
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Number of pages to iterate per run (default: 3 pages = up to 60 jobs per run).
            </p>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Schedule (Cron)
            </label>
            <input
              type="text"
              value={cron}
              onChange={(e) => setCron(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <button
            type="submit"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold shadow-xs transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>Save Configuration</span>
          </button>
        </form>

        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Current Active Parameters
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Live runtime parameters applied to execution engine runs.
            </p>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-between">
              <span>Adapter Family:</span>
              <b className="text-teal-600 dark:text-teal-400">{board.family}</b>
            </div>
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-between">
              <span>Max Pages Depth:</span>
              <b className="text-teal-600 dark:text-teal-400">{maxPages} pages (up to {maxPages * 20} jobs)</b>
            </div>
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-between">
              <span>Status:</span>
              <StatusBadge status={board.status} size="sm" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
