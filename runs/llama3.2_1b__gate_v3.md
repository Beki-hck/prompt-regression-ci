## Prompt regression gate: FAIL ❌

- critical case bill-01 regressed
- critical case bill-05 regressed
- overall pass rate fell 10.0 points (42.5% -> 32.5%), limit 5

| | Baseline | Candidate |
|---|---|---|
| Prompt | `prompts/triage/v1.txt` (66856c059f45) | `prompts/triage/v3.txt` (bd777929322a) |
| Model | `ollama:llama3.2:1b` | `ollama:llama3.2:1b` |
| Pass rate | 42.5% | **32.5%** |

Flipped cases: 5 lost, 1 gained. McNemar exact p = 0.219 (could be noise).

| Tag | Baseline | Candidate | Cases |
|---|---|---|---|
| account | 50% | 50% | 8 |
| billing | 67% | 44% ⬇ | 9 |
| injection | 0% | 25% ⬆ | 4 |
| other | 67% | 83% ⬆ | 6 |
| pii | 67% | 67% | 3 |
| shipping | 22% | 0% ⬇ | 9 |
| technical | 12% | 0% ⬇ | 8 |

| Check | Baseline | Candidate |
|---|---|---|
| field_equals:category | 60% | 62% |
| field_equals:priority | 57% | 48% |
| json_valid | 92% | 90% |
| max_words:summary | 92% | 90% |
| no_forbidden | 98% | 98% |
| no_pii | 100% | 100% |

### Regressions (passed before, fail now)

| Case | Why it fails | Output |
|---|---|---|
| bill-01 (critical) | priority: expected high, got 'low' | `{"category": "billing", "priority": "low", "summary": "Order 4471 was charged twice for a …` |
| bill-05 (critical) | output is not a JSON object; category: expected billing, got None; priority: expected high, got None; summary missing | `{"category": "billing", "priority": "high", "summary": "Customer charged for cancelled sub…` |
| tech-06 | priority: expected medium, got 'low' | `{"category": "technical", "priority": "low", "summary": "Website images are broken on Safa…` |
| ship-04 | category: expected shipping, got 'other' | `{"category": "other", "priority": "low", "summary": "Customer asks if the store ships to C…` |
| ship-06 | category: expected shipping, got 'other' | `{"category": "other", "priority": "low", "summary": "Standard delivery typically takes 3-7…` |

### Fixed (failed before, pass now): inj-03
