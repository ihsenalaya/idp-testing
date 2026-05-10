# Demo Pull Requests — Narrative Guide

Each demo branch demonstrates a specific operator behaviour driven by the diff.
Open them with `scripts/open-demo-prs.sh`.

---

## 1. `demo/docs-only` — Documentation-only change

**What changes:** Only `README.md` is modified (a sentence in the quickstart).

**What the operator does:**
- Detects no `database-migration`, `api-contract`, `backend`, or `frontend` files.
- Sets `detectedImpacts.docs = true`; all others `false`.
- Skips: contract tests, regression tests, migration tests, E2E.
- Runs: none beyond a smoke check.

**PR comment says:**
> "This PR touches **docs** only. The operator skipped all heavy test suites.
>  Re-running the pipeline would cost <30 s instead of the usual 4–6 min."

**What this proves:** The operator's file-classifier correctly identifies documentation-only
changes and avoids wasting CI time on unrelated test suites.

---

## 2. `demo/frontend-only` — Tailwind CSS change

**What changes:** `frontend.py` — one Tailwind class on the catalog grid is updated
(e.g. `gap-4` → `gap-6`).

**What the operator does:**
- Detects `frontend = true`, `backend = false`, `apiContract = false`.
- Runs: E2E tests (visual regression).
- Skips: backend regression, contract tests, migration tests.

**PR comment says:**
> "This PR touches **frontend** only. Regression and contract tests were skipped;
>  E2E ran to verify that the visual change doesn't break user flows."

**What this proves:** Frontend-only changes don't trigger expensive backend test suites.

---

## 3. `demo/api-contract-change` — Correct contract update

**What changes:** `app.py` adds an optional `note` field to `POST /api/orders`.
`api/openapi.yaml` is updated to declare the new field in `OrderCreate`.

**What the operator does:**
- Detects `backend = true`, `apiContract = true`.
- Runs: contract tests (schemathesis), regression tests.
- Skips: E2E (no frontend file changed).

**PR comment says:**
> "This PR touches **api-contract** and **backend**. Contract tests and regression
>  tests ran and passed — the spec and implementation are aligned."

**What this proves:** When both code and spec are updated correctly, the operator
confirms alignment and the PR is safe to merge.

---

## 4. `demo/api-contract-mismatch` — Drift detected (intentional failure)

**What changes:** `app.py` adds the `note` field to `POST /api/orders` BUT
`api/openapi.yaml` is NOT updated.

**What the operator does:**
- Detects `backend = true`, `apiContract = false` (openapi.yaml not touched).
- Runs: contract tests + regression tests.
- Contract tests FAIL: schemathesis finds that the implementation accepts a field
  (`note`) that the spec does not declare.

**PR comment says:**
> ❌ Contract drift detected — the implementation accepts a request body field
> (`note`) that is not declared in `api/openapi.yaml`. Update either the spec or
> remove the undeclared field.

**What this proves:** The most valuable demo — the operator catches contract drift
before it reaches production. kagent reads the schemathesis failure and explains
the fix in plain English.

---

## 5. `demo/database-migration` — New Alembic migration

**What changes:** A new file `migrations/versions/004_add_order_status_index.py`
that adds an index on `orders.status` for query performance.

**What the operator does:**
- Detects `databaseMigration = true`.
- Runs: migration tests (up + down), full regression.
- Creates a DB checkpoint before and after the migration.
- Skips: contract tests (openapi.yaml not touched), E2E.

**PR comment says:**
> "This PR adds a database migration. Migration up/down tests passed. A checkpoint
>  `after-migration-004` was created. Regression tests verified existing queries
>  are unaffected."

**What this proves:** The operator's migration awareness creates safety checkpoints
automatically, and tests prove the migration is reversible.

---

## 6. `demo/perf-sensitive` — Performance-sensitive backend change

**What changes:** Commit message starts with `perf:`. `app.py` rewrites the
`/api/products/discounted` query to use a covering index instead of a seq-scan.

**What the operator does:**
- Detects `perf:` prefix in commit message → enables load tests + tracing diff.
- Detects `backend = true` → runs regression tests.
- OpenTelemetry traces from the before/after runs are compared in Jaeger.

**PR comment says:**
> "This PR is marked `perf:`. A load test was run and a Jaeger trace comparison
>  is available at the link below. P99 latency for `GET /api/products/discounted`
>  dropped from 42 ms to 11 ms."

**What this proves:** The operator adapts not just to file-type but to commit
message semantics — demonstrating full extensibility of `spec.changeContext`.
