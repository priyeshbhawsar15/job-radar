import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Save, ArrowLeft, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const BoardConfig: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const isNew = !id || id === 'new';

  const [name, setName] = useState(isNew ? '' : 'Stripe Engineering');
  const [family, setFamily] = useState(isNew ? 'greenhouse' : 'greenhouse');
  const [targetUrl, setTargetUrl] = useState(isNew ? '' : 'https://boards.greenhouse.io/stripe');
  const [cron, setCron] = useState(isNew ? '0 */6 * * *' : '0 */6 * * *');
  const [selectorConfig, setSelectorConfig] = useState(
    JSON.stringify(
      {
        container: '.job-post',
        title: 'h3.title',
        location: '.location',
        department: '.department',
        link: 'a.job-link'
      },
      null,
      2
    )
  );

  const [submitted, setSubmitted] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      navigate('/boards');
    }, 1000);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/boards')}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 dark:hover:text-slate-200"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Registry</span>
        </button>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-teal-500" />
          <span className="text-xs font-mono text-slate-500">Board Revision Safety Guard</span>
        </div>
      </div>

      <div className="p-6 sm:p-8 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">
            {isNew ? 'Create New Board Configuration' : `Edit Board Configuration: ${id}`}
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Submitting creates a new immutable revision entry in the database.
          </p>
        </div>

        {submitted ? (
          <div className="py-12 text-center space-y-3">
            <CheckCircle2 className="w-12 h-12 text-teal-500 mx-auto" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Revision Saved Successfully</h3>
            <p className="text-xs text-slate-500 font-mono">Redirecting back to Board Registry...</p>
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Board Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Stripe Engineering"
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Adapter Family
                </label>
                <select
                  value={family}
                  onChange={(e) => setFamily(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                >
                  <option value="greenhouse">Greenhouse</option>
                  <option value="lever">Lever</option>
                  <option value="ashby">Ashby</option>
                  <option value="workday">Workday</option>
                  <option value="custom">Custom Selector JSON</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                Target URL
              </label>
              <input
                type="url"
                required
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder="https://boards.greenhouse.io/company"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-mono focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                Schedule (Cron Expression)
              </label>
              <input
                type="text"
                required
                value={cron}
                onChange={(e) => setCron(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-mono focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                DOM Extraction Rules (JSON)
              </label>
              <textarea
                rows={6}
                value={selectorConfig}
                onChange={(e) => setSelectorConfig(e.target.value)}
                className="w-full p-3.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-900 text-teal-400 font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => navigate('/boards')}
                className="px-4 py-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 text-sm font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors shadow-xs"
              >
                <Save className="w-4 h-4" />
                <span>Save Board Revision</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
