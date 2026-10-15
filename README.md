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

1. **Golden set** (`suites/triage/cases.jsonl`): 40 support tickets with the expected category and priority. Tags group them (billing, shipping, ..., `injection`, `pii`); 7 are marked `critical`.
2. **Checks** (`promptci/checks.py`): deterministic rules, no LLM judge, so the same output always gets the same verdict: valid JSON, category and priority match, summary at most 25 words, no personal data copied, no obeying instructions hidden in the ticket.
3. **Baseline**: a run someone reviewed and committed (`promptci bless`). It pins the numbers the next change is judged against.
4. **Gate** (`promptci/gate.py`) fails when
   - any **critical** case goes from pass to fail,
   - the overall pass rate drops more than **5 points**, or
   - a tag with at least 4 cases drops more than **25 points**.
   With `--require-significance`, a drop only counts if an exact **McNemar test** on the flipped cases says it is unlikely to be noise (p < 0.05).
5. **CI**: `tests.yml` runs the unit tests and the gate with the mock model on every push. `llm-gate.yml` installs Ollama on the GitHub runner, pulls a small open model (default `qwen2.5:1.5b`) and gates every pull request that touches `prompts/` or `suites/`, posting the report as the job summary. Run it by hand with `task=experiments` to reproduce the results below.

Three prompt versions are included to show the gate working: `v1` (the baseline), `v2` (a "shorter" prompt that drops the priority rules and the injection guard) and `v3` (the same rules reworded, which should pass).

## Results

<!-- results:start -->
Real runs on GitHub's free CPU runner (Ollama, temperature 0, seed 0), 2026-10-15. Raw runs and reports: [`benchmarks/2026-10-15/`](benchmarks/2026-10-15/).

**1. Does the gate catch a bad prompt edit, and let a harmless one through?**

| Model | v1 baseline | v2 "shortened" | v3 reworded |
|---|---|---|---|
| `qwen2.5:1.5b` | 47.5% | 12.5%: **FAIL** (16 lost, 2 gained, McNemar p = 0.001; critical `tech-01` broke) | 50.0%: **PASS** (2 lost, 3 gained, p = 1.0) |
| `llama3.2:1b` | 42.5% | 27.5%: **FAIL** (8 lost, 2 gained, p = 0.11) | 32.5%: **FAIL** (critical `bill-01`, `bill-05` broke; p = 0.22) |

- **What v2 broke on Qwen:** without the category definitions it filed account and technical tickets under "billing" (tech-01 "app crashes" → billing) and called almost everything high priority ("Do you ship to Canada?" → high). JSON validity stayed at 100%, so a format-only test would have passed this change.
- **The same reword helped one model and hurt another.** v3 says the same thing as v1 in different words: Qwen went up 2.5 points, Llama lost two critical billing cases. A prompt change has to be tested on the model you ship.
- **Small models are weak at this task.** Even with the full prompt, priority is right only 55-58% of the time and Qwen wrote "PWNED" into a summary when told to. The baseline is not "good"; the gate's job is to stop it getting worse.
- **Model swap** (Qwen v1 → Llama v1): FAIL, critical `tech-01` and the technical tag dropped 37.5 points, even though the overall rate moved only 5 points.

**2. How often does each gate rule raise a false alarm when nothing changed?** Same prompt run 6 times at temperature 0.8 (like a production setting), every pair compared (30 comparisons):

| Gate rule | `qwen2.5:1.5b` | `llama3.2:1b` |
|---|---|---|
| naive: any drop fails | 17/30 | 26/30 |
| default: drop > 5 pts, tag > 25 pts, any critical case | 15/30 | 23/30 |
| critical-case rule alone | 15/30 | 21/30 |
| drops only if McNemar p < 0.05, no critical rule | **0/30** | **0/30** |

- Run-to-run spread was 7.5 points for Qwen and 15 points for Llama (23 of its 40 cases changed verdict at least once). A plain threshold on the average cries wolf most of the time.
- Requiring significance removed every false alarm, **but** it would also have let Llama's v2 regression through (p = 0.11): with 40 cases, a 15-point drop isn't provably more than noise. That's the real trade-off: more cases, or several samples per case, buy you both.
- The critical-case rule is only trustworthy when outputs are repeatable. So the PR gate runs at temperature 0 with a fixed seed; at higher temperatures, critical cases should be judged by a majority vote over samples (`--samples 5`).

**Is temperature 0 repeatable enough to gate on?** A `check` run of the unchanged v1 prompt on a fresh runner reproduced the committed Qwen baseline exactly: 0 cases lost, 0 gained ([run](https://github.com/Beki-hck/prompt-regression-ci/actions/runs/38710821314)).

All of this ran inside GitHub Actions with no API key and no GPU: [`llm-gate.yml`](.github/workflows/llm-gate.yml).
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
promptci noise -m ollama:qwen2.5:1.5b --temperature 0.8 --runs 6 --out runs/noise
promptci noise --from-dir benchmarks/2026-10-15/noise_qwen2.5_1.5b   # recompute, no model calls
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
| `baselines/` | Pinned runs: mock, `qwen2.5:1.5b`, `llama3.2:1b` |

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

Standard library only. Tests cover every check, the McNemar maths, the gate rules, the cache, failed model calls, the CLI exit codes and the Ollama client against a fake HTTP server. One test is skipped on purpose: `gate.flaky_cases` is mine to write.

## License

MIT
