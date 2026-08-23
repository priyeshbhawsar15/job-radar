import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { ArrowLeft, Copy, Check, ExternalLink, Code2, AlertTriangle, RefreshCw, Send } from 'lucide-react';

export const JobDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<any | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [retrying, setRetrying] = useState<boolean>(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [retrySucceeded, setRetrySucceeded] = useState<boolean>(false);
  const [importing, setImporting] = useState<boolean>(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);

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
            ops: found.job_ops_status || 'untracked',
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
    skipTailoring: true,
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

  const handleRetryEnrichment = () => {
    if (!job || retrying) return;
    setRetrying(true);
    setRetryError(null);
    setRetrySucceeded(false);
    fetch(`/api/v1/jobs/${job.id}/retry-enrichment`, { method: 'POST' })
      .then(async (res) => {
        if (!res.ok) throw new Error(`Retry failed with status ${res.status}`);
        const updated = await res.json();
        setJob((prev: any) => ({
          ...prev,
          description: updated.description || prev.description,
          location: updated.location || prev.location,
          type: updated.employment_type || prev.type,
          department: updated.department || prev.department,
          salary_raw: updated.salary_raw || prev.salary_raw,
          detail_enrichment_status: updated.detail_enrichment_status,
          detail_enrichment_error_code: updated.detail_enrichment_error_code || null,
        }));
        if (updated.detail_enrichment_status === 'succeeded') {
          setRetrySucceeded(true);
        } else {
          setRetryError(updated.detail_enrichment_error_code || 'Enrichment retry failed');
        }
      })
      .catch((e) => setRetryError(e.message || 'Enrichment retry failed'))
      .finally(() => setRetrying(false));
  };

  const handlePushJobOps = () => {
    if (!job || importing) return;
    setImporting(true);
    setImportMessage(null);
    fetch(`/api/v1/jobs/${job.id}/push-jobops`, { method: 'POST' })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `Import failed with status ${res.status}`);
        setJob((prev: any) => ({
          ...prev,
          ops: data.status === 'imported' ? 'accepted' : data.status,
        }));
        setImportMessage(data.detail || 'Job imported to Job Ops successfully!');
      })
      .catch((e) => setImportMessage(e.message || 'Manual import to Job Ops failed.'))
      .finally(() => setImporting(false));
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
    { key: 'job_ops_status', label: 'Job Ops Status', value: job.ops },
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
            onClick={handlePushJobOps}
            disabled={importing}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Send className={`w-4 h-4 ${importing ? 'animate-spin' : ''}`} />
            <span>{importing ? 'Importing to Job Ops...' : 'Import to Job Ops'}</span>
          </button>

          {job.detail_enrichment_status === 'failed' && (
            <button
              onClick={handleRetryEnrichment}
              disabled={retrying}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-teal-300 dark:border-teal-700 bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 text-xs font-semibold hover:bg-teal-100 dark:hover:bg-teal-900/50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${retrying ? 'animate-spin' : ''}`} />
              <span>{retrying ? 'Retrying enrichment...' : 'Retry Enrichment'}</span>
            </button>
          )}

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

      {/* Manual Import Feedback Banner */}
      {importMessage && (
        <section className="p-4 rounded-xl bg-teal-50 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800/60 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-teal-900 dark:text-teal-300">
            <Check className="w-4 h-4 text-teal-500 shrink-0" />
            <span>{importMessage}</span>
          </div>
        </section>
      )}

      {/* Enrichment Failure Warning Banner */}
      {job.detail_enrichment_status === 'failed' && (
        <section className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-bold text-rose-700 dark:text-rose-400">Detail enrichment failed</p>
            <p className="text-xs text-rose-600 dark:text-rose-300 mt-0.5">
              Error code: <span className="font-mono">{job.detail_enrichment_error_code || 'unknown'}</span>. Description and detail fields may be incomplete.
            </p>
            {retryError && (
              <p className="text-xs text-rose-700 dark:text-rose-300 mt-1 font-mono">{retryError}</p>
            )}
          </div>
          <button
            onClick={handleRetryEnrichment}
            disabled={retrying}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors disabled:opacity-60 disabled:cursor-not-allowed shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${retrying ? 'animate-spin' : ''}`} />
            <span>{retrying ? 'Retrying enrichment...' : 'Retry Enrichment'}</span>
          </button>
        </section>
      )}

      {retrySucceeded && (
        <section className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 flex items-center gap-3">
          <Check className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <p className="text-sm font-bold text-emerald-700 dark:text-emerald-400">Detail enrichment succeeded</p>
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
