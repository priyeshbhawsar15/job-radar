import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { Search, Filter, ChevronRight } from 'lucide-react';

export const Jobs: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [dateSort, setDateSort] = useState<'new' | 'old'>('new');
  const [boardFilter, setBoardFilter] = useState<string>('all');
  const [adapterFilter, setAdapterFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [enrichmentFilter, setEnrichmentFilter] = useState<string>('all');
  const [jobs, setJobs] = useState<any[]>([]);
  const [boards, setBoards] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/jobs').then((res) => (res.ok ? res.json() : [])),
      fetch('/api/v1/boards').then((res) => (res.ok ? res.json() : []))
    ])
      .then(([jData, bData]) => {
        setJobs(jData);
        setBoards(bData);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const boardFamilyMap: Record<string, string> = {};
  boards.forEach((b) => {
    boardFamilyMap[b.board_id] = b.family;
  });

  const uniqueAdapters = Array.from(new Set(boards.map((b) => b.family))).sort();

  const filteredJobs = jobs
    .filter((j) => {
      const q = searchTerm.toLowerCase();
      const jobAdapter = boardFamilyMap[j.board_id] || j.adapter || 'unknown';
      const textMatch = (j.title + ' ' + j.company + ' ' + (j.location || '') + ' ' + j.board_id + ' ' + jobAdapter).toLowerCase().includes(q);
      const boardMatch = boardFilter === 'all' || j.board_id.toLowerCase() === boardFilter.toLowerCase();
      const adapterMatch = adapterFilter === 'all' || jobAdapter.toLowerCase() === adapterFilter.toLowerCase();
      const statusMatch = statusFilter === 'all' || (j.job_ops_status || 'accepted').toLowerCase() === statusFilter.toLowerCase();
      const enrichmentMatch =
        enrichmentFilter === 'all' ||
        (j.detail_enrichment_status || 'pending').toLowerCase() === enrichmentFilter.toLowerCase();
      return textMatch && boardMatch && adapterMatch && statusMatch && enrichmentMatch;
    })
    .sort((a, b) => {
      const timeA = a.first_seen_at || '';
      const timeB = b.first_seen_at || '';
      const comp = timeB.localeCompare(timeA);
      return dateSort === 'new' ? comp : -comp;
    });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Normalized Candidates
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Extracted jobs ({filteredJobs.length})
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Search and filter normalized candidate records by board, adapter family, or status.
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
      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
          {/* Search Input */}
          <div className="space-y-1">
            <label htmlFor="jobSearch" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Search jobs
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                id="jobSearch"
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Title, company, location"
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>

          {/* Date Sort Dropdown */}
          <div className="space-y-1">
            <label htmlFor="jobDate" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Sort by date
            </label>
            <select
              id="jobDate"
              value={dateSort}
              onChange={(e) => setDateSort(e.target.value as 'new' | 'old')}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              <option value="new">Newest first</option>
              <option value="old">Oldest first</option>
            </select>
          </div>

          {/* Dynamic Board Filter Dropdown */}
          <div className="space-y-1">
            <label htmlFor="jobBoard" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Board
            </label>
            <select
              id="jobBoard"
              value={boardFilter}
              onChange={(e) => setBoardFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              <option value="all">All boards ({boards.length})</option>
              {boards.map((b) => (
                <option key={b.board_id} value={b.board_id}>
                  {b.name} ({b.family})
                </option>
              ))}
            </select>
          </div>

          {/* New Adapter Type Filter Dropdown */}
          <div className="space-y-1">
            <label htmlFor="jobAdapter" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Adapter Type
            </label>
            <select
              id="jobAdapter"
              value={adapterFilter}
              onChange={(e) => setAdapterFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              <option value="all">All adapters ({uniqueAdapters.length})</option>
              {uniqueAdapters.map((fam) => (
                <option key={fam} value={fam}>
                  {fam.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Job Ops Status Dropdown */}
          <div className="space-y-1">
            <label htmlFor="jobStatus" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Job Ops status
            </label>
            <select
              id="jobStatus"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              <option value="all">All outcomes</option>
              <option value="accepted">Accepted (Imported)</option>
              <option value="queued">Queued</option>
              <option value="dispatching">Dispatching</option>
              <option value="uncertain">Uncertain</option>
              <option value="untracked">Untracked</option>
            </select>
          </div>

          {/* Enrichment Status Filter Dropdown */}
          <div className="space-y-1">
            <label htmlFor="jobEnrichment" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Enrichment status
            </label>
            <select
              id="jobEnrichment"
              value={enrichmentFilter}
              onChange={(e) => setEnrichmentFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              <option value="all">All enrichment</option>
              <option value="succeeded">Succeeded only</option>
              <option value="failed">Failed only</option>
              <option value="pending">Pending only</option>
            </select>
          </div>
        </div>

        {/* Job Cards List */}
        <div id="jobList" className="space-y-3 pt-2">
          {loading ? (
            <div className="p-8 text-center text-slate-400 font-mono text-xs">Loading jobs...</div>
          ) : filteredJobs.length > 0 ? (
            filteredJobs.map((j) => {
              const adapterName = boardFamilyMap[j.board_id] || 'unknown';
              return (
                <Link
                  key={j.candidate_id}
                  to={'/jobs/' + j.candidate_id}
                  className="flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all group shadow-xs"
                >
                  <div>
                    <b className="block text-sm font-bold text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                      {j.title}
                    </b>
                    <span className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 block">
                      {j.company} · {j.location || 'Unspecified'} · <span className="font-mono text-teal-600 dark:text-teal-400 uppercase text-[10px]">{adapterName}</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    {j.detail_enrichment_status === 'failed' && (
                      <StatusBadge
                        status="failed"
                        label={`Failed enrichment: ${j.detail_enrichment_error_code || 'unknown'}`}
                        size="sm"
                      />
                    )}
                    <StatusBadge status={j.job_ops_status || 'accepted'} size="sm" />
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-teal-500 transition-colors" />
                  </div>
                </Link>
              );
            })
          ) : (
            <div className="empty p-10 text-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              No jobs match these filters.
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
