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


def false_alarm_report(runs: list[dict], max_drop: float, temperature) -> str:
    """Compare every ordered pair of identical-prompt runs and count how often each rule fails the gate."""
    pairs = [(i, j) for i in range(len(runs)) for j in range(len(runs)) if i != j]
    rules = [("naive: any drop fails", Rules(max_drop=0, tag_max_drop=0, critical=False)),
             (f"drop > {max_drop:g} pts + tag + critical (default)", Rules(max_drop=max_drop)),
             ("default + McNemar p < 0.05 on drops", Rules(max_drop=max_drop, require_significance=True)),
             ("critical-case rule alone", Rules(max_drop=1e9, tag_max_drop=1e9)),
             ("McNemar-gated drops, no critical rule", Rules(max_drop=max_drop, require_significance=True, critical=False))]
    rows = [f"| {label} | {sum(not compare(runs[i], runs[j], r).passed for i, j in pairs)}/{len(pairs)} |"
            for label, r in rules]
    rates = [100 * r["summary"]["overall"]["rate"] for r in runs]
    flaky = sorted({c["id"] for k, c in enumerate(runs[0]["cases"])
                    if len({r["cases"][k]["passed"] for r in runs}) > 1})
    m = runs[0]["meta"]
    return "\n".join([
        f"## Noise check: `{m['model']}`, `{m['prompt']}`, temperature {temperature}", "",
        f"Pass rates over {len(runs)} identical runs: {', '.join(f'{x:.1f}%' for x in rates)} "
        f"(spread {max(rates) - min(rates):.1f} points). {len(flaky)} of {len(runs[0]['cases'])} cases "
        f"changed verdict at least once.", "",
        f"| Gate rule | False alarms ({len(pairs)} comparisons, prompt unchanged) |", "|---|---|", *rows, ""])


def cmd_noise(a) -> int:
    """Rerun the SAME prompt several times and count how often each gate rule cries wolf."""
    if a.from_dir:
        runs = [R.load(p) for p in sorted(Path(a.from_dir).glob("noise_*.json"))]
        temperature = runs[0]["meta"]["temperature"]
    else:
        runs = []
        for k in range(a.runs):
            a.seed = 1000 * k
            print(f"run {k + 1}/{a.runs}", file=sys.stderr)
            runs.append(_do_run(a))
            if a.out:
                R.save(runs[-1], Path(a.out) / f"noise_{k}.json")
        temperature = a.temperature
    text = false_alarm_report(runs, a.max_drop, temperature)
    print(text)
    if a.report:
        Path(a.report).write_text(text, encoding="utf-8")
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
    p.add_argument("--from-dir", help="recompute the table from saved noise_*.json runs (no model calls)")
    p.set_defaults(fn=cmd_noise)

    a = ap.parse_args(argv)
    return a.fn(a)
