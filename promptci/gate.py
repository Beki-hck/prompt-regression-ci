"""The gate: compare a candidate run with the pinned baseline and decide PASS or FAIL."""
from __future__ import annotations

from dataclasses import dataclass, field

from .stats import mcnemar_exact

MIN_TAG_CASES = 4  # tags with fewer cases are too small to judge on their own


@dataclass
class Rules:
    max_drop: float = 5.0          # overall pass rate may fall at most this many points
    tag_max_drop: float = 25.0     # same, per tag (category, injection, pii, ...)
    alpha: float = 0.05            # significance level for the McNemar test
    require_significance: bool = False  # only fail on a drop that is unlikely to be noise
    critical: bool = True          # a critical case going pass -> fail always fails the gate


@dataclass
class Verdict:
    passed: bool
    reasons: list[str]
    baseline_rate: float
    candidate_rate: float
    lost: list[str]
    gained: list[str]
    p_value: float
    tag_deltas: dict = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)


def flaky_cases(run: dict) -> list[str]:
    """Beki's feature: ids of cases whose samples disagree (some passed, some failed).

    A case with pass_rate strictly between 0 and 1 is flaky: the same prompt
    gave a different verdict on a rerun. Return their ids in the run's order.
    """
    raise NotImplementedError("Beki writes this one (see tests/test_flaky.py)")


def compare(baseline: dict, candidate: dict, rules: Rules | None = None) -> Verdict:
    rules = rules or Rules()
    base = {c["id"]: c for c in baseline["cases"]}
    cand = {c["id"]: c for c in candidate["cases"]}
    shared = [i for i in base if i in cand]
    lost = [i for i in shared if base[i]["passed"] and not cand[i]["passed"]]
    gained = [i for i in shared if not base[i]["passed"] and cand[i]["passed"]]
    p = mcnemar_exact(len(lost), len(gained))

    def pct(run, ids):
        return 100 * sum(run[i]["passed"] for i in ids) / len(ids) if ids else 0.0

    b_rate, c_rate = pct(base, shared), pct(cand, shared)
    noise_ok = rules.require_significance and p >= rules.alpha
    reasons = []

    if rules.critical:
        for i in lost:
            if base[i].get("critical"):
                reasons.append(f"critical case {i} regressed")
    drop = b_rate - c_rate
    if drop > rules.max_drop and not noise_ok:
        reasons.append(f"overall pass rate fell {drop:.1f} points ({b_rate:.1f}% -> {c_rate:.1f}%), "
                       f"limit {rules.max_drop:g}")

    tag_deltas = {}
    for tag in sorted({t for i in shared for t in base[i]["tags"]}):
        ids = [i for i in shared if tag in base[i]["tags"]]
        tb, tc = pct(base, ids), pct(cand, ids)
        tag_deltas[tag] = (tb, tc, len(ids))
        if len(ids) >= MIN_TAG_CASES and tb - tc > rules.tag_max_drop and not noise_ok:
            reasons.append(f"tag '{tag}' fell {tb - tc:.1f} points ({tb:.0f}% -> {tc:.0f}%)")

    return Verdict(passed=not reasons, reasons=reasons, baseline_rate=b_rate, candidate_rate=c_rate,
                   lost=lost, gained=gained, p_value=p, tag_deltas=tag_deltas,
                   missing=[i for i in base if i not in cand], added=[i for i in cand if i not in base])
