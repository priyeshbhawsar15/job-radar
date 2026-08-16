import React, { useState, useEffect } from 'react';
import { Search, Filter, Briefcase, ExternalLink, ChevronRight, X, Building2, MapPin } from 'lucide-react';

export const Jobs: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [employmentFilter, setEmploymentFilter] = useState<string>('all');
  const [selectedJob, setSelectedJob] = useState<any | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await fetch('/api/v1/jobs');
        if (res.ok) {
          const data = await res.json();
          setJobs(data);
        }
      } catch (e) {
        console.error('Failed to fetch jobs', e);
      } finally {
        setLoading(false);
      }
    };
    fetchJobs();
  }, []);

  const filteredJobs = jobs.filter((job) => {
    const title = job.title || '';
    const company = job.company || '';
    const location = job.location_raw || '';
    const matchesSearch =
      title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      location.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesType =
      employmentFilter === 'all' || job.employment_type === employmentFilter;

    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Normalized Jobs Explorer</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Unified schema job candidates extracted across parser revisions with deduplication fingerprints.
        </p>
      </div>

      {/* Search & Filter Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search by title, company, or location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-teal-500"
          />
        </div>

        <div className="relative">
          <Filter className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <select
            value={employmentFilter}
            onChange={(e) => setEmploymentFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-teal-500"
          >
            <option value="all">All Employment Types</option>
            <option value="full_time">Full-Time</option>
            <option value="part_time">Part-Time</option>
            <option value="contract">Contract</option>
          </select>
        </div>
      </div>

      {/* Main Jobs Table */}
      <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-3">Job Title & Company</th>
                <th className="py-3 px-3">Location</th>
                <th className="py-3 px-3">Department</th>
                <th className="py-3 px-3">First Seen</th>
                <th className="py-3 px-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
              {filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400 font-mono">
                    {loading ? 'Loading jobs...' : 'No normalized candidate jobs found.'}
                  </td>
                </tr>
              ) : (
                filteredJobs.map((job) => (
                  <tr
                    key={job.candidate_id}
                    onClick={() => setSelectedJob(job)}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-3">
                      <span className="font-semibold text-slate-900 dark:text-white block text-sm">{job.title}</span>
                      <span className="text-slate-500 font-medium">{job.company}</span>
                    </td>
                    <td className="py-3.5 px-3 text-slate-600 dark:text-slate-400">{job.location_raw || 'Unspecified'}</td>
                    <td className="py-3.5 px-3">
                      <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[11px] font-medium">
                        {job.department || 'General'}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-slate-500 font-mono">
                      {job.first_seen_at ? new Date(job.first_seen_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="py-3.5 px-3 text-right">
                      <ChevronRight className="w-4 h-4 text-slate-400 ml-auto" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Job Details Modal/Drawer */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-teal-600 dark:text-teal-400" />
                <h3 className="font-semibold text-slate-900 dark:text-white">Normalized Job Detail</h3>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">{selectedJob.title}</h2>
                <div className="flex items-center gap-4 mt-2 text-xs text-slate-500 font-medium">
                  <span className="flex items-center gap-1">
                    <Building2 className="w-3.5 h-3.5 text-slate-400" />
                    {selectedJob.company}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    {selectedJob.location_raw || 'Unspecified'}
                  </span>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-2 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Candidate ID:</span>
                  <span className="text-teal-600 dark:text-teal-400 font-bold">{selectedJob.candidate_id}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Department:</span>
                  <span className="text-slate-700 dark:text-slate-300">{selectedJob.department || 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Employment Type:</span>
                  <span className="text-slate-700 dark:text-slate-300 capitalize">{selectedJob.employment_type || 'N/A'}</span>
                </div>
              </div>

              <div>
                <span className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Canonical Job URL
                </span>
                <a
                  href={selectedJob.public_apply_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:underline break-all font-mono"
                >
                  <span>{selectedJob.public_apply_url}</span>
                  <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                </a>
              </div>
            </div>

            <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30 text-right">
              <button
                onClick={() => setSelectedJob(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
