# CI Review Follow-ups Implementation Plan

> **For agentic workers:** Execute inline with targeted regression tests; the user has authorized implementation and PR creation.

**Goal:** Address PR #1's three post-merge findings without repeating CI deployment.
**Architecture:** Keep the existing locked toolchains and split workflow path filters by backend, worker and frontend. Share the offline socket fixture from the repository root, and exercise the actual worker against temporary SQLite and an in-memory scheduler.
**Tech Stack:** Python 3.12, pytest, SQLAlchemy, APScheduler 3.11, existing GitHub Actions.
**Spec:** PR #1 review threads and the user's 2026-10-18 repair request; AGENTS.md and RULES.md.

## Global Constraints

- No production behavior changes, new dependencies, deployment or merge.
- Preserve pinned Actions, locked dependencies and secret-free CI configuration.
- Validate affected behavior only; the shared fixture warrants one final Python suite run.

## Review Focus / Known Failure Modes

- Worker-only changes must run worker tests without the full backend suite.
- Backend application and Python dependency changes must also verify their worker consumer.
- IPv4/IPv6 UDP sendmsg must fail before transmitting; Unix socket IPC must remain usable.
- Refresh failure must close the session, record the heartbeat and permit another cycle.
- One-shot mode must initialize storage and refresh once; scheduled mode must retain timezone, interval and overlap/misfire limits.

### Task 1: Offline guard

**Files:** Move backend/tests/conftest.py to conftest.py; extend backend/tests/test_offline_guard.py.
**Interface:** Autouse disable_network fixture applies to both Python suites.
- [x] Add IPv4/IPv6 sendmsg regressions using loopback destinations; observe expected failures.
- [x] Block optional sendmsg; preserve Unix sockets and test their actual data exchange.
- [x] Run only the offline guard tests.

### Task 2: Worker verification and CI routing

**Files:** worker/tests/test_worker.py, pyproject.toml, .github/workflows/{ci,worker,frontend}.yml.
**Interface:** Worker imports backend app; root fixture isolates both suites.
- [x] Test refresh persistence for the configured location, session cleanup and recovery from an exception, --once and scheduled main configuration.
- [x] Add worker test discovery and repository-root import path; keep business code unchanged.
- [x] Split workflows: backend/** runs backend tests; worker/** and backend/app/** run worker tests; frontend/** runs only the build. Shared Python configuration/fixture changes run both Python suites.
- [x] Check workflow syntax and routing for frontend-only, worker-only, backend application, shared Python and documentation changes.

### Task 3: Verification and delivery

**Files:** README.md, DECISIONS.md, SESSION_STATE.md.
- [x] Sync documentation with actual commands, boundaries and results.
- [x] Run affected tests during development, then the Python suites once with a JUnit report. Do not rebuild the unchanged frontend locally.
- [x] Review the full diff independently; no blocking findings.

Delivery: commit to `fix/ci-review-followups`, push, create a PR and inspect its Actions runs. The PR checks are the authoritative remote execution record.
