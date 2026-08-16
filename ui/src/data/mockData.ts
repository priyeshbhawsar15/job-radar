export interface BoardItem {
  id: string;
  name: string;
  adapter: string;
  url: string;
  state: 'reviewed' | 'paused' | 'draft' | 'active' | string;
  rev: string;
  runs: number;
  success: number;
  missing: string[];
  next: string;
}

export interface JobItem {
  id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  posted: string;
  type: string;
  department: string;
  board: string;
  source: string;
  revision: string;
  discovered: string;
  normalization: string;
  eligibility: string;
  ops: 'accepted' | 'held' | 'rejected' | string;
  receipt: string;
}

export interface BoardRunTuple {
  boardId: string;
  state: 'completed' | 'partial' | 'failed' | 'held' | string;
  outcome: string;
  boardRunId: string;
}

export interface RunItem {
  id: string;
  time: string;
  state: 'completed' | 'partial' | 'failed' | string;
  duration: string;
  boards: number;
  completed: number;
  extracted: number;
  accepted: number;
  held: number;
  boardRuns: BoardRunTuple[];
  jobs: string[];
}

export const MOCK_BOARDS: BoardItem[] = [];
export const MOCK_JOBS: JobItem[] = [];
export const MOCK_RUNS: RunItem[] = [];

export function getBoard(id: string): BoardItem | undefined {
  return MOCK_BOARDS.find((b) => b.id.toLowerCase() === id.toLowerCase());
}

export function getJob(id: string): JobItem | undefined {
  return MOCK_JOBS.find((j) => j.id.toLowerCase() === id.toLowerCase());
}

export function getRun(id: string): RunItem | undefined {
  return MOCK_RUNS.find((r) => r.id.toLowerCase() === id.toLowerCase());
}

export function getBoardRun(id: string): { entry: BoardRunTuple; run: RunItem; board: BoardItem } | undefined {
  return undefined;
}
