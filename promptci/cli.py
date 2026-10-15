"""Command line: run, gate, check (run + gate), bless, noise."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from . import run as R
from .gate import Rules, compare
from .llm import Model
from .report import markdown
from .suite import load_suite


def _add_run_args(p):
    p.add_argument("--suite", default="suites/triage")
    p.add_argument("--model", "-m", default="mock", help="mock or ollama:<name>")
    p.add_argument("--prompt", help="prompt file (default: the one in suite.json)")
    p.add_argument("--samples", type=int, default=1, help="samples per case (majority vote)")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--workers", type=int, default=1)


def _add_gate_args(p):
    p.add_argument("--max-drop", type=float, default=5.0, help="allowed overall drop, in points")
    p.add_argument("--tag-max-drop", type=float, default=25.0)
    p.add_argument("--require-significance", action="store_true",
                   help="ignore drops that a McNemar test can't tell apart from noise")
    p.add_argument("--report", help="write the markdown report here")


def _rules(a) -> Rules:
    return Rules(max_drop=a.max_drop, tag_max_drop=a.tag_max_drop, require_significance=a.require_significance)


def _do_run(a) -> dict:
    suite = load_suite(a.suite, a.prompt)
    done = []
    tick = lambda _id: (done.append(_id), print(f"\r  {len(done)}/{len(suite.cases)}", end="", file=sys.stderr))
    run = R.run_suite(suite, Model(a.model), a.samples, a.temperature, a.seed, a.workers,
                      tick if sys.stderr.isatty() else None)
    if sys.stderr.isatty():
        print(file=sys.stderr)
    return run


def _gate(baseline: dict, candidate: dict, a) -> int:
    verdict = compare(baseline, candidate, _rules(a))
    text = markdown(verdict, baseline, candidate)
    print(text)
    if a.report:
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(text, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)
    return 0 if verdict.passed else 1


def cmd_run(a) -> int:
    run = _do_run(a)
    s = run["summary"]["overall"]
    print(f"{run['meta']['model']} {run['meta']['prompt']}: {s['passed']}/{s['total']} ({100 * s['rate']:.1f}%)")
    if a.out:
        print("saved", R.save(run, a.out))
    return 0


def cmd_gate(a) -> int:
    return _gate(R.load(a.baseline), R.load(a.candidate), a)


def cmd_check(a) -> int:
    candidate = _do_run(a)
    if a.out:
        R.save(candidate, a.out)
    return _gate(R.load(a.baseline), candidate, a)


def cmd_bless(a) -> int:
    Path(a.baseline).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(a.run, a.baseline)
    print(f"baseline {a.baseline} <- {a.run}")
    return 0


def cmd_noise(a) -> int:
    """Rerun the SAME prompt several times and count how often each gate rule cries wolf."""
    runs = []
    for k in range(a.runs):
        a.seed = 1000 * k
        print(f"run {k + 1}/{a.runs}", file=sys.stderr)
        runs.append(_do_run(a))
    rates = [100 * r["summary"]["overall"]["rate"] for r in runs]
    base = runs[0]
    rows = []
    for label, rules in [("naive: any drop > 0 points", Rules(max_drop=0, tag_max_drop=0, critical=False)),
                         (f"threshold: drop > {a.max_drop:g} points + critical cases", Rules(max_drop=a.max_drop)),
                         ("threshold + McNemar p < 0.05", Rules(max_drop=a.max_drop, require_significance=True))]:
        alarms = sum(not compare(base, r, rules).passed for r in runs[1:])
        rows.append(f"| {label} | {alarms}/{len(runs) - 1} |")
    flips = [len(compare(base, r).lost) + len(compare(base, r).gained) for r in runs[1:]]
    text = "\n".join([
        f"## Noise check: `{base['meta']['model']}`, `{base['meta']['prompt']}`, temperature {a.temperature}", "",
        f"Pass rates over {a.runs} identical runs: {', '.join(f'{x:.1f}%' for x in rates)} "
        f"(spread {max(rates) - min(rates):.1f} points). Cases flipped vs run 1: {flips}.", "",
        "| Gate rule | False alarms (prompt unchanged) |", "|---|---|", *rows, ""])
    print(text)
    if a.report:
        Path(a.report).write_text(text, encoding="utf-8")
    if a.out:
        for k, r in enumerate(runs):
            R.save(r, Path(a.out) / f"noise_{k}.json")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="promptci", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="run a suite and save the results")
    _add_run_args(p)
    p.add_argument("--out", "-o")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("gate", help="compare two saved runs; exit 1 on regression")
    p.add_argument("baseline")
    p.add_argument("candidate")
    _add_gate_args(p)
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("check", help="run the suite now and gate it against a baseline (for CI)")
    _add_run_args(p)
    _add_gate_args(p)
    p.add_argument("--baseline", "-b", required=True)
    p.add_argument("--out", "-o")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("bless", help="accept a run as the new baseline")
    p.add_argument("run")
    p.add_argument("baseline")
    p.set_defaults(fn=cmd_bless)

    p = sub.add_parser("noise", help="measure false alarms by rerunning an unchanged prompt")
    _add_run_args(p)
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--max-drop", type=float, default=5.0)
    p.add_argument("--report")
    p.add_argument("--out", help="folder for the individual runs")
    p.set_defaults(fn=cmd_noise)

    a = ap.parse_args(argv)
    return a.fn(a)
