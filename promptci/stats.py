"""Small statistics helpers (standard library only)."""
from __future__ import annotations

import math


def mcnemar_exact(lost: int, gained: int) -> float:
    """Two-sided exact McNemar test on paired pass/fail results.

    `lost` = cases that passed before and fail now, `gained` = the reverse.
    Cases that stayed the same carry no information about a change. Under
    "nothing really changed", each flipped case is a coin toss, so the p-value
    is a two-sided binomial tail. Small p = unlikely to be noise.
    """
    n = lost + gained
    if n == 0:
        return 1.0
    k = min(lost, gained)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def wilson(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a pass rate."""
    if total == 0:
        return (0.0, 0.0)
    p = passed / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))
