import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { Search, Filter, ArrowLeft, ChevronRight } from 'lucide-react';
import { MOCK_JOBS, MOCK_BOARDS } from '../data/mockData';

export const Jobs: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [dateSort, setDateSort] = useState<'new' | 'old'>('new');
  const [boardFilter, setBoardFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [jobs, setJobs] = useState<JobItem[]>(MOCK_JOBS);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    // Attempt to merge with API data if backend returns jobs
    const fetchApiJobs = async () => {
      try {
        const res = await fetch('/api/v1/jobs');
        if (res.ok) {
          const apiJobs: any[] = await res.json();
          if (apiJobs && apiJobs.length > 0) {
            const mapped: JobItem[] = apiJobs.map((j) => ({
              id: j.candidate_id || j.id,
              title: j.title,
              company: j.company,
              location: j.location || j.location_raw || 'Unspecified',
              url: j.public_apply_url || j.url || '',
              posted: j.first_seen_at ? j.first_seen_at.split('T')[0] : '2026-08-20',
              type: j.employment_type || 'Full-time',
              department: j.department || 'Engineering',
              board: j.board_id,
              source: j.source || `${j.board_id}:${j.candidate_id}`,
              revision: 'rev-01',
              discovered: j.first_seen_at || new Date().toISOString(),
              normalization: 'accepted · norm-v3',
              eligibility: 'eligible · policy-11',
              ops: 'accepted',
              receipt: `OPS-${j.candidate_id}`
            }));

            // Merge with mock jobs ensuring unique IDs
            const existingIds = new Set(MOCK_JOBS.map((x) => x.id));
            const fresh = mapped.filter((x) => !existingIds.has(x.id));
            setJobs([...MOCK_JOBS, ...fresh]);
          }
        }
      } catch (e) {
        console.error('API jobs fetch error:', e);
      }
    };
    fetchApiJobs();
  }, []);

  const filteredJobs = jobs
    .filter((j) => {
      const q = searchTerm.toLowerCase();
      const textMatch =
        `${j.title} ${j.company} ${j.location} ${j.board}`.toLowerCase().includes(q);
      const boardMatch = boardFilter === 'all' || j.board.toLowerCase() === boardFilter.toLowerCase();
      const statusMatch = statusFilter === 'all' || j.ops.toLowerCase() === statusFilter.toLowerCase();
      return textMatch && boardMatch && statusMatch;
    })
    .sort((a, b) => {
      const comp = b.discovered.localeCompare(a.discovered);
      return dateSort === 'new' ? comp : -comp;
    });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Extracted jobs
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Search and filter normalized mock records.
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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

          {/* Board Filter Dropdown */}
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
              <option value="all">All boards</option>
              {MOCK_BOARDS.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
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
              <option value="accepted">Accepted</option>
              <option value="held">Held</option>
            </select>
          </div>
        </div>

        {/* Job Cards List */}
        <div id="jobList" className="space-y-3 pt-2">
          {filteredJobs.length > 0 ? (
            filteredJobs.map((j) => (
              <Link
                key={j.id}
                to={`/jobs/${j.id}`}
                className="flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-teal-500 dark:hover:border-teal-500 transition-all group shadow-xs"
              >
                <div>
                  <b className="block text-sm font-bold text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                    {j.title}
                  </b>
                  <span className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 block">
                    {j.company} · {j.posted}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={j.ops} size="sm" />
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-teal-500 transition-colors" />
                </div>
              </Link>
            ))
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
