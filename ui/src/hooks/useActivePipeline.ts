import { useCallback, useEffect, useRef, useState } from 'react';

export const PIPELINE_TRIGGERED_EVENT = 'job-radar:pipeline-triggered';
const ACTIVE_RUN_POLL_INTERVAL_MS = 5_000;

export interface ActivePipeline {
  pipeline_id: string;
  status: 'running';
  started_at: string;
  total_boards: number;
  completed_boards: number;
  remaining_boards: number;
  progress_percentage: number;
  current_board_name: string | null;
  current_stage: string | null;
}

export function useActivePipeline() {
  const [activePipeline, setActivePipeline] = useState<ActivePipeline | null>(null);
  const [error, setError] = useState(false);
  const latestRequestId = useRef(0);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const requestId = ++latestRequestId.current;
    try {
      const response = await fetch('/api/v1/runs/active', { signal });
      if (!response.ok) {
        throw new Error(`Active pipeline request failed with ${response.status}`);
      }
      const data: ActivePipeline | null = await response.json();
      if (requestId !== latestRequestId.current) return;
      setActivePipeline(data);
      setError(false);
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === 'AbortError') {
        return;
      }
      if (requestId !== latestRequestId.current) return;
      console.error('Failed to load active pipeline:', requestError);
      setError(true);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const refreshNow = () => void refresh(controller.signal);

    refreshNow();
    const intervalId = window.setInterval(refreshNow, ACTIVE_RUN_POLL_INTERVAL_MS);
    window.addEventListener(PIPELINE_TRIGGERED_EVENT, refreshNow);

    return () => {
      latestRequestId.current += 1;
      controller.abort();
      window.clearInterval(intervalId);
      window.removeEventListener(PIPELINE_TRIGGERED_EVENT, refreshNow);
    };
  }, [refresh]);

  return { activePipeline, error, refresh };
}
