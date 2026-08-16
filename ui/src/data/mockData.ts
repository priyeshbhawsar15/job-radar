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

export const MOCK_BOARDS: BoardItem[] = [
  {
    id: 'oracle',
    name: 'Oracle',
    adapter: 'oracle',
    url: 'https://careers.oracle.com/jobs/',
    state: 'reviewed',
    rev: 'rev-19',
    runs: 18,
    success: 94,
    missing: [],
    next: '06:00 IST'
  },
  {
    id: 'gururo',
    name: 'Gururo',
    adapter: 'careerpage',
    url: 'https://www.gururo.com/careers',
    state: 'paused',
    rev: 'rev-04',
    runs: 6,
    success: 0,
    missing: ['listing readiness descriptor', 'reviewed detail route allowlist'],
    next: 'Paused for provider_failure'
  },
  {
    id: 'amazon',
    name: 'Amazon',
    adapter: 'amazon_jobs',
    url: 'https://www.amazon.jobs/en/',
    state: 'reviewed',
    rev: 'rev-12',
    runs: 18,
    success: 100,
    missing: [],
    next: '06:00 IST'
  },
  {
    id: 'celonis',
    name: 'Celonis',
    adapter: 'custom',
    url: 'https://www.celonis.com/careers/',
    state: 'draft',
    rev: 'rev-03',
    runs: 3,
    success: 67,
    missing: ['typed pagination cap', 'approved readiness descriptor'],
    next: 'Review required'
  },
  {
    id: 'board-coupa-01',
    name: 'Coupa Software',
    adapter: 'lever',
    url: 'https://api.lever.co/v0/postings/coupa?mode=json',
    state: 'reviewed',
    rev: 'rev-01',
    runs: 12,
    success: 100,
    missing: [],
    next: '06:00 IST'
  },
  {
    id: 'board-stripe-02',
    name: 'Stripe',
    adapter: 'greenhouse',
    url: 'https://boards-api.greenhouse.io/v1/boards/stripe/jobs',
    state: 'reviewed',
    rev: 'rev-02',
    runs: 15,
    success: 100,
    missing: [],
    next: '06:00 IST'
  },
  {
    id: 'board-linear-03',
    name: 'Linear',
    adapter: 'ashby',
    url: 'https://api.ashbyhq.com/posting-api/job-board/linear',
    state: 'reviewed',
    rev: 'rev-01',
    runs: 8,
    success: 100,
    missing: [],
    next: '12:00 IST'
  },
  {
    id: 'board-datadog-04',
    name: 'Datadog',
    adapter: 'lever',
    url: 'https://api.lever.co/v0/postings/datadog?mode=json',
    state: 'reviewed',
    rev: 'rev-05',
    runs: 14,
    success: 92,
    missing: [],
    next: '06:00 IST'
  }
];

export const MOCK_JOBS: JobItem[] = [
  {
    id: 'job-oracle-48129',
    title: 'Senior Software Engineer',
    company: 'Oracle',
    location: 'Bengaluru, India',
    url: 'https://careers.oracle.com/jobs/#en/sites/jobsearch/job/48129',
    posted: '2026-08-20',
    type: 'Full-time',
    department: 'Cloud Infrastructure',
    board: 'oracle',
    source: 'oracle:48129',
    revision: 'rev-19',
    discovered: '2026-08-20T18:04:12+05:30',
    normalization: 'accepted · norm-v3',
    eligibility: 'eligible · policy-11',
    ops: 'accepted',
    receipt: 'OPS-48129'
  },
  {
    id: 'job-walmart-48131',
    title: 'Backend Engineer II',
    company: 'Walmart',
    location: 'Chennai, India',
    url: 'https://careers.walmart.com/job/backend-engineer-ii',
    posted: '2026-08-20',
    type: 'Full-time',
    department: 'Engineering',
    board: 'walmart',
    source: 'workday:WMT-19381',
    revision: 'rev-08',
    discovered: '2026-08-20T18:05:07+05:30',
    normalization: 'accepted · norm-v3',
    eligibility: 'eligible · policy-11',
    ops: 'accepted',
    receipt: 'OPS-48131'
  },
  {
    id: 'job-celonis-001',
    title: 'Platform Engineer',
    company: 'Celonis',
    location: 'Bengaluru, India',
    url: 'https://www.celonis.com/careers/jobs/platform-engineer/',
    posted: '2026-08-20',
    type: 'Full-time',
    department: 'Platform',
    board: 'celonis',
    source: 'celonis:platform-001',
    revision: 'rev-03',
    discovered: '2026-08-20T18:06:16+05:30',
    normalization: 'accepted · norm-v3',
    eligibility: 'held · duplicate review',
    ops: 'held',
    receipt: 'No delivery intent created'
  }
];

export const MOCK_RUNS: RunItem[] = [
  {
    id: 'run-240820-1802',
    time: '20 Aug 2026 · 18:02 IST',
    state: 'partial',
    duration: '4m 12s',
    boards: 36,
    completed: 35,
    extracted: 28,
    accepted: 19,
    held: 4,
    boardRuns: [
      { boardId: 'oracle', state: 'completed', outcome: '9 extracted', boardRunId: 'br-oracle-1802' },
      { boardId: 'amazon', state: 'completed', outcome: '4 extracted', boardRunId: 'br-amazon-1802' },
      { boardId: 'gururo', state: 'partial', outcome: 'provider_failure', boardRunId: 'br-gururo-1802' },
      { boardId: 'celonis', state: 'held', outcome: 'draft configuration', boardRunId: 'br-celonis-1802' }
    ],
    jobs: ['job-oracle-48129', 'job-walmart-48131', 'job-celonis-001']
  },
  {
    id: 'run-240820-0601',
    time: '20 Aug 2026 · 06:01 IST',
    state: 'completed',
    duration: '3m 41s',
    boards: 36,
    completed: 36,
    extracted: 17,
    accepted: 15,
    held: 0,
    boardRuns: [
      { boardId: 'oracle', state: 'completed', outcome: '6 extracted', boardRunId: 'br-oracle-0601' },
      { boardId: 'amazon', state: 'completed', outcome: '4 extracted', boardRunId: 'br-amazon-0601' }
    ],
    jobs: ['job-oracle-48129']
  },
  {
    id: 'run-240819-1800',
    time: '19 Aug 2026 · 18:00 IST',
    state: 'failed',
    duration: '1m 08s',
    boards: 36,
    completed: 0,
    extracted: 0,
    accepted: 0,
    held: 0,
    boardRuns: [
      { boardId: 'oracle', state: 'failed', outcome: 'capacity_held', boardRunId: 'br-oracle-1900' }
    ],
    jobs: []
  }
];

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
  for (const r of MOCK_RUNS) {
    const entry = r.boardRuns.find((br) => br.boardRunId.toLowerCase() === id.toLowerCase());
    if (entry) {
      const b = getBoard(entry.boardId) || {
        id: entry.boardId,
        name: entry.boardId,
        adapter: 'unknown',
        url: '',
        state: 'reviewed',
        rev: 'rev-01',
        runs: 1,
        success: 100,
        missing: [],
        next: '06:00 IST'
      };
      return { entry, run: r, board: b };
    }
  }
  return undefined;
}
