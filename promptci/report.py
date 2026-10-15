"""Markdown report for a gate verdict (fits a PR comment or the GitHub job summary)."""
from __future__ import annotations

from .gate import Verdict, flaky_cases


def _failures(case: dict) -> str:
    for s in case["samples"]:
        bad = [c["reason"] or c["check"] for c in s["checks"] if not c["ok"]]
        if bad:
            return "; ".join(bad)
    return ""


def _snippet(case: dict, n: int = 90) -> str:
    text = " ".join(case["samples"][0]["output"].split())
    text = text.replace("|", "\\|")
    return text[:n] + ("…" if len(text) > n else "")


def markdown(verdict: Verdict, baseline: dict, candidate: dict) -> str:
    b, c = baseline["meta"], candidate["meta"]
    icon = "PASS ✅" if verdict.passed else "FAIL ❌"
    lines = [f"## Prompt regression gate: {icon}", ""]
    if verdict.reasons:
        lines += [f"- {r}" for r in verdict.reasons] + [""]
    lines += [
        "| | Baseline | Candidate |", "|---|---|---|",
        f"| Prompt | `{b['prompt']}` ({b['prompt_sha']}) | `{c['prompt']}` ({c['prompt_sha']}) |",
        f"| Model | `{b['model']}` | `{c['model']}` |",
        f"| Pass rate | {verdict.baseline_rate:.1f}% | **{verdict.candidate_rate:.1f}%** |",
        "",
        f"Flipped cases: {len(verdict.lost)} lost, {len(verdict.gained)} gained. "
        f"McNemar exact p = {verdict.p_value:.3f} "
        f"({'unlikely to be noise' if verdict.p_value < 0.05 else 'could be noise'}).",
        "",
        "| Tag | Baseline | Candidate | Cases |", "|---|---|---|---|",
    ]
    for tag, (tb, tc, n) in verdict.tag_deltas.items():
        mark = " ⬇" if tc < tb else (" ⬆" if tc > tb else "")
        lines.append(f"| {tag} | {tb:.0f}% | {tc:.0f}%{mark} | {n} |")

    checks = sorted(set(baseline["summary"]["by_check"]) | set(candidate["summary"]["by_check"]))
    lines += ["", "| Check | Baseline | Candidate |", "|---|---|---|"]
    for name in checks:
        bv, cv = baseline["summary"]["by_check"].get(name), candidate["summary"]["by_check"].get(name)
        fmt = lambda v: "n/a" if v is None else f"{100 * v:.0f}%"
        lines.append(f"| {name} | {fmt(bv)} | {fmt(cv)} |")

    cand = {x["id"]: x for x in candidate["cases"]}
    if verdict.lost:
        lines += ["", "### Regressions (passed before, fail now)", "",
                  "| Case | Why it fails | Output |", "|---|---|---|"]
        for i in verdict.lost:
            crit = " (critical)" if cand[i].get("critical") else ""
            lines.append(f"| {i}{crit} | {_failures(cand[i])} | `{_snippet(cand[i])}` |")
    if verdict.gained:
        lines += ["", f"### Fixed (failed before, pass now): {', '.join(verdict.gained)}"]
    try:
        flaky = flaky_cases(candidate)
        if flaky:
            lines += ["", f"### Flaky in candidate (samples disagree): {', '.join(flaky)}"]
    except NotImplementedError:
        pass
    if verdict.missing or verdict.added:
        lines += ["", f"Cases only in baseline: {verdict.missing or 'none'}; only in candidate: {verdict.added or 'none'}."]
    return "\n".join(lines) + "\n"
