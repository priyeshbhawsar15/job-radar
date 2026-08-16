import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, Copy, Check, ExternalLink, Code2 } from 'lucide-react';
import { getJob } from '../data/mockData';

export const JobDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobItem | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!id) return;
    // Check mock data first
    const mock = getJob(id);
    if (mock) {
      setJob(mock);
      setLoading(false);
    } else {
      // Fetch from API if needed
      fetch('/api/v1/jobs')
        .then((res) => (res.ok ? res.json() : []))
        .then((data: any[]) => {
          const found = data.find((j: any) => j.candidate_id === id || j.id === id);
          if (found) {
            setJob({
              id: found.candidate_id || found.id,
              title: found.title,
              company: found.company,
              location: found.location || found.location_raw || 'Unspecified',
              url: found.public_apply_url || found.url || '',
              posted: found.first_seen_at ? found.first_seen_at.split('T')[0] : '2026-08-20',
              type: found.employment_type || 'Full-time',
              department: found.department || 'Engineering',
              board: found.board_id || 'oracle',
              source: found.source || `${found.board_id}:${found.candidate_id}`,
              revision: 'rev-01',
              discovered: found.first_seen_at || new Date().toISOString(),
              normalization: 'accepted · norm-v3',
              eligibility: 'eligible · policy-11',
              ops: 'accepted',
              receipt: `OPS-${id}`
            });
          }
        })
        .catch((e) => console.error(e))
        .finally(() => setLoading(false));
    }
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading job details...</div>;
  }

  if (!job) {
    return (
      <div className="p-8 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Job Candidate Not Found</h2>
        <p className="text-sm text-slate-500">The requested job ID standard reference "{id}" could not be found.</p>
        <Link to="/jobs" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 text-white font-medium text-xs">
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Extracted Jobs</span>
        </Link>
      </div>
    );
  }

  const payload = {
    idempotency_reference: `jr:${job.id}:policy-11`,
    title: job.title,
    company: job.company,
    location: job.location,
    apply_url: job.url,
    posting_date: job.posted,
    employment_type: job.type,
    department: job.department,
    board_id: job.board,
    source_stable_id: job.source,
    board_revision: job.revision,
    discovered_at: job.discovered,
    normalization: job.normalization,
    eligibility: job.eligibility,
    job_ops_status: job.ops,
    job_ops_receipt: job.receipt,
  };

  const payloadString = JSON.stringify(payload, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(payloadString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const kvFields = [
    { key: 'title', label: 'Title', value: job.title },
    { key: 'company', label: 'Company', value: job.company },
    { key: 'location', label: 'Location', value: job.location },
    { key: 'apply_url', label: 'Apply URL', value: job.url, isLink: true },
    { key: 'posting_date', label: 'Posting date', value: job.posted },
    { key: 'employment_type', label: 'Employment type', value: job.type },
    { key: 'department', label: 'Department', value: job.department },
    { key: 'board_id', label: 'Board ID', value: job.board },
    { key: 'source_stable_id', label: 'Source stable ID', value: job.source },
    { key: 'board_revision', label: 'Board revision', value: job.revision },
    { key: 'discovered_at', label: 'Discovered at', value: job.discovered },
    { key: 'normalization', label: 'Normalization', value: job.normalization },
    { key: 'eligibility', label: 'Eligibility', value: job.eligibility },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Job Candidate
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            {job.title}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {job.company} · normalized job candidate
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/jobs')}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to jobs</span>
          </button>
        </div>
      </header>

      {/* Breadcrumb path */}
      <p className="text-xs text-slate-500 dark:text-slate-400">
        <Link to="/jobs" className="hover:underline">Extracted jobs</Link> / {job.id}
      </p>

      {/* Two column grid */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Candidate status & KV fields */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Candidate status</h2>
            <StatusBadge status={job.ops} />
          </div>

          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-y-3 gap-x-4 text-xs">
            {kvFields.map((field) => (
              <React.Fragment key={field.key}>
                <dt className="text-slate-500 dark:text-slate-400 font-medium capitalize">
                  {field.label}
                </dt>
                <dd className="sm:col-span-2 font-mono text-slate-900 dark:text-slate-100 break-all">
                  {field.isLink ? (
                    <a
                      href={field.value}
                      target="_blank"
                      rel="noreferrer"
                      className="text-teal-600 dark:text-teal-400 hover:underline inline-flex items-center gap-1"
                    >
                      <span>{field.value}</span>
                      <ExternalLink className="w-3 h-3 shrink-0" />
                    </a>
                  ) : (
                    field.value
                  )}
                </dd>
              </React.Fragment>
            ))}
          </dl>
        </div>

        {/* Job Ops Payload pre block */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-teal-500" />
                <h2 className="text-base font-bold text-slate-900 dark:text-white">Job Ops payload</h2>
              </div>
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-mono transition-colors"
                title="Copy JSON Payload"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-teal-500" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
              </button>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              Complete normalized static mock payload. No credentials, cookies, raw upstream content, or endpoint data is present.
            </p>
          </div>

          <div className="mt-3">
            <pre className="code payload text-xs font-mono p-4 rounded-lg bg-slate-950 text-teal-300 dark:text-teal-300 border border-slate-800 overflow-auto max-h-[500px] whitespace-pre-wrap break-all leading-relaxed shadow-inner">
              {payloadString}
            </pre>
          </div>
        </div>
      </section>
    </div>
  );
};
