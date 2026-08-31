import React from 'react';
import { Activity, AlertCircle } from 'lucide-react';
import type { ActivePipeline } from '../hooks/useActivePipeline';

interface ActivePipelineStatusProps {
  pipeline: ActivePipeline | null;
  error: boolean;
}

export const ActivePipelineStatus: React.FC<ActivePipelineStatusProps> = ({ pipeline, error }) => {
  if (!pipeline) {
    return error ? (
      <div
        role="status"
        className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-300"
      >
        <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>Pipeline activity is unavailable. Retrying automatically.</span>
      </div>
    ) : null;
  }

  const progress = Math.min(Math.max(pipeline.progress_percentage, 0), 100);
  const currentContext = [pipeline.current_board_name, pipeline.current_stage]
    .filter(Boolean)
    .join(' · ');

  return (
    <section
      aria-labelledby="active-pipeline-title"
      aria-live="polite"
      className="rounded-xl border border-teal-200 bg-white p-5 shadow-xs dark:border-teal-900 dark:bg-slate-900 sm:p-6"
    >
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="mt-0.5 rounded-lg bg-teal-50 p-2 text-teal-700 dark:bg-teal-950 dark:text-teal-300">
            <Activity className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 id="active-pipeline-title" className="text-sm font-semibold text-slate-900 dark:text-white">
                Full pipeline in progress
              </h2>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-2.5 py-1 text-[11px] font-semibold text-teal-700 dark:bg-teal-950 dark:text-teal-300">
                <span className="h-1.5 w-1.5 rounded-full bg-teal-500" aria-hidden="true" />
                Running
              </span>
            </div>
            <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">
              {currentContext || 'Preparing the next board'}
            </p>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-x-8 gap-y-2 sm:flex sm:items-center">
          <div>
            <dt className="text-[11px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">Completed</dt>
            <dd className="mt-0.5 font-mono text-lg font-semibold text-slate-900 dark:text-white">
              {pipeline.completed_boards} / {pipeline.total_boards}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">Remaining</dt>
            <dd className="mt-0.5 font-mono text-lg font-semibold text-slate-900 dark:text-white">
              {pipeline.remaining_boards}
            </dd>
          </div>
        </dl>
      </div>

      <div className="mt-5">
        <div
          role="progressbar"
          aria-label="Full pipeline board progress"
          aria-valuemin={0}
          aria-valuemax={pipeline.total_boards}
          aria-valuenow={pipeline.completed_boards}
          aria-valuetext={`${pipeline.completed_boards} of ${pipeline.total_boards} boards completed; ${pipeline.remaining_boards} remaining`}
          className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"
        >
          <div
            className="h-full rounded-full bg-teal-600 transition-[width] duration-500 ease-out dark:bg-teal-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="mt-2 flex items-center justify-between gap-4 text-[11px] text-slate-500 dark:text-slate-400">
          <span className="truncate font-mono" title={pipeline.pipeline_id}>
            Run {pipeline.pipeline_id.slice(0, 8)}
          </span>
          <span className="shrink-0 font-mono">{progress}%</span>
        </div>
      </div>
    </section>
  );
};
