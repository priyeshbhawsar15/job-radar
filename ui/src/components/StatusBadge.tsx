import React from 'react';

export type StatusType =
  | 'healthy'
  | 'success'
  | 'completed'
  | 'active'
  | 'running'
  | 'attention'
  | 'held'
  | 'draft'
  | 'warning'
  | 'failed'
  | 'error'
  | 'rejected'
  | 'neutral';

interface StatusBadgeProps {
  status: StatusType | string;
  label?: string;
  size?: 'sm' | 'md';
  title?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, size = 'md', title }) => {
  const normalized = status.toLowerCase();

  let styles = "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700";
  let dotColor = "bg-slate-400";

  if (['healthy', 'success', 'completed', 'active', 'accepted', 'imported'].includes(normalized)) {
    styles = "bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-400 border-teal-200 dark:border-teal-800/60";
    dotColor = "bg-teal-500 dark:bg-teal-400";
  } else if (['attention', 'held', 'draft', 'warning', 'queued', 'dispatching', 'uncertain', 'untracked'].includes(normalized)) {
    styles = "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border-amber-200 dark:border-amber-800/60";
    dotColor = "bg-amber-500 dark:bg-amber-400";
  } else if (['failed', 'error', 'rejected'].includes(normalized)) {
    styles = "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 border-rose-200 dark:border-rose-800/60";
    dotColor = "bg-rose-500 dark:bg-rose-400";
  } else if (['running'].includes(normalized)) {
    styles = "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border-blue-200 dark:border-blue-800/60";
    dotColor = "bg-blue-500 dark:bg-blue-400 animate-pulse";
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  let displayLabel = label || status.charAt(0).toUpperCase() + status.slice(1);
  if (normalized === 'accepted' && !label) {
    displayLabel = 'Imported';
  }

  return (
    <span title={title} className={`inline-flex items-center gap-1.5 rounded-full border ${sizeClasses} ${styles}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      {displayLabel}
    </span>
  );
};
