import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { Search, Filter } from 'lucide-react';

export const Boards: React.FC = () => {
  const [boards, setBoards] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [adapterFilter, setAdapterFilter] = useState<string>('all');

  useEffect(() => {
    fetch('/api/v1/boards')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        setBoards(data.sort((a, b) => a.name.localeCompare(b.name)));
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const uniqueAdapters = Array.from(new Set(boards.map((b) => b.family))).sort();

  const filteredBoards = boards
    .filter((b) => {
      const q = searchTerm.toLowerCase();
      const matchesText = (b.name + ' ' + b.target_url + ' ' + b.family).toLowerCase().includes(q);
      const matchesAdapter = adapterFilter === 'all' || b.family.toLowerCase() === adapterFilter.toLowerCase();
      return matchesText && matchesAdapter;
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Boards Registry
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Boards ({filteredBoards.length})
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

      {/* Filter Control Box */}
      <section className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Search Box */}
          <div className="space-y-1">
            <label htmlFor="boardSearch" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Search boards
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                id="boardSearch"
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Company name, URL, adapter..."
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>

          {/* Adapter Filter Dropdown */}
          <div className="space-y-1">
            <label htmlFor="adapterFilter" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Filter by Adapter Family
            </label>
            <div className="relative">
              <Filter className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <select
                id="adapterFilter"
                value={adapterFilter}
                onChange={(e) => setAdapterFilter(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              >
                <option value="all">All Adapters ({boards.length})</option>
                {uniqueAdapters.map((fam) => (
                  <option key={fam} value={fam}>
                    {fam.toUpperCase()} ({boards.filter((b) => b.family === fam).length})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* Boards Card Grid */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full p-8 text-center text-slate-400 font-mono text-xs">Loading boards...</div>
        ) : filteredBoards.length > 0 ? (
          filteredBoards.map((b) => (
            <Link
              key={b.board_id}
              to={'/boards/' + b.board_id}
              className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all flex flex-col justify-between space-y-4 group shadow-xs"
            >
              <div>
                <div className="flex items-start justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
                  <div>
                    <p className="text-[10px] uppercase font-bold text-teal-600 dark:text-teal-400 font-mono">
                      {b.family}
                    </p>
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mt-0.5 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                      {b.name}
                    </h2>
                  </div>
                  <StatusBadge status={b.status === 'active' ? 'reviewed' : b.status} />
                </div>

                <p className="text-xs font-mono text-slate-500 dark:text-slate-400 truncate mt-3">
                  {b.target_url}
                </p>

                <div className="grid grid-cols-2 gap-4 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80">
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    <b className="block text-xl font-bold font-mono text-slate-900 dark:text-white">Active</b>
                    status
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    <b className="block text-xl font-bold font-mono text-slate-900 dark:text-white">100%</b>
                    completion
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80">
                <p className="text-xs font-mono font-medium text-slate-500 dark:text-slate-400">
                  Next due: {b.schedule_cron || '06:00 IST'}
                </p>
              </div>
            </Link>
          ))
        ) : (
          <div className="col-span-full p-8 text-center text-slate-400 font-mono text-xs border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
            No boards match adapter filter "{adapterFilter}".
          </div>
        )}
      </section>
    </div>
  );
};
