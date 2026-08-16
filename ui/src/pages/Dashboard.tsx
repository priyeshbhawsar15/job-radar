import React from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { PlaySquare, Layers, Briefcase, AlertCircle, ArrowUpRight, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';

interface DashboardProps {
  onRunClick: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onRunClick }) => {
  const stats = [
    { label: 'Active Boards', value: '12', icon: Layers, status: 'healthy', delta: '+2 this week' },
    { label: 'Pipeline Runs (24h)', value: '48', icon: PlaySquare, status: 'healthy', delta: '100% success rate' },
    { label: 'Normalized Jobs', value: '1,420', icon: Briefcase, status: 'active', delta: '34 fresh today' },
    { label: 'Pending Handoffs', value: '3', icon: AlertCircle, status: 'attention', delta: 'Outbox active' },
  ];

  const recentRuns = [
    { id: 'run-8f92a01', board: 'Stripe Engineering', family: 'Greenhouse', duration: '1.4s', status: 'completed', time: '10 mins ago', jobsFound: 14 },
    { id: 'run-7b41c09', board: 'Datadog Product', family: 'Lever', duration: '2.1s', status: 'completed', time: '45 mins ago', jobsFound: 28 },
    { id: 'run-6d12e88', board: 'Linear Core', family: 'Ashby', duration: '0.9s', status: 'completed', time: '2 hours ago', jobsFound: 6 },
    { id: 'run-5e01f34', board: 'Vercel Infrastructure', family: 'Workday', duration: '5.2s', status: 'attention', time: '5 hours ago', jobsFound: 0 },
  ];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">System Operations Overview</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time normalization monitoring, board health telemetry, and ingestion runs.
          </p>
        </div>
        <button
          onClick={onRunClick}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors shadow-xs"
        >
          <Activity className="w-4 h-4" />
          <span>Manual Pipeline Trigger</span>
        </button>
      </div>

      {/* Overview Stat Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <div
            key={idx}
            className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                {stat.label}
              </span>
              <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                <stat.icon className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="text-3xl font-bold text-slate-900 dark:text-white font-mono">{stat.value}</span>
              <StatusBadge status={stat.status} size="sm" />
            </div>
            <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{stat.delta}</div>
          </div>
        ))}
      </div>

      {/* Board Health & Recent Runs split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Runs Table */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Recent Pipeline Executions</h2>
            <Link
              to="/runs"
              className="inline-flex items-center gap-1 text-xs font-medium text-teal-600 dark:text-teal-400 hover:underline"
            >
              View all runs <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 px-3">Run ID</th>
                  <th className="py-2.5 px-3">Board Target</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Jobs Found</th>
                  <th className="py-2.5 px-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
                {recentRuns.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                    <td className="py-3 px-3 font-mono text-slate-600 dark:text-slate-400">{run.id}</td>
                    <td className="py-3 px-3 font-medium text-slate-900 dark:text-white">
                      {run.board}
                      <span className="block text-[10px] font-normal text-slate-400">{run.family}</span>
                    </td>
                    <td className="py-3 px-3 text-slate-500 font-mono">{run.duration}</td>
                    <td className="py-3 px-3 font-semibold text-slate-700 dark:text-slate-300 font-mono">{run.jobsFound}</td>
                    <td className="py-3 px-3 text-right">
                      <StatusBadge status={run.status} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Board Status & Revision Health */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Board Revision Health</h2>

          <div className="space-y-3">
            <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-slate-900 dark:text-white text-xs">Stripe Engineering</span>
                <StatusBadge status="healthy" size="sm" />
              </div>
              <div className="text-[11px] text-slate-500 font-mono">Rev 4 • 0 Consecutive Failures</div>
            </div>

            <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-slate-900 dark:text-white text-xs">Datadog Product</span>
                <StatusBadge status="healthy" size="sm" />
              </div>
              <div className="text-[11px] text-slate-500 font-mono">Rev 2 • 0 Consecutive Failures</div>
            </div>

            <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-slate-900 dark:text-white text-xs">Vercel Infra</span>
                <StatusBadge status="attention" size="sm" label="1 Failure" />
              </div>
              <div className="text-[11px] text-slate-500 font-mono">Rev 1 • 1 Consecutive Failure (Auto-Hold @ 3)</div>
            </div>
          </div>

          <Link
            to="/boards"
            className="block text-center py-2 text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
          >
            Manage Board Registry →
          </Link>
        </div>
      </div>
    </div>
  );
};
