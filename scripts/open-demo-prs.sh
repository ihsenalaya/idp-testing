#!/usr/bin/env bash
# open-demo-prs.sh — push all demo branches and open PRs via GitHub CLI.
#
# Usage:
#   bash scripts/open-demo-prs.sh
#
# Requires: git, gh (GitHub CLI, authenticated)
# The script is idempotent: it can be run multiple times safely.
set -euo pipefail

REPO=$(git remote get-url origin 2>/dev/null | sed 's|.*github.com[:/]||;s|\.git$||')
BASE_BRANCH="main"
CURRENT_BRANCH=$(git branch --show-current)

log()  { echo "→ $*"; }
warn() { echo "⚠  $*" >&2; }

require_cmd() {
  if ! command -v "$1" &>/dev/null; then
    echo "ERROR: '$1' is required but not found." >&2
    exit 1
  fi
}

require_cmd git
require_cmd gh

# ── Helper: create branch, apply change, push, open PR ───────────────────────

open_demo_pr() {
  local branch="$1"
  local title="$2"
  local body="$3"
  local patch_fn="$4"   # name of a function defined below

  log "Processing $branch …"

  # Abort any in-progress rebase/merge
  git rebase --abort 2>/dev/null || true

  # Go back to main and pull latest
  git checkout "$BASE_BRANCH" --quiet
  git pull --quiet origin "$BASE_BRANCH" 2>/dev/null || true

  # Create or reset the demo branch
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    git branch -D "$branch"
  fi
  git checkout -b "$branch"

  # Apply the demo change
  "$patch_fn"

  # Commit and push
  git add -A
  git diff --cached --quiet && { warn "No changes on $branch — skipping"; git checkout "$BASE_BRANCH" --quiet; return; }
  git commit -m "$title"
  git push --force --quiet origin "$branch"

  # Open PR (idempotent: error if PR exists is fine)
  gh pr create \
    --repo "$REPO" \
    --base "$BASE_BRANCH" \
    --head "$branch" \
    --title "$title" \
    --body "$body" 2>/dev/null \
    || log "  PR for $branch already exists — skipping creation."

  git checkout "$BASE_BRANCH" --quiet
}

# ── Demo 1: docs-only ─────────────────────────────────────────────────────────

patch_docs_only() {
  local ts; ts=$(date +%s)
  # Append a harmless sentence to README so the diff is non-empty
  echo "" >> README.md
  echo "<!-- demo touch $ts -->" >> README.md
}

open_demo_pr \
  "demo/docs-only" \
  "docs: update README quickstart section" \
  "Changes only \`README.md\`. Expected: operator skips all heavy tests; PR comment explains why." \
  patch_docs_only

# ── Demo 2: frontend-only ─────────────────────────────────────────────────────

patch_frontend_only() {
  # Update a Tailwind-equivalent class in the frontend template
  sed -i 's/gap:1rem/gap:1.5rem/g' frontend.py || true
}

open_demo_pr \
  "demo/frontend-only" \
  "style: increase product grid gap on catalog page" \
  "Updates a layout class in \`frontend.py\`. Expected: E2E runs; backend regression skipped." \
  patch_frontend_only

# ── Demo 3: api-contract-change (correct) ─────────────────────────────────────

patch_api_contract_change() {
  # 1. Add `note` field in app.py (api_create_order)
  python3 - <<'PY'
import pathlib, re

path = pathlib.Path("app.py")
src = path.read_text()

# Add note extraction after data = request.get_json...
old = "    product_id = data.get(\"product_id\")\n    quantity   = int(data.get(\"quantity\", 1))"
new = "    product_id = data.get(\"product_id\")\n    quantity   = int(data.get(\"quantity\", 1))\n    note       = str(data.get(\"note\", \"\"))[:200] or None"
src = src.replace(old, new)
path.write_text(src)
PY

  # 2. Update openapi.yaml to declare the new field in OrderCreate
  python3 - <<'PY'
import pathlib

path = pathlib.Path("api/openapi.yaml")
src = path.read_text()
old = "    OrderCreate:\n      type: object\n      required:\n      - product_id"
new = ("    OrderCreate:\n"
       "      type: object\n"
       "      required:\n"
       "      - product_id\n"
       "      properties:\n"
       "        note:\n"
       "          type: string\n"
       "          maxLength: 200\n"
       "          nullable: true\n"
       "          description: Optional note attached to the order")
if old not in src:
    print("Marker not found in openapi.yaml — patching manually")
else:
    path.write_text(src.replace(old, new))
PY
}

open_demo_pr \
  "demo/api-contract-change" \
  "feat(orders): add optional note field to POST /api/orders" \
  "Adds \`note\` field in both \`app.py\` and \`api/openapi.yaml\`. Expected: contract + regression pass." \
  patch_api_contract_change

# ── Demo 4: api-contract-mismatch (intentional failure) ───────────────────────

patch_api_contract_mismatch() {
  # Add `internal_ref` to app.py response only — do NOT touch openapi.yaml
  python3 - <<'PY'
import pathlib

path = pathlib.Path("app.py")
src = path.read_text()
old = '        return jsonify({"id": r[0], "product_id": r[1], "quantity": r[2],\n                        "status": r[3], "created_at": r[4].isoformat()}), 201'
new = ('        return jsonify({"id": r[0], "product_id": r[1], "quantity": r[2],\n'
       '                        "status": r[3], "created_at": r[4].isoformat(),\n'
       '                        "internal_ref": "ord-" + str(r[0])}), 201')
if old in src:
    path.write_text(src.replace(old, new))
else:
    print("Marker not found — applying simple append")
    with open("app.py", "a") as f:
        f.write("\n# demo/api-contract-mismatch marker\n")
PY
}

open_demo_pr \
  "demo/api-contract-mismatch" \
  "feat(orders): add internal_ref to order response (contract not updated)" \
  "Adds \`internal_ref\` field in \`app.py\` but NOT in \`openapi.yaml\`. Expected: contract tests fail." \
  patch_api_contract_mismatch

# ── Demo 5: database-migration ────────────────────────────────────────────────

patch_database_migration() {
  cat > migrations/versions/004_add_order_status_index.py <<'PY'
"""add index on orders.status for query performance

Revision ID: 004
Revises: 003
Create Date: 2026-05-10
"""
from typing import Sequence, Union
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_orders_status", "orders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_orders_status", table_name="orders")
PY
}

open_demo_pr \
  "demo/database-migration" \
  "perf(db): add index on orders.status for faster status filtering" \
  "Adds Alembic migration 004. Expected: migration up/down tests run, full regression run." \
  patch_database_migration

# ── Demo 6: perf-sensitive ────────────────────────────────────────────────────

patch_perf_sensitive() {
  # Rewrite the discounted products query to add EXPLAIN comment (cosmetic change)
  python3 - <<'PY'
import pathlib

path = pathlib.Path("app.py")
src = path.read_text()
old = '            WHERE p.discount_pct >= %s AND p.stock > 0\n            ORDER BY p.discount_pct DESC'
new = '            WHERE p.discount_pct >= %s AND p.stock > 0\n            ORDER BY p.discount_pct DESC, p.id'
if old in src:
    path.write_text(src.replace(old, new))
else:
    with open("app.py", "a") as f:
        f.write("\n# perf: deterministic ordering for discounted products\n")
PY
}

open_demo_pr \
  "demo/perf-sensitive" \
  "perf: deterministic ordering for GET /api/products/discounted" \
  "Commit starts with \`perf:\`. Changes pricing query ordering. Expected: load test + tracing diff." \
  patch_perf_sensitive

# ── Done ──────────────────────────────────────────────────────────────────────

git checkout "$CURRENT_BRANCH" 2>/dev/null || git checkout "$BASE_BRANCH"

log ""
log "All demo PRs opened. View them at:"
log "  https://github.com/$REPO/pulls"
