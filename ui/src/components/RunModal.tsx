import React, { useState, useEffect } from 'react';
import { X, Play, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface RunModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const RunModal: React.FC<RunModalProps> = ({ isOpen, onClose }) => {
  const [triggerType, setTriggerType] = useState<'all' | 'specific'>('all');
  const [boardId, setBoardId] = useState<string>('');
  const [boards, setBoards] = useState<any[]>([]);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [success, setSuccess] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      fetch('/api/v1/boards')
        .then((res) => (res.ok ? res.json() : []))
        .then((data: any[]) => {
          setBoards(data);
          if (data.length > 0) {
            setBoardId(data[0].board_id);
          }
        })
        .catch((e) => console.error(e));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const payload = triggerType === 'specific' ? { board_id: boardId } : {};
      const res = await fetch('/api/v1/runs/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error('Server error');
      }

      setSubmitting(false);
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1200);
    } catch (err) {
      console.error('Trigger run error:', err);
      setSubmitting(false);
      alert('Failed to trigger run.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Play className="w-5 h-5 text-teal-600 dark:text-teal-400" />
            <h3 className="font-semibold text-slate-900 dark:text-white">Trigger Pipeline Run</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {success ? (
          <div className="p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-teal-500 mx-auto mb-3" />
            <h4 className="font-semibold text-slate-900 dark:text-white text-lg">Run Enqueued</h4>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Execution attempt enqueued in pipeline queue.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Scope Selection
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setTriggerType('all')}
                  className={'px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ' + (triggerType === 'all' ? 'border-teal-500 bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300' : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400')}
                >
                  All Active Boards
                </button>
                <button
                  type="button"
                  onClick={() => setTriggerType('specific')}
                  className={'px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ' + (triggerType === 'specific' ? 'border-teal-500 bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300' : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400')}
                >
                  Single Board
                </button>
              </div>
            </div>

            {triggerType === 'specific' && (
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Select Board
                </label>
                <select
                  value={boardId}
                  onChange={(e) => setBoardId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                >
                  {boards.map((b: any) => (
                    <option key={b.board_id} value={b.board_id}>
                      {b.name} ({b.family})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs text-amber-800 dark:text-amber-300 space-y-1">
                <div className="font-semibold">Local Boundary Assurance</div>
                <div>Playwright instances run exclusively against registered targets. Unrecognized URLs will be dropped.</div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 text-sm font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors disabled:opacity-50"
              >
                {submitting ? 'Dispatching...' : 'Confirm & Execute'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
