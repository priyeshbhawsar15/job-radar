import { useState, useEffect } from 'react';

export interface SSEEvent {
  event_type: string;
  timestamp: string;
  system_status: string;
  active_runs_count: number;
}

export function useSSE(url: string = '/api/v1/stream') {
  const [data, setData] = useState<SSEEvent | null>(null);
  const [connected, setConnected] = useState<boolean>(false);

  useEffect(() => {
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(url);

      eventSource.onopen = () => {
        setConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
        } catch (e) {
          console.error("Failed to parse SSE payload", e);
        }
      };

      eventSource.onerror = () => {
        setConnected(false);
        eventSource?.close();
      };
    } catch (e) {
      setConnected(false);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [url]);

  return { data, connected };
}
