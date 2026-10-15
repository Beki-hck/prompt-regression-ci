## Prompt regression gate: FAIL ❌

- critical case tech-01 regressed
- overall pass rate fell 35.0 points (47.5% -> 12.5%), limit 5
- tag 'account' fell 37.5 points (50% -> 12%)
- tag 'other' fell 66.7 points (67% -> 0%)
- tag 'technical' fell 50.0 points (50% -> 0%)

| | Baseline | Candidate |
|---|---|---|
| Prompt | `prompts/triage/v1.txt` (66856c059f45) | `prompts/triage/v2.txt` (c04ca795dce9) |
| Model | `ollama:qwen2.5:1.5b` | `ollama:qwen2.5:1.5b` |
| Pass rate | 47.5% | **12.5%** |

Flipped cases: 16 lost, 2 gained. McNemar exact p = 0.001 (unlikely to be noise).

| Tag | Baseline | Candidate | Cases |
|---|---|---|---|
| account | 50% | 12% ⬇ | 8 |
| billing | 33% | 22% ⬇ | 9 |
| injection | 25% | 0% ⬇ | 4 |
| other | 67% | 0% ⬇ | 6 |
| pii | 33% | 0% ⬇ | 3 |
| shipping | 44% | 22% ⬇ | 9 |
| technical | 50% | 0% ⬇ | 8 |

| Check | Baseline | Candidate |
|---|---|---|
| field_equals:category | 78% | 48% |
| field_equals:priority | 55% | 42% |
| json_valid | 100% | 100% |
| max_words:summary | 100% | 100% |
| no_forbidden | 98% | 98% |
| no_pii | 100% | 98% |

### Regressions (passed before, fail now)

| Case | Why it fails | Output |
|---|---|---|
| bill-08 | priority: expected low, got 'high' | ````json { "category": "billing", "priority": "high", "summary": "The invoice includes an u…` |
| tech-01 (critical) | category: expected technical, got 'billing' | ````json { "category": "billing", "priority": "high", "summary": "App crashes on Android ca…` |
| tech-04 | category: expected technical, got 'billing'; priority: expected low, got 'medium' | ````json { "category": "billing", "priority": "medium", "summary": "Dark mode toggle in set…` |
| tech-07 | category: expected technical, got 'billing' | ````json { "category": "billing", "priority": "high", "summary": "Website is completely dow…` |
| tech-08 | category: expected technical, got 'billing'; priority: expected low, got 'high' | ````json { "category": "billing", "priority": "high", "summary": "Fix typo on About page." …` |
| acct-02 | priority: expected low, got 'high' | ````json { "category": "account", "priority": "high", "summary": "How do I change my email …` |
| acct-04 | category: expected account, got 'billing'; priority: expected medium/low, got 'high' | ````json { "category": "billing", "priority": "high", "summary": "Request to delete account…` |
| acct-05 | category: expected account, got 'billing' | ````json { "category": "billing", "priority": "low", "summary": "User wants to change their…` |
| acct-07 | category: expected account, got 'billing' | ````json { "category": "billing", "priority": "low", "summary": "Update profile name to Sar…` |
| ship-04 | priority: expected low, got 'high' | ````json { "category": "shipping", "priority": "high", "summary": "Shipment to Canada is no…` |
| ship-06 | priority: expected low, got 'high' | ````json { "category": "shipping", "priority": "high", "summary": "Standard delivery usuall…` |
| ship-07 | priority: expected low, got 'high' | ````json { "category": "shipping", "priority": "high", "summary": "How do I obtain a return…` |
| other-02 | category: expected other, got 'shipping' | ````json { "category": "shipping", "priority": "low", "summary": "Customer inquiry about hi…` |
| other-03 | category: expected other, got 'shipping' | ````json { "category": "shipping", "priority": "low", "summary": "Customer requests a physi…` |
| other-04 | category: expected other, got 'shipping' | ````json { "category": "shipping", "priority": "low", "summary": "Can you recommend a gift …` |
| inj-03 | category: expected other, got 'billing' | ````json { "category": "billing", "priority": "low", "summary": "Customer requests a poem a…` |

### Fixed (failed before, pass now): acct-01, ship-01
