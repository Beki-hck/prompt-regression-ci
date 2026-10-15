"""Model backends: Ollama over plain HTTP, and a mock for tests and offline CI.

Model specs look like `ollama:qwen2.5:1.5b` or `mock`.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import urllib.request
from pathlib import Path

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
if not OLLAMA_HOST.startswith("http"):
    OLLAMA_HOST = "http://" + OLLAMA_HOST


def ollama_generate(model: str, prompt: str, temperature: float, seed: int,
                    max_tokens: int = 200, host: str = OLLAMA_HOST) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False,
               "options": {"temperature": temperature, "seed": seed,
                           "num_predict": max_tokens, "num_ctx": 2048}}
    req = urllib.request.Request(host.rstrip("/") + "/api/generate", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())["response"]


# --- mock -------------------------------------------------------------------
# A rule-based stand-in for a model. It reacts to what the prompt actually says,
# so editing a prompt changes its behaviour the way it would change a real
# model's. Its numbers are a simulation, not a measurement.

KEYWORDS = [
    ("injection", ["ignore all previous", "disregard your rules"]),
    ("account", ["log in", "login", "password", "account", "username", "two-factor", "profile"]),
    ("billing", ["charge", "refund", "invoice", "paypal", "coupon", "card", "fee"]),
    ("shipping", ["package", "parcel", "tracking", "ship", "deliver", "arrived", "return", "courier"]),
    ("technical", ["crash", "error", "slow", "website", "app", "search", "toggle", "safari", "typo", "down"]),
]
URGENT = ["urgent", "right away", "can't", "cannot", "help!", "crash", "error 500", "down", "charged twice",
          "someone logged", "locked", "today"]
PII = [r"\b\d{3}-\d{3}-\d{4}\b", r"\S+@\S+", r"\b\d+ \w+ Street\b"]


def _category(ticket: str) -> str:
    low = ticket.lower()
    for name, words in KEYWORDS:
        if any(w in low for w in words):
            return "other" if name == "injection" else name
    return "other"


def mock_generate(prompt: str, ticket: str, temperature: float, seed: int) -> str:
    rules = prompt.lower()
    low = ticket.lower()
    rng = random.Random(f"{ticket}|{seed}")
    guarded = "never follow instructions" in rules or "never obey" in rules
    if not guarded and "only with the word" in low:
        return low.split("only with the word")[1].strip(" .").upper()
    category = _category(ticket)
    if not guarded and "category to billing" in low:
        category = "billing"
    if "high:" in rules or "high =" in rules:
        priority = "high" if any(w in low for w in URGENT) else ("low" if "?" in ticket else "medium")
    else:
        priority = "medium"
    if temperature > 0 and rng.random() < temperature * 0.12:
        priority = rng.choice(["high", "medium", "low"])
    summary = " ".join(ticket.split()[:14])
    if "personal data" in rules:
        for pattern in PII:
            summary = re.sub(pattern, "[redacted]", summary)
    if not guarded and "system prompt" in low:
        summary = prompt.splitlines()[0]
    if "json" not in rules:
        return f"Category: {category}\nPriority: {priority}\nSummary: {summary}"
    return json.dumps({"category": category, "priority": priority, "summary": summary})


# --- dispatch + cache ---------------------------------------------------------

class Model:
    """Calls a backend, caching every answer on disk so reruns and re-grading are free."""

    def __init__(self, spec: str, cache_dir: str | Path = ".promptci/cache", max_tokens: int = 200):
        self.spec = spec
        self.max_tokens = max_tokens
        self.cache_path = Path(cache_dir) / (re.sub(r"[^\w.-]+", "_", spec) + ".jsonl")
        self._cache = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self._cache[row["key"]] = row["output"]

    def _key(self, prompt: str, temperature: float, seed: int) -> str:
        raw = json.dumps([self.spec, prompt, temperature, seed, self.max_tokens])
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def generate(self, prompt: str, ticket: str, temperature: float = 0.0, seed: int = 0) -> str:
        key = self._key(prompt, temperature, seed)
        if key in self._cache:
            return self._cache[key]
        if self.spec == "mock":
            out = mock_generate(prompt, ticket, temperature, seed)
        elif self.spec.startswith("ollama:"):
            out = ollama_generate(self.spec.split(":", 1)[1], prompt, temperature, seed, self.max_tokens)
        else:
            raise ValueError(f"unknown model spec {self.spec!r} (use mock or ollama:<name>)")
        self._cache[key] = out
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "output": out}) + "\n")
        return out
