"""Run a suite against one prompt + model and record every output and check."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .checks import grade
from .llm import Model
from .suite import Suite, render


def run_suite(suite: Suite, model: Model, samples: int = 1, temperature: float = 0.0,
              seed: int = 0, workers: int = 1, progress=None) -> dict:
    template = suite.prompt_path.read_text(encoding="utf-8")

    def one(case):
        prompt = render(template, case)
        outs = []
        for s in range(samples):
            try:
                output = model.generate(prompt, case.get("ticket", ""), temperature, seed + s)
                checks = grade(suite.checks, output, case)
            except Exception as exc:  # a failed call is a failed sample, not a crashed run
                output, checks = "", [{"check": "call", "ok": False, "reason": f"{type(exc).__name__}: {exc}"}]
            outs.append({"output": output, "passed": all(c["ok"] for c in checks), "checks": checks})
        if progress:
            progress(case["id"])
        passes = sum(o["passed"] for o in outs)
        return {"id": case["id"], "tags": case.get("tags", []), "critical": bool(case.get("critical")),
                "pass_rate": passes / samples, "passed": passes * 2 > samples, "samples": outs}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        cases = list(pool.map(one, suite.cases))
    return {
        "meta": {"suite": suite.name, "model": model.spec, "prompt": suite.prompt_path.as_posix(),
                 "prompt_sha": hashlib.sha256(template.encode()).hexdigest()[:12],
                 "samples": samples, "temperature": temperature, "seed": seed,
                 "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")},
        "summary": summarize(cases),
        "cases": cases,
    }


def summarize(cases: list[dict]) -> dict:
    """Pass rates overall, per tag and per check (a check's rate counts every sample)."""
    def rate(group):
        return {"passed": sum(c["passed"] for c in group), "total": len(group),
                "rate": round(sum(c["passed"] for c in group) / len(group), 4) if group else 0.0}

    tags = sorted({t for c in cases for t in c["tags"]})
    by_check = {}
    for c in cases:
        for s in c["samples"]:
            for chk in s["checks"]:
                row = by_check.setdefault(chk["check"], [0, 0])
                row[0] += chk["ok"]
                row[1] += 1
    return {"overall": rate(cases),
            "by_tag": {t: rate([c for c in cases if t in c["tags"]]) for t in tags},
            "by_check": {k: round(v[0] / v[1], 4) for k, v in sorted(by_check.items())}}


def save(run: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
