# Job Radar: New Boards Integration Requirements

## Source of truth

- Canonical board inventory: `docs/specs/job-boards-source.md`, section `## New Boards` (65 rows).
- Existing provider contracts: `docs/specs/adapters/`.
- Existing repository behavior and tests are authoritative where they conflict with unverified assumptions in the inventory.

## User-approved scope

1. Integrate every board listed under `## New Boards` into Job Radar.
2. Reuse existing provider-family adapters where live evidence proves the contract works; create a new provider-family adapter or a dedicated custom adapter when required.
3. Preserve each board's exact URL filters and intent (India, engineering/technology, full-time, pagination, etc.).
4. Add a global Job Radar-side India eligibility gate for every board before Job Ops handoff/import:
   - If an extracted location is present and clearly outside India, do not enqueue or send it to Job Ops.
   - If an extracted location is India, an Indian city/state, India-remote, or a multi-location string that includes India, it is eligible.
   - If location is missing/blank/unknown, it remains eligible and may be sent to Job Ops.
   - Ambiguous non-empty locations must not be silently treated as India; classify and retain a durable exclusion reason/observation where the current model supports it.
   - The gate must apply to every current and new board, not only the 65 new boards.
5. Local-only verification in the isolated worktree. Do not deploy, merge, push, alter canonical `main`, touch production, or invoke Job Ops.
6. Handoff to Job Ops must be disabled in all local runtime/config/database tests. Use fakes/mocks for handoff tests and assert zero outbound Job Ops HTTP calls.
7. No hardcoded dummy job data in production code. Fixtures may contain deterministic test records.
8. Implement tests first/alongside changes, including provider fixtures, pagination/filter preservation, India eligibility, missing-location behavior, non-India exclusion, and zero outbound handoff calls.
9. Use explicit worktree imports for Python tests:
   `PYTHONPATH="$PWD/src" /home/priyesh/Work/job-radar/.venv/bin/pytest -q`
10. The implementation branch is `feature/new-boards-india-filter` in `/home/priyesh/Work/job-radar/.claude/worktrees/new-boards-india-filter` on Gaming PC `pb-desk` (`192.168.2.90`).

## Required planning output

Create `IMPLEMENTATION_PLAN.md` in the worktree. It must contain:

- Section 0 document index and assumptions/evidence policy.
- Exact inventory of all 65 boards, one row per board, with proposed adapter family, listing acquisition, detail acquisition, filters/pagination, location strategy, live-canary requirement, test fixture, and any blocker/uncertainty.
- Explicit distinction between verified provider contracts and hypotheses requiring a pre-implementation live canary.
- Phased implementation order that avoids context saturation and integrates one provider/board cohort at a time.
- Exact repository files expected to change/create.
- New adapter architecture where existing families are insufficient (for example SmartRecruiters, Talent500, or company-specific custom contracts), without forcing unrelated sites into the wrong family.
- Global India eligibility design and persistence/observability behavior.
- Local-only execution design with Job Ops handoff disabled and mechanically verified.
- Test matrix, full-suite gate, live-canary gate, isolated database readback, rollback plan, and completion receipt/report requirements.
- Explicit integration gate: no merge/deploy/push without separate approval.

## Remote-agent rule

Do not delegate to subagents or spawn external coding-agent processes. Perform all repository inspection, planning, file edits, tests, fixtures, and reporting directly in this session.
