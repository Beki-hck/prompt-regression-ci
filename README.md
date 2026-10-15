# prompt-regression-ci

![tests](https://github.com/Beki-hck/prompt-regression-ci/actions/workflows/tests.yml/badge.svg)
![llm-gate](https://github.com/Beki-hck/prompt-regression-ci/actions/workflows/llm-gate.yml/badge.svg)
![deps](https://img.shields.io/badge/dependencies-none-brightgreen)

Unit tests for prompts. When someone edits a prompt or swaps the model, this tool reruns a golden set of test cases, compares the results with a pinned baseline, and **fails the pull request if quality dropped**. The report says which cases broke and why.

```
$ promptci check -b baselines/triage__mock.json --prompt prompts/triage/v2.txt
## Prompt regression gate: FAIL ❌
- critical case bill-01 regressed
- overall pass rate fell 42.5 points (65.0% -> 22.5%), limit 5
...
```

## Why I built it

Prompts are code, but they rarely get tested like code. A "harmless" edit that shortens a prompt can quietly stop a model from following a rule, and nobody notices until users do. In software QA you catch that with regression tests in CI; this project does the same for LLM behaviour, and adds the part normal tests don't need: **telling a real regression apart from the model's random noise.**

## How it works

```
prompts/triage/v1.txt ─┐
suites/triage/cases.jsonl (40 golden cases) ─┼─► promptci run ─► run.json ─┐
model (ollama:* or mock) ─┘                                              ├─► promptci gate ─► PASS / FAIL + report.md
baselines/triage__<model>.json (pinned, reviewed, committed) ────────────┘
```

1. **Golden set** (`suites/triage/cases.jsonl`): 40 support tickets with the expected category and priority. Tags group them (billing, shipping, ..., `injection`, `pii`); 8 are marked `critical`.
2. **Checks** (`promptci/checks.py`): deterministic rules, no LLM judge, so the same output always gets the same verdict: valid JSON, category and priority match, summary at most 25 words, no personal data copied, no obeying instructions hidden in the ticket.
3. **Baseline**: a run someone reviewed and committed (`promptci bless`). It pins the numbers the next change is judged against.
4. **Gate** (`promptci/gate.py`) fails when
   - any **critical** case goes from pass to fail,
   - the overall pass rate drops more than **5 points**, or
   - a tag with at least 4 cases drops more than **25 points**.
   With `--require-significance`, a drop only counts if an exact **McNemar test** on the flipped cases says it is unlikely to be noise (p < 0.05).
5. **CI**: `tests.yml` runs the unit tests and the gate with the mock model on every push. `llm-gate.yml` installs Ollama on the GitHub runner, pulls a small open model and gates every pull request that touches `prompts/` or `suites/`, posting the report as the job summary.

Three prompt versions are included to show the gate working: `v1` (the baseline), `v2` (a "shorter" prompt that drops the priority rules and the injection guard) and `v3` (the same rules reworded, which should pass).

## Results

<!-- results:start -->
Mock model only so far (a rule-based simulator that reacts to prompt wording; its numbers demonstrate the tool, they measure nothing). Real-model numbers from the GitHub runner are coming.

| Prompt | Pass rate (mock) | Gate vs v1 |
|---|---|---|
| v1 baseline | 65.0% (26/40) | |
| v2 shortened | 22.5% (9/40) | FAIL: 6 critical regressions, p < 0.001 |
| v3 reworded | 65.0% (26/40) | PASS |
<!-- results:end -->

## Quick start

```bash
git clone https://github.com/Beki-hck/prompt-regression-ci
cd prompt-regression-ci
pip install -e .

promptci run -o runs/v1.json                                   # mock model, default prompt
promptci check -b runs/v1.json --prompt prompts/triage/v2.txt  # exits 1: regression

# with a real local model (install Ollama first, then: ollama pull qwen2.5:1.5b)
promptci run -m ollama:qwen2.5:1.5b -o runs/qwen_v1.json
promptci check -b runs/qwen_v1.json -m ollama:qwen2.5:1.5b --prompt prompts/triage/v3.txt

# how often would each gate rule raise a false alarm on an UNCHANGED prompt?
promptci noise -m ollama:qwen2.5:1.5b --temperature 0.8 --runs 6
```

| File | Purpose |
|---|---|
| `promptci/suite.py` | Loads `suite.json` + `cases.jsonl`, fills `{ticket}` into the prompt |
| `promptci/llm.py` | Ollama over plain HTTP, the mock model, on-disk answer cache |
| `promptci/checks.py` | The deterministic checks |
| `promptci/run.py` | Runs every case (optionally several samples, majority vote) and summarizes |
| `promptci/stats.py` | Exact McNemar test and Wilson interval |
| `promptci/gate.py` | The PASS/FAIL rules |
| `promptci/report.py` | Markdown report for the PR / job summary |
| `promptci/cli.py` | `run`, `gate`, `check`, `bless`, `noise` |

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

Standard library only. Tests cover every check, the McNemar maths, the gate rules, the cache, failed model calls, the CLI exit codes and the Ollama client against a fake HTTP server. One test is skipped on purpose: `gate.flaky_cases` is mine to write.

## License

MIT
