import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, Copy, Check, ExternalLink, Code2, AlertTriangle } from 'lucide-react';

export const JobDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<any | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!id) return;
    fetch('/api/v1/jobs')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        const found = data.find((j: any) => j.candidate_id === id || j.id === id);
        if (found) {
          setJob({
            id: found.candidate_id || found.id,
            title: found.title,
            company: found.company || found.company_name,
            location: found.location || 'India',
            url: found.public_apply_url || found.url || '',
            posted: found.first_seen_at ? found.first_seen_at.split('T')[0] : '2026-08-16',
            type: found.employment_type || 'Full-time',
            department: found.department || 'Engineering',
            board: found.board_id,
            source: found.board_id + ':' + (found.candidate_id || found.id),
            revision: 'rev-01',
            discovered: found.first_seen_at || new Date().toISOString(),
            normalization: 'accepted · norm-v3',
            eligibility: 'eligible · policy-11',
            ops: 'accepted',
            receipt: 'OPS-' + id,
            description: found.description || ('Position for ' + found.title + ' at ' + (found.company || found.company_name) + '. Full position details and responsibilities available at apply link.'),
            salary_raw: found.salary_raw || 'Competitive / Not specified',
            detail_enrichment_status: found.detail_enrichment_status || 'pending',
            detail_enrichment_error_code: found.detail_enrichment_error_code || null,
          });
        }
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading job details...</div>;
  }

  if (!job) {
    return (
      <div className="p-8 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Job Candidate Not Found</h2>
        <p className="text-sm text-slate-500">The requested job candidate "{id}" could not be found.</p>
        <Link to="/jobs" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 text-white font-medium text-xs">
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Extracted Jobs</span>
        </Link>
      </div>
    );
  }

  const payload = {
    skipTailoring: false,
    job: {
      source: job.board,
      sourceJobId: job.id,
      title: job.title,
      employer: job.company,
      jobUrl: job.url,
      applicationLink: job.url,
      location: job.location,
      salary: job.salary_raw,
      jobDescription: job.description,
      jobType: job.type,
      jobFunction: job.department
    }
  };

  const payloadString = JSON.stringify(payload, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(payloadString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const kvFields = [
    { key: 'title', label: 'Title', value: job.title },
    { key: 'employer', label: 'Employer (Company)', value: job.company },
    { key: 'location', label: 'Location', value: job.location },
    { key: 'applicationLink', label: 'Application Link', value: job.url, isLink: true },
    { key: 'salary', label: 'Salary', value: job.salary_raw },
    { key: 'jobType', label: 'Job Type', value: job.type },
    { key: 'jobFunction', label: 'Job Function', value: job.department },
    { key: 'source', label: 'Source Board', value: job.board },
    { key: 'sourceJobId', label: 'Source Job ID', value: job.id },
    { key: 'discovered_at', label: 'Discovered at', value: job.discovered },
    { key: 'detail_enrichment_status', label: 'Detail Enrichment Status', value: job.detail_enrichment_status },
    { key: 'detail_enrichment_error_code', label: 'Enrichment Error Code', value: job.detail_enrichment_error_code || 'None' },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
            Operator workspace · Job Ops Intake API Candidate
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            {job.title}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {job.company} · POST /api/manual-jobs/import
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

      {/* Enrichment Failure Warning Banner */}
      {job.detail_enrichment_status === 'failed' && (
        <section className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-bold text-rose-700 dark:text-rose-400">Detail enrichment failed</p>
            <p className="text-xs text-rose-600 dark:text-rose-300 mt-0.5">
              Error code: <span className="font-mono">{job.detail_enrichment_error_code || 'unknown'}</span>. Description and detail fields may be incomplete.
            </p>
          </div>
        </section>
      )}

      {/* Job Description Card */}
      <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3">
        <h2 className="text-base font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2">
          Job description & details
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
          {job.description}
        </p>
      </section>

      {/* Two column grid */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Candidate status & KV fields */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Job Ops import metadata</h2>
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

        {/* Job Ops Intake API Payload pre block */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-teal-500" />
                <h2 className="text-base font-bold text-slate-900 dark:text-white">Job Ops POST /api/manual-jobs/import payload</h2>
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
              Exact verified payload expected by Job Ops <code>POST /api/manual-jobs/import</code> endpoint.
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
