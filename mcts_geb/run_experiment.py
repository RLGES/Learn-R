"""
mcts_geb/run_experiment.py

Entry point: builds the combined action space (static rewrite_rules'
egglog equivalents + LLM-learned rules from this repo's real learned-
rules pipeline), then runs MCTS-GEB and plain equality saturation on a
sample set of test cases, and prints/saves a comparison table.

Usage:
    cd Learn-R-main
    python -m mcts_geb.run_experiment
    python -m mcts_geb.run_experiment --no-llm            # static rules only
    python -m mcts_geb.run_experiment --simulations 200 --steps 10
    python -m mcts_geb.run_experiment --provider anthropic --verify

Output:
    - a results table printed to stdout
    - mcts_geb/results.json  (machine-readable results)
    - mcts_geb/results.csv   (spreadsheet-friendly results)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcts_geb.rulesets import build_action_space
from mcts_geb.search import mcts_construct, plain_saturation
from mcts_geb.test_cases import get_test_cases


def main():
    parser = argparse.ArgumentParser(description="Run MCTS-GEB over this repo's rewrite rules.")
    parser.add_argument("--no-llm", action="store_true", help="Use only static rules (skip LLM rule generation).")
    parser.add_argument("--provider", default=None, help="LLM provider override (openai/anthropic/google/lmstudio/huggingface).")
    parser.add_argument("--verify", action="store_true", help="Enable Z3 SMT verification of learned rules (requires z3-solver).")
    parser.add_argument("--simulations", type=int, default=100, help="MCTS simulations per construction step.")
    parser.add_argument("--steps", type=int, default=8, help="Number of actions MCTS commits to per test case.")
    parser.add_argument("--rollout-depth", type=int, default=5, help="Random rollout depth during MCTS simulation.")
    parser.add_argument("--sat-iters", type=int, default=8, help="Iterations for the plain-saturation baseline.")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility.")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-rule generation logging.")
    args = parser.parse_args()

    verbose = not args.quiet

    print("=" * 78)
    print("MCTS-GEB: Monte Carlo Tree Search over Learn-R's rewrite rules")
    print("=" * 78)

    test_cases = get_test_cases()
    windows = [instr for _, _, instr in test_cases]

    print(f"\nBuilding action space (static rules{' + LLM-learned rules' if not args.no_llm else ' only'})...")
    action_names, rules = build_action_space(
        instruction_windows=windows,
        use_llm=not args.no_llm,
        provider=args.provider,
        verify=args.verify,
        verbose=verbose,
    )
    print(f"\nTotal actions available to MCTS: {len(rules)}")
    n_static = sum(1 for n in action_names if n.startswith("static/"))
    n_learned = sum(1 for n in action_names if n.startswith("learned/"))
    print(f"  static rules : {n_static}")
    print(f"  learned rules: {n_learned}")

    print(f"\nRunning {len(test_cases)} test case(s)...\n")

    results = []
    header = f"{'test case':28} {'init':>5} {'MCTS':>6} {'saturation':>11} {'mcts time':>10} {'actions used'}"
    print(header)
    print("-" * len(header))

    for name, expr_fn, _instr in test_cases:
        t0 = time.time()
        mcts_result = mcts_construct(
            expr_fn,
            rules,
            action_names,
            n_construction_steps=args.steps,
            n_simulations=args.simulations,
            max_sim_step=args.rollout_depth,
            seed=args.seed,
        )
        mcts_time = time.time() - t0

        sat_expr, sat_init, sat_cost = plain_saturation(expr_fn, rules, iters=args.sat_iters)

        used = ", ".join(mcts_result.action_names) if mcts_result.action_names else "(none)"
        print(f"{name:28} {mcts_result.initial_cost:>5} {mcts_result.final_cost:>6} {sat_cost:>11} {mcts_time:>9.2f}s {used}")

        results.append({
            "test_case": name,
            "initial_cost": mcts_result.initial_cost,
            "mcts_cost": mcts_result.final_cost,
            "mcts_expr": mcts_result.final_expr,
            "mcts_actions": mcts_result.action_names,
            "saturation_cost": sat_cost,
            "saturation_expr": sat_expr,
            "mcts_time_sec": round(mcts_time, 3),
        })

    out_dir = Path(__file__).parent
    json_path = out_dir / "results.json"
    csv_path = out_dir / "results.csv"

    with open(json_path, "w") as f:
        json.dump({
            "config": vars(args),
            "n_static_rules": n_static,
            "n_learned_rules": n_learned,
            "results": results,
        }, f, indent=2)

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "test_case", "initial_cost", "mcts_cost", "saturation_cost",
            "mcts_time_sec", "mcts_expr", "saturation_expr", "mcts_actions",
        ])
        writer.writeheader()
        for r in results:
            row = dict(r)
            row["mcts_actions"] = "; ".join(row["mcts_actions"])
            writer.writerow(row)

    print(f"\nSaved: {json_path}")
    print(f"Saved: {csv_path}")

    n_matched_or_beat_saturation = sum(1 for r in results if r["mcts_cost"] <= r["saturation_cost"])
    print(f"\nMCTS matched-or-beat plain saturation on {n_matched_or_beat_saturation}/{len(results)} test cases.")


if __name__ == "__main__":
    main()
