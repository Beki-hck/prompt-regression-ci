"""Load a suite: a folder with suite.json (prompt path + checks) and cases.jsonl."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .checks import CHECKS


@dataclass
class Suite:
    name: str
    root: Path
    prompt_path: Path
    checks: list[dict]
    cases: list[dict]


def load_suite(path: str | Path, prompt: str | Path | None = None) -> Suite:
    root = Path(path)
    config = json.loads((root / "suite.json").read_text(encoding="utf-8"))
    cases = []
    for n, line in enumerate((root / config.get("cases", "cases.jsonl")).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        if "id" not in case:
            raise ValueError(f"case on line {n} has no id")
        cases.append(case)
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case ids")
    for spec in config["checks"]:
        if spec["type"] not in CHECKS:
            raise ValueError(f"unknown check type {spec['type']!r}")
    return Suite(config["name"], root, Path(prompt or config["prompt"]), config["checks"], cases)


def render(template: str, case: dict) -> str:
    """Fill {field} placeholders from the case. Plain replace, so JSON braces in prompts are safe."""
    out = template
    for key, value in case.items():
        if isinstance(value, str):
            out = out.replace("{" + key + "}", value)
    return out
