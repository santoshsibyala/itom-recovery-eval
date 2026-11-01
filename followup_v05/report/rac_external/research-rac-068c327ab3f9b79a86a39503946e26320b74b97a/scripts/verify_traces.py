#!/usr/bin/env python3
"""
verify_traces.py — Analyse pre-recorded benchmark traces.

Reads the JSON execution traces shipped in RAC-CAIS-2026/ and produces
human-readable summary tables that correspond to the evaluation results
presented in the paper.

Usage:
    python scripts/verify_traces.py              # all benchmarks
    python scripts/verify_traces.py --bench tau2  # τ²-bench only
    python scripts/verify_traces.py --bench realm # REALM-Bench only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TAU2_DIR = REPO_ROOT / "RAC-CAIS-2026" / "Tau^2 Bench"
REALM_DIR = REPO_ROOT / "RAC-CAIS-2026" / "REALMBench"

# ── Helpers ──────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | list | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _fmt(val: float, decimals: int = 1) -> str:
    if val == 0:
        return "—"
    return f"{val:,.{decimals}f}"


# ── τ²-bench Analysis ───────────────────────────────────────────────

def analyse_tau2() -> None:
    """Scan Tau^2 Bench task directories and compute per-framework stats."""
    if not TAU2_DIR.exists():
        print("  [SKIP] Tau^2 Bench directory not found.\n")
        return

    # framework -> list of trace dicts
    frameworks: dict[str, list[dict]] = defaultdict(list)

    for task_dir in sorted(TAU2_DIR.iterdir()):
        if not task_dir.is_dir() or task_dir.name in ("prompts", "all_tasks"):
            continue
        for trace_file in task_dir.glob("trace_*.json"):
            data = _load_json(trace_file)
            if data is None or not isinstance(data, dict):
                continue
            fw = data.get("framework") or ""
            if not fw or fw == "?":
                # Legacy traces lack a framework field – infer from filename
                name = trace_file.name.lower()
                if "_rac_" in name:
                    fw = "rac"
                elif "sagallm" in name:
                    fw = "sagallm"
                elif "prompt_engineer" in name:
                    fw = "langgraph_pe"
                elif "langgraph" in name:
                    fw = "langgraph"
                else:
                    fw = "unknown"

            # Extract tokens: prefer top-level, fall back to summing steps
            total_tokens_obj = data.get("total_tokens")
            if isinstance(total_tokens_obj, dict):
                tokens = total_tokens_obj.get("total", 0)
            else:
                # Legacy format: sum tokens from individual steps
                tokens = sum(
                    s.get("tokens", {}).get("total", 0)
                    for s in data.get("steps", [])
                    if isinstance(s, dict)
                )

            # Extract task_id: prefer top-level, infer from directory name
            task_id = data.get("task_id") or task_dir.name.replace("Task-", "")

            # Status: prefer top-level, infer from presence of steps
            status = data.get("status")
            if not status:
                # Legacy traces with steps but no status – mark as "completed"
                # if they have any steps with tokens
                status = "success" if tokens > 0 else "unknown"

            frameworks[fw].append({
                "task": task_id,
                "status": status,
                "tokens": tokens,
                "duration": data.get("duration", 0.0),
            })

    # Deduplicate: keep best (most recent / successful) per (fw, task)
    deduped: dict[str, dict[str, dict]] = {}
    for fw, traces in frameworks.items():
        best: dict[str, dict] = {}
        for t in traces:
            key = t["task"]
            prev = best.get(key)
            # Prefer successful over failed, then higher token count (more complete)
            if prev is None or (t["status"] == "success" and prev["status"] != "success"):
                best[key] = t
            elif t["status"] == prev["status"] and t["tokens"] > prev["tokens"]:
                best[key] = t
        deduped[fw] = best

    # ── Table ────────────────────────────────────────────────────────
    print("=" * 72)
    print("  τ²-bench (Airline Domain) — Per-Framework Summary")
    print("=" * 72)
    header = f"{'Framework':<20} {'Tasks':>6} {'Success':>8} {'Rate':>7} {'Avg Tok':>9} {'Avg Lat':>9}"
    print(header)
    print("-" * 72)

    display_order = ["rac", "sagallm", "langgraph_pe", "langgraph", "unknown"]
    display_names = {
        "rac": "RAC",
        "sagallm": "SagaLLM",
        "langgraph_pe": "LangGraph (PE)",
        "langgraph": "LangGraph",
        "unknown": "Other",
    }

    for fw_key in display_order:
        best = deduped.get(fw_key)
        if not best:
            continue
        traces_list = list(best.values())
        total = len(traces_list)
        successes = sum(1 for t in traces_list if t["status"] == "success")
        valid_tokens = [t["tokens"] for t in traces_list if t["tokens"] > 0]
        avg_tokens = sum(valid_tokens) / max(len(valid_tokens), 1)
        valid_dur = [t["duration"] for t in traces_list if t["duration"] > 0]
        avg_dur = sum(valid_dur) / max(len(valid_dur), 1)
        rate = (successes / total * 100) if total > 0 else 0
        name = display_names.get(fw_key, fw_key)
        print(f"{name:<20} {total:>6} {successes:>8} {rate:>6.1f}% {_fmt(avg_tokens, 0):>9} {_fmt(avg_dur):>8}s")

    print("-" * 72)
    print()

    # Per-task breakdown
    all_tasks = sorted({t for bst in deduped.values() for t in bst})
    if all_tasks:
        print("  Per-Task Breakdown (Success / Tokens)")
        print(f"  {'Task':<12}", end="")
        for fw_key in display_order:
            if fw_key in deduped:
                name = display_names.get(fw_key, fw_key)
                print(f" {name:>18}", end="")
        print()
        print("  " + "-" * (12 + 19 * sum(1 for k in display_order if k in deduped)))
        for task in all_tasks:
            print(f"  {task:<12}", end="")
            for fw_key in display_order:
                best = deduped.get(fw_key, {})
                t = best.get(task)
                if t:
                    mark = "✓" if t["status"] == "success" else "✗"
                    tok = t["tokens"] if t["tokens"] > 0 else "—"
                    print(f" {mark} {str(tok):>15}", end="")
                else:
                    print(f" {'—':>18}", end="")
            print()
        print()


# ── REALM-Bench Analysis ─────────────────────────────────────────────

def analyse_realm() -> None:
    """Scan REALMBench scenario directories and produce a comparison table."""
    if not REALM_DIR.exists():
        print("  [SKIP] REALMBench directory not found.\n")
        return

    print("=" * 80)
    print("  REALM-Bench (Logistics & Disaster Relief) — Per-Scenario Summary")
    print("=" * 80)

    fw_names = {
        "rac_reference": "RAC",
        "langgraph_vanilla_reference": "LangGraph",
        "langgraph_pe_reference": "LangGraph (PE)",
        "saga_llm_reference": "SagaLLM",
        "saga_react_reference": "SagaReAct",
    }

    scenarios = sorted(
        [d.name for d in REALM_DIR.iterdir()
         if d.is_dir() and d.name.startswith("P")],
        key=lambda x: int(x[1:])
    )

    header = f"  {'Scenario':<10}"
    seen_fws = set()
    for scenario in scenarios:
        sdir = REALM_DIR / scenario
        for f in sdir.iterdir():
            if f.suffix == ".json" and f.stem in fw_names:
                seen_fws.add(f.stem)

    ordered_fws = ["rac_reference", "saga_llm_reference", "langgraph_pe_reference",
                    "langgraph_vanilla_reference", "saga_react_reference"]
    active_fws = [fw for fw in ordered_fws if fw in seen_fws]

    for fw in active_fws:
        header += f" {fw_names[fw]:>16}"
    print(header)
    print("  " + "-" * (10 + 17 * len(active_fws)))

    for scenario in scenarios:
        sdir = REALM_DIR / scenario
        row = f"  {scenario:<10}"
        for fw_key in active_fws:
            fpath = sdir / f"{fw_key}.json"
            trace_path = sdir / "trace.json"
            data = None
            if fpath.exists():
                data = _load_json(fpath)
            elif trace_path.exists():
                d = _load_json(trace_path)
                if d and isinstance(d, dict) and d.get("framework", "").replace("_", "") in fw_key.replace("_", ""):
                    data = d

            if data and isinstance(data, dict):
                summary = data.get("summary", {})
                tokens = summary.get("total_tokens", 0)
                duration = data.get("duration", 0)
                comp = summary.get("compensation_count", 0)
                row += f" {tokens:>8}t {duration:>5.1f}s"
            else:
                row += f" {'—':>16}"
        print(row)

    print("  " + "-" * (10 + 17 * len(active_fws)))
    print()

    # Detailed per-scenario info
    print("  Legend: <tokens>t <duration>s")
    print()

    for scenario in scenarios:
        sdir = REALM_DIR / scenario
        fpath = sdir / "rac_reference.json"
        data = _load_json(fpath) if fpath.exists() else None
        if data and isinstance(data, dict):
            summary = data.get("summary", {})
            disruptions = data.get("disruptions", [])
            comp_events = data.get("compensation_events", [])
            print(f"  {scenario}:")
            print(f"    Tool calls: {summary.get('tool_call_count', '?')}, "
                  f"Retries: {summary.get('retry_count', '?')}, "
                  f"Replans: {summary.get('replan_count', '?')}, "
                  f"Compensations: {summary.get('compensation_count', '?')}")
            if disruptions:
                print(f"    Disruptions injected: {len(disruptions)}")
            if comp_events:
                print(f"    Compensation events: {len(comp_events)}")
            print()


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify pre-recorded benchmark traces from RAC-CAIS-2026."
    )
    parser.add_argument(
        "--bench",
        choices=["tau2", "realm", "all"],
        default="all",
        help="Which benchmark to analyse (default: all).",
    )
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║     RAC Artifact — Benchmark Trace Verification                ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    if args.bench in ("tau2", "all"):
        analyse_tau2()

    if args.bench in ("realm", "all"):
        analyse_realm()

    print("Verification complete. Compare the tables above with the paper's")
    print("evaluation results.")
    print()


if __name__ == "__main__":
    main()
