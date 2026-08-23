import React, { useState, useEffect } from 'react';
import { Save, CheckCircle, Cog, Wifi, Send, Cpu } from 'lucide-react';

interface AppSettings {
  scheduler_enabled: boolean;
  scheduler_interval_hours: number | null;
  selected_board_ids: string[];
  handoff_enabled: boolean;
  jobops_endpoint: string | null;
  jobops_username: string | null;
  jobops_password: string | null;
  discord_webhook_enabled: boolean;
  discord_webhook_url: string;
  global_browser_concurrency: number;
}

interface BoardOption {
  board_id: string;
  name: string;
}

type ConnectionStatus = 'idle' | 'testing' | 'connected' | 'unauthorized' | 'unreachable';
type WebhookTestStatus = 'idle' | 'testing' | 'success' | 'failure';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [boards, setBoards] = useState<BoardOption[]>([]);
  const [schedulerEnabled, setSchedulerEnabled] = useState<boolean>(false);
  const [intervalHours, setIntervalHours] = useState<string>('disabled');
  const [selectedBoardIds, setSelectedBoardIds] = useState<string[]>([]);
  const [handoffEnabled, setHandoffEnabled] = useState<boolean>(false);
  const [jobopsEndpoint, setJobopsEndpoint] = useState<string>('');
  const [jobopsUsername, setJobopsUsername] = useState<string>('');
  const [jobopsPassword, setJobopsPassword] = useState<string>('');
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('idle');
  const [discordWebhookEnabled, setDiscordWebhookEnabled] = useState<boolean>(false);
  const [discordWebhookUrl, setDiscordWebhookUrl] = useState<string>('');
  const [globalBrowserConcurrency, setGlobalBrowserConcurrency] = useState<number>(10);
  const [webhookTestStatus, setWebhookTestStatus] = useState<WebhookTestStatus>('idle');
  const [webhookTestMessage, setWebhookTestMessage] = useState<string>('');
  const [savedMsg, setSavedMsg] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/settings').then((res) => (res.ok ? res.json() : null)),
      fetch('/api/v1/boards').then((res) => (res.ok ? res.json() : [])),
    ])
      .then(([settingsData, boardsData]: [AppSettings | null, any[]]) => {
        if (settingsData) {
          setSettings(settingsData);
          setSchedulerEnabled(settingsData.scheduler_enabled);
          setIntervalHours(
            settingsData.scheduler_interval_hours ? String(settingsData.scheduler_interval_hours) : 'disabled'
          );
          setSelectedBoardIds(settingsData.selected_board_ids || []);
          setHandoffEnabled(settingsData.handoff_enabled);
          setJobopsEndpoint(settingsData.jobops_endpoint || '');
          setJobopsUsername(settingsData.jobops_username || '');
          setJobopsPassword(settingsData.jobops_password || '');
          setDiscordWebhookEnabled(settingsData.discord_webhook_enabled || false);
          setDiscordWebhookUrl(settingsData.discord_webhook_url || '');
          setGlobalBrowserConcurrency(settingsData.global_browser_concurrency || 10);
        }
        setBoards((boardsData || []).map((b) => ({ board_id: b.board_id, name: b.name })));
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const toggleBoard = (boardId: string) => {
    setSelectedBoardIds((prev) =>
      prev.includes(boardId) ? prev.filter((id) => id !== boardId) : [...prev, boardId]
    );
  };

  const selectAllBoards = () => setSelectedBoardIds(boards.map((b) => b.board_id));
  const deselectAllBoards = () => setSelectedBoardIds([]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    fetch('/api/v1/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scheduler_enabled: schedulerEnabled,
        scheduler_interval_hours: intervalHours === 'disabled' ? null : Number(intervalHours),
        selected_board_ids: selectedBoardIds,
        handoff_enabled: handoffEnabled,
        jobops_endpoint: jobopsEndpoint || null,
        jobops_username: jobopsUsername || null,
        jobops_password: jobopsPassword || null,
        discord_webhook_enabled: discordWebhookEnabled,
        discord_webhook_url: discordWebhookUrl,
        global_browser_concurrency: globalBrowserConcurrency,
      }),
    })
      .then((res) => res.json())
      .then((data: AppSettings) => {
        setSettings(data);
        setSavedMsg(true);
        setTimeout(() => setSavedMsg(false), 3000);
      })
      .catch((err) => alert('Error saving settings: ' + err));
  };

  const handleTestConnection = () => {
    setConnectionStatus('testing');
    fetch('/api/v1/settings/test-jobops', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jobops_endpoint: jobopsEndpoint,
        jobops_username: jobopsUsername,
        jobops_password: jobopsPassword,
      }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          setConnectionStatus('unreachable');
          return;
        }
        setConnectionStatus(data.status as ConnectionStatus);
      })
      .catch(() => setConnectionStatus('unreachable'));
  };

  const handleTestWebhook = () => {
    setWebhookTestStatus('testing');
    setWebhookTestMessage('');
    fetch('/api/v1/settings/test-discord-webhook', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ discord_webhook_url: discordWebhookUrl }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok || !data.ok) {
          setWebhookTestStatus('failure');
          setWebhookTestMessage(data.detail || data.message || 'Failed to send test notification.');
          return;
        }
        setWebhookTestStatus('success');
        setWebhookTestMessage(data.message);
      })
      .catch((err) => {
        setWebhookTestStatus('failure');
        setWebhookTestMessage(String(err));
      });
  };

  if (loading || !settings) {
    return <div className="p-8 text-center text-slate-400 font-mono">Loading settings...</div>;
  }

  const statusBadge: Record<Exclude<ConnectionStatus, 'idle' | 'testing'>, { label: string; className: string }> = {
    connected: { label: 'Connected', className: 'bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/30' },
    unauthorized: { label: 'Unauthorized', className: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30' },
    unreachable: { label: 'Unreachable', className: 'bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/30' },
  };

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] uppercase tracking-widest font-extrabold text-teal-600 dark:text-teal-400 mb-1">
          Operator workspace · Settings
        </p>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
          <Cog className="w-6 h-6 text-teal-500" />
          <span>Settings</span>
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
          Configure the automated pipeline scheduler, browser concurrency controls, and Job Ops integration.
        </p>
      </header>

      {savedMsg && (
        <div className="p-3.5 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-900 dark:text-teal-300 text-xs flex items-center gap-2 font-bold">
          <CheckCircle className="w-4 h-4 text-teal-500 shrink-0" />
          <span>Settings saved successfully.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Browser Concurrency Controls</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Set the global maximum concurrent Chromium rendering instances across all active pipelines.
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="globalBrowserConcurrency" className="block text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-teal-500" />
                <span>Global Browser Concurrency Limit</span>
              </label>
              <span className="text-xs font-extrabold text-teal-600 dark:text-teal-400 font-mono">
                {globalBrowserConcurrency} active instances
              </span>
            </div>
            <input
              id="globalBrowserConcurrency"
              type="number"
              min="1"
              max="50"
              value={globalBrowserConcurrency}
              onChange={(e) => setGlobalBrowserConcurrency(Math.max(1, Number(e.target.value)))}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Default is 10. Per-board default is 5 unless overridden in board configuration.
            </p>
          </div>
        </section>

        <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Automated Pipeline Scheduler</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Control how often the pipeline runs automatically and which boards are included.
            </p>
          </div>

          <div className="flex items-center justify-between p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Enable scheduler</span>
            <button
              type="button"
              role="switch"
              aria-checked={schedulerEnabled}
              onClick={() => setSchedulerEnabled((prev) => !prev)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                schedulerEnabled ? 'bg-teal-600' : 'bg-slate-300 dark:bg-slate-700'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  schedulerEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="space-y-1">
            <label htmlFor="intervalHours" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Run frequency
            </label>
            <select
              id="intervalHours"
              value={intervalHours}
              onChange={(e) => setIntervalHours(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              <option value="disabled">Disabled</option>
              <option value="6">Every 6 hours</option>
              <option value="12">Every 12 hours</option>
              <option value="24">Every 24 hours</option>
            </select>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                Active boards ({selectedBoardIds.length}/{boards.length})
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={selectAllBoards}
                  className="text-[11px] font-semibold text-teal-600 dark:text-teal-400 hover:underline"
                >
                  Select all
                </button>
                <button
                  type="button"
                  onClick={deselectAllBoards}
                  className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 hover:underline"
                >
                  Deselect all
                </button>
              </div>
            </div>
            <div className="max-h-64 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-1.5 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
              {boards.length === 0 ? (
                <p className="text-xs text-slate-400 col-span-full">No boards found.</p>
              ) : (
                boards.map((b) => (
                  <label
                    key={b.board_id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-md text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedBoardIds.includes(b.board_id)}
                      onChange={() => toggleBoard(b.board_id)}
                      className="rounded border-slate-300 dark:border-slate-700 text-teal-600 focus:ring-teal-500"
                    />
                    <span className="truncate">{b.name}</span>
                  </label>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Job Ops Integration &amp; Hand-off</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Configure the hand-off process to the Job Ops manual review system.
            </p>
          </div>

          <div className="flex items-center justify-between p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Enable hand-off</span>
            <button
              type="button"
              role="switch"
              aria-checked={handoffEnabled}
              onClick={() => setHandoffEnabled((prev) => !prev)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                handoffEnabled ? 'bg-teal-600' : 'bg-slate-300 dark:bg-slate-700'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  handoffEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="space-y-1">
            <label htmlFor="jobopsEndpoint" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Job Ops endpoint
            </label>
            <input
              id="jobopsEndpoint"
              type="text"
              value={jobopsEndpoint}
              onChange={(e) => setJobopsEndpoint(e.target.value)}
              placeholder="http://192.168.2.201:3005"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label htmlFor="jobopsUsername" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                Job Ops username
              </label>
              <input
                id="jobopsUsername"
                type="text"
                value={jobopsUsername}
                onChange={(e) => setJobopsUsername(e.target.value)}
                placeholder="priyesh"
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="jobopsPassword" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                Job Ops password
              </label>
              <input
                id="jobopsPassword"
                type="password"
                value={jobopsPassword}
                onChange={(e) => setJobopsPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={connectionStatus === 'testing'}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
            >
              <Wifi className="w-4 h-4" />
              <span>{connectionStatus === 'testing' ? 'Testing...' : 'Test Connection'}</span>
            </button>
            {connectionStatus !== 'idle' && connectionStatus !== 'testing' && (
              <span
                className={`px-2.5 py-1 rounded-full text-[11px] font-bold border ${statusBadge[connectionStatus].className}`}
              >
                {statusBadge[connectionStatus].label}
              </span>
            )}
          </div>
        </section>

        <section className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Discord Webhook Integration</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Send an automated summary to a Discord channel whenever a pipeline run completes.
            </p>
          </div>

          <div className="flex items-center justify-between p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Enable Discord notifications</span>
            <button
              type="button"
              role="switch"
              aria-checked={discordWebhookEnabled}
              onClick={() => setDiscordWebhookEnabled((prev) => !prev)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                discordWebhookEnabled ? 'bg-teal-600' : 'bg-slate-300 dark:bg-slate-700'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  discordWebhookEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="space-y-1">
            <label htmlFor="discordWebhookUrl" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Discord webhook URL
            </label>
            <input
              id="discordWebhookUrl"
              type="text"
              value={discordWebhookUrl}
              onChange={(e) => setDiscordWebhookUrl(e.target.value)}
              placeholder="https://discord.com/api/webhooks/..."
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleTestWebhook}
              disabled={webhookTestStatus === 'testing' || !discordWebhookUrl}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>{webhookTestStatus === 'testing' ? 'Testing...' : 'Test Webhook'}</span>
            </button>
            {webhookTestStatus === 'success' && (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-bold border bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/30">
                Sent
              </span>
            )}
            {webhookTestStatus === 'failure' && (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-bold border bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/30">
                Failed
              </span>
            )}
          </div>
          {webhookTestMessage && (
            <p className="text-xs text-slate-500 dark:text-slate-400">{webhookTestMessage}</p>
          )}
        </section>

        <button
          type="submit"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold shadow-xs transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>Save Settings</span>
        </button>
      </form>
    </div>
  );
};
