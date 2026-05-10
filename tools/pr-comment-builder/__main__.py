"""
PR Comment Builder — idp-preview demo companion.

Reads:
  --change-context  YAML file emitted by the operator (spec.changeContext)
  --report-dir      Directory containing pytest-report.json (default: ./test-reports)
  --preview-url     Preview environment URL
  --namespace       Kubernetes namespace of the preview
  --pr              Pull-request number
  --output          Output file (default: stdout)

Produces a single Markdown comment suitable for posting/updating on the PR.
If --change-context is omitted, falls back to "full results" mode.

The comment is idempotent: include the same HTML marker so the GitHub workflow
can PATCH the existing comment instead of creating a new one.

Usage:
    python3 -m tools.pr-comment-builder \\
        --change-context change_context.yaml \\
        --report-dir ./test-reports \\
        --preview-url http://pr-42.preview.example.com \\
        --namespace preview-pr-42 \\
        --pr 42
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ── Marker used for idempotent comment updates ────────────────────────────────
MARKER = "<!-- idp-preview-pr-comment -->"

# ── File-type classification patterns ────────────────────────────────────────
FILE_CLASSIFIERS: list[tuple[str, str]] = [
    ("migrations/versions/", "database-migration"),
    ("alembic/versions/",    "database-migration"),
    ("api/openapi.yaml",     "api-contract"),
    ("openapi.yaml",         "api-contract"),
    ("frontend/",            "frontend"),
    ("templates/",           "frontend"),
    ("frontend.py",          "frontend"),
    ("tests/",               "tests"),
    ("docs/",                "docs"),
    ("*.md",                 "docs"),
    ("README",               "docs"),
    ("app.py",               "backend"),
    ("backend/",             "backend"),
]


def classify_file(path: str) -> str:
    for pattern, kind in FILE_CLASSIFIERS:
        if pattern.endswith("/") and pattern in path:
            return kind
        if pattern.startswith("*.") and path.endswith(pattern[1:]):
            return kind
        if not pattern.endswith("/") and not pattern.startswith("*.") and pattern in path:
            return kind
    return "other"


def group_files(files: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for f in files:
        kind = classify_file(f)
        grouped.setdefault(kind, []).append(f)
    return grouped


# ── changeContext parsing ─────────────────────────────────────────────────────

def load_change_context(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = pathlib.Path(path)
    if not p.exists():
        return None
    text = p.read_text()
    if YAML_AVAILABLE:
        return yaml.safe_load(text) or {}
    # Minimal fallback: just return raw text info
    return {"raw": text}


def extract_detected_impacts(ctx: dict) -> dict[str, bool]:
    impacts = ctx.get("detectedImpacts", {})
    if isinstance(impacts, dict):
        return {k: bool(v) for k, v in impacts.items()}
    return {}


# ── Test report parsing ───────────────────────────────────────────────────────

def load_pytest_report(report_dir: str) -> dict[str, Any] | None:
    p = pathlib.Path(report_dir) / "pytest-report.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def summarise_pytest_report(report: dict) -> dict[str, Any]:
    summary = report.get("summary", {})
    tests = report.get("tests", [])

    suites: dict[str, dict] = {}
    for t in tests:
        node = t.get("nodeid", "")
        # Extract suite name from test path (tests/unit, tests/regression, etc.)
        parts = node.split("/")
        if len(parts) >= 2:
            suite = parts[1] if parts[0] == "tests" else parts[0]
        else:
            suite = "other"

        if suite not in suites:
            suites[suite] = {"passed": 0, "failed": 0, "skipped": 0, "failures": []}

        outcome = t.get("outcome", "")
        if outcome == "passed":
            suites[suite]["passed"] += 1
        elif outcome == "failed":
            suites[suite]["failed"] += 1
            call = t.get("call", {})
            suites[suite]["failures"].append({
                "name": node,
                "message": call.get("longrepr", "")[:500],
            })
        elif outcome == "skipped":
            suites[suite]["skipped"] += 1

    duration = report.get("duration", 0)
    return {
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "skipped": summary.get("skipped", 0),
        "duration": round(duration, 1),
        "suites": suites,
    }


# ── Comment sections ──────────────────────────────────────────────────────────

IMPACT_ICONS = {
    "database":    "🗄️",
    "databaseMigration": "🗄️",
    "apiContract": "📄",
    "backend":     "⚙️",
    "frontend":    "🎨",
    "tests":       "🧪",
    "docs":        "📚",
    "payments":    "💳",
    "orders":      "🛒",
}


def render_section1_what_changed(ctx: dict | None, args: argparse.Namespace) -> str:
    if not ctx:
        return ""
    diff = ctx.get("diff", {})
    files_changed = diff.get("filesChanged", [])
    additions = diff.get("additions", "?")
    deletions = diff.get("deletions", "?")
    grouped = group_files(files_changed)

    lines = [
        "## 📂 What Changed\n",
        f"**{len(files_changed)} files changed** · +{additions} / -{deletions}\n",
    ]

    if grouped:
        lines.append("\n| Type | Files |")
        lines.append("|------|-------|")
        for kind, flist in sorted(grouped.items()):
            label = kind.replace("-", " ").title()
            display = ", ".join(f"`{f}`" for f in flist[:4])
            if len(flist) > 4:
                display += f" _+{len(flist)-4} more_"
            lines.append(f"| {label} | {display} |")

    # Impact badge row
    impacts = extract_detected_impacts(ctx)
    if impacts:
        lines.append("\n**Detected impacts:**\n")
        badges = []
        for impact, active in impacts.items():
            icon = IMPACT_ICONS.get(impact, "🔹")
            badge = "✅" if active else "⛔"
            badges.append(f"{badge} {icon} {impact}")
        lines.append("  ".join(badges))

    return "\n".join(lines) + "\n"


def render_section2_why_tests_ran(ctx: dict | None) -> str:
    if not ctx:
        return ""
    impacts = extract_detected_impacts(ctx)
    active = [k for k, v in impacts.items() if v]
    inactive = [k for k, v in impacts.items() if not v]

    if not active:
        return ""

    enabled_str = ", ".join(f"**{k}**" for k in active)
    skipped_str = ""
    if inactive:
        skipped_str = " ".join(f"**{k}**" for k in inactive) + " was skipped because no matching file changed."

    text = (
        f"> This PR touches {enabled_str}. "
        f"The operator therefore enabled: {enabled_str} tests. "
        f"{skipped_str}"
    )

    return "## 🤔 Why These Tests Ran\n\n" + text + "\n\n"


def render_section3_test_results(summary: dict | None) -> str:
    if not summary:
        return "## 🧪 Test Results\n\n_No test report found._\n\n"

    total = summary["total"]
    passed = summary["passed"]
    failed = summary["failed"]
    skipped = summary["skipped"]
    duration = summary["duration"]

    overall = "✅ All passed" if failed == 0 else f"❌ {failed} failed"
    lines = [
        "## 🧪 Test Results\n",
        f"**{overall}** — {passed}/{total} passed · {skipped} skipped · {duration}s\n",
        "\n| Suite | Status | Passed | Failed | Skipped |",
        "|-------|--------|--------|--------|---------|",
    ]

    for suite, data in summary["suites"].items():
        status = "✅" if data["failed"] == 0 else "❌"
        lines.append(
            f"| `{suite}` | {status} | {data['passed']} | {data['failed']} | {data['skipped']} |"
        )

    # Failures detail
    all_failures = []
    for data in summary["suites"].values():
        all_failures.extend(data["failures"])

    if all_failures:
        lines.append("\n<details>")
        lines.append("<summary>🔴 Failure details</summary>\n")
        for f in all_failures[:10]:  # cap at 10
            lines.append(f"**`{f['name']}`**")
            lines.append("```")
            lines.append(f["message"][:400])
            lines.append("```\n")
        lines.append("</details>")

    return "\n".join(lines) + "\n\n"


def render_section4_preview_env(args: argparse.Namespace) -> str:
    url = args.preview_url or "_not set_"
    ns = args.namespace or "_not set_"
    pr = args.pr or "_"

    lines = [
        "## 🌐 Preview Environment\n",
        f"| Key | Value |",
        "|-----|-------|",
        f"| Preview URL | [{url}]({url}) |",
        f"| Namespace | `{ns}` |",
        f"| PR | #{pr} |",
        f"| Checkpoint | `after-seed` |",
    ]
    return "\n".join(lines) + "\n\n"


def render_section5_next_steps(summary: dict | None, ctx: dict | None) -> str:
    suggestions: list[str] = []

    if summary:
        for suite, data in summary["suites"].items():
            for f in data["failures"]:
                name = f["name"]
                msg = f["message"].lower()

                if "contract" in suite or "schemathesis" in name:
                    suggestions.append(
                        "**Contract drift detected** — update either `api/openapi.yaml` or "
                        "the implementation to realign the contract."
                    )
                elif "migration" in suite and "downgrade" in name:
                    suggestions.append(
                        "**Migration is not reversible** — the `downgrade` path failed. "
                        "Ensure your `downgrade()` function is a true inverse of `upgrade()`."
                    )
                elif "idempotency" in name or "duplicate" in msg:
                    suggestions.append(
                        f"**Idempotency issue in `{name}`** — the endpoint accepted duplicate "
                        "requests. Add a uniqueness check before inserting."
                    )
                elif "total_price" in msg or "total_price" in name:
                    suggestions.append(
                        f"**Missing field in `{name}`** — the API response does not include "
                        "`total_price`. Add it to the order response in `app.py::api_create_order()`."
                    )
                elif "kagent_demo" in name.lower():
                    suggestions.append(
                        f"**Demo failure `{name.split('::')[-1]}`** — see the kagent AI analysis "
                        "comment below for the suggested fix."
                    )

    if not suggestions:
        suggestions.append("✅ No issues detected — the diff looks clean.")

    lines = ["## 💡 Next Steps\n"]
    for s in suggestions:
        lines.append(f"- {s}")

    return "\n".join(lines) + "\n\n"


# ── Main renderer ─────────────────────────────────────────────────────────────

def build_comment(args: argparse.Namespace) -> str:
    ctx = load_change_context(args.change_context)
    report_raw = load_pytest_report(args.report_dir)
    summary = summarise_pytest_report(report_raw) if report_raw else None

    diff_aware = ctx is not None
    mode_label = "diff-aware" if diff_aware else "full results (no changeContext provided)"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    parts = [
        MARKER,
        f"# idp-preview — PR #{args.pr or '?'} · {mode_label}\n",
        f"_Generated {ts}_\n\n",
        "---\n",
    ]

    if diff_aware:
        parts.append(render_section1_what_changed(ctx, args))
        parts.append("---\n")
        parts.append(render_section2_why_tests_ran(ctx))
        parts.append("---\n")

    parts.append(render_section3_test_results(summary))
    parts.append("---\n")
    parts.append(render_section4_preview_env(args))
    parts.append("---\n")
    parts.append(render_section5_next_steps(summary, ctx))

    if not diff_aware:
        parts.append(
            "> ℹ️ **Full-results mode**: no `changeContext` was provided. "
            "All test suites ran. To enable diff-aware behaviour, ensure the "
            "idp-preview operator emits `spec.changeContext` in the Preview CR.\n"
        )

    return "\n".join(parts)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Build a GitHub PR comment from test results.")
    parser.add_argument("--change-context", metavar="FILE",
                        help="Operator-emitted changeContext YAML")
    parser.add_argument("--report-dir", default="./test-reports",
                        help="Directory with pytest-report.json (default: ./test-reports)")
    parser.add_argument("--preview-url", default="", help="Preview environment URL")
    parser.add_argument("--namespace", default="", help="Kubernetes namespace")
    parser.add_argument("--pr", default="", help="Pull-request number")
    parser.add_argument("--output", default="-",
                        help="Output file path (default: stdout)")
    args = parser.parse_args()

    comment = build_comment(args)

    if args.output == "-":
        print(comment)
    else:
        pathlib.Path(args.output).write_text(comment)
        print(f"Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
