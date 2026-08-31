import React, { useState, useEffect } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { PlaySquare, Layers, Briefcase, AlertCircle, ArrowUpRight, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ActivePipelineStatus } from '../components/ActivePipelineStatus';
import { useActivePipeline } from '../hooks/useActivePipeline';

interface DashboardProps {
  onRunClick: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onRunClick }) => {
  const [boards, setBoards] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const { activePipeline, error: activePipelineError } = useActivePipeline();

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/boards').then((res) => (res.ok ? res.json() : [])),
      fetch('/api/v1/runs').then((res) => (res.ok ? res.json() : [])),
      fetch('/api/v1/jobs').then((res) => (res.ok ? res.json() : []))
    ])
      .then(([bData, rData, jData]) => {
        setBoards(bData);
        setRuns(rData);
        setJobs(jData);
      })
      .catch((e) => console.error(e));
  }, []);

  const activeBoardsCount = boards.filter((b) => b.status !== 'retired').length;
  const totalRunsCount = runs.length;
  const totalJobsCount = jobs.length;
  const pendingHandoffsCount = jobs.filter((j) => j.job_ops_status === 'held').length;

  const stats = [
    { label: 'Active Boards', value: activeBoardsCount.toString(), icon: Layers, status: 'healthy', delta: boards.length + ' registered' },
    { label: 'Pipeline Runs', value: totalRunsCount.toString(), icon: PlaySquare, status: 'healthy', delta: 'Retained execution runs' },
    { label: 'Normalized Jobs', value: totalJobsCount.toString(), icon: Briefcase, status: 'active', delta: 'Canonical candidate records' },
    { label: 'Pending Handoffs', value: pendingHandoffsCount.toString(), icon: AlertCircle, status: pendingHandoffsCount > 0 ? 'attention' : 'healthy', delta: 'Outbox queue status' },
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

      <ActivePipelineStatus pipeline={activePipeline} error={activePipelineError} />

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
            {runs.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    <th className="py-2.5 px-3">Run ID</th>
                    <th className="py-2.5 px-3">Board Target</th>
                    <th className="py-2.5 px-3">Stage</th>
                    <th className="py-2.5 px-3">Extracted</th>
                    <th className="py-2.5 px-3 text-right">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
                  {runs.slice(0, 5).map((run) => (
                    <tr key={run.run_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="py-3 px-3 font-mono text-slate-600 dark:text-slate-400">{run.run_id.slice(0, 8)}...</td>
                      <td className="py-3 px-3 font-medium text-slate-900 dark:text-white">
                        {run.board_name}
                        <span className="block text-[10px] font-normal text-slate-400">{run.family}</span>
                      </td>
                      <td className="py-3 px-3 text-slate-500 font-mono">{run.stage}</td>
                      <td className="py-3 px-3 font-semibold text-slate-700 dark:text-slate-300 font-mono">{run.extracted_count}</td>
                      <td className="py-3 px-3 text-right">
                        <StatusBadge status={run.outcome} size="sm" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                No pipeline runs recorded yet. Click "Manual Pipeline Trigger" to execute.
              </div>
            )}
          </div>
        </div>

        {/* Board Status & Revision Health */}
        <div className="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Board Revision Health</h2>

          <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
            {boards.slice(0, 6).map((b) => (
              <div key={b.board_id} className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-slate-900 dark:text-white text-xs">{b.name}</span>
                  <StatusBadge status={b.status === 'active' ? 'healthy' : b.status} size="sm" />
                </div>
                <div className="text-[11px] text-slate-500 font-mono">{b.family} adapter • {(b.consecutive_parser_failures || 0)} Failures</div>
              </div>
            ))}
          </div>

          <Link
            to="/boards"
            className="block text-center py-2 text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
          >
            Manage Board Registry ({boards.length} Boards) →
          </Link>
        </div>
      </div>
    </div>
  );
};
