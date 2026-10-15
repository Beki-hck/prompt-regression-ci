## Prompt regression gate: PASS ✅

| | Baseline | Candidate |
|---|---|---|
| Prompt | `prompts/triage/v1.txt` (66856c059f45) | `prompts/triage/v3.txt` (bd777929322a) |
| Model | `ollama:qwen2.5:1.5b` | `ollama:qwen2.5:1.5b` |
| Pass rate | 47.5% | **50.0%** |

Flipped cases: 2 lost, 3 gained. McNemar exact p = 1.000 (could be noise).

| Tag | Baseline | Candidate | Cases |
|---|---|---|---|
| account | 50% | 50% | 8 |
| billing | 33% | 22% ⬇ | 9 |
| injection | 25% | 25% | 4 |
| other | 67% | 83% ⬆ | 6 |
| pii | 33% | 33% | 3 |
| shipping | 44% | 56% ⬆ | 9 |
| technical | 50% | 50% | 8 |

| Check | Baseline | Candidate |
|---|---|---|
| field_equals:category | 78% | 88% |
| field_equals:priority | 55% | 57% |
| json_valid | 100% | 100% |
| max_words:summary | 100% | 100% |
| no_forbidden | 98% | 100% |
| no_pii | 100% | 100% |

### Regressions (passed before, fail now)

| Case | Why it fails | Output |
|---|---|---|
| bill-08 | priority: expected low, got 'high' | `{"category":"billing","priority":"high","summary":"Service fee not mentioned in invoice."}` |
| tech-04 | category: expected technical, got 'account' | `{"category":"account","priority":"low","summary":"Dark mode setting not remembered in sett…` |

### Fixed (failed before, pass now): tech-03, ship-01, other-01
