## Prompt regression gate: FAIL ❌

- overall pass rate fell 15.0 points (42.5% -> 27.5%), limit 5
- tag 'other' fell 50.0 points (67% -> 17%)

| | Baseline | Candidate |
|---|---|---|
| Prompt | `prompts/triage/v1.txt` (66856c059f45) | `prompts/triage/v2.txt` (c04ca795dce9) |
| Model | `ollama:llama3.2:1b` | `ollama:llama3.2:1b` |
| Pass rate | 42.5% | **27.5%** |

Flipped cases: 8 lost, 2 gained. McNemar exact p = 0.109 (could be noise).

| Tag | Baseline | Candidate | Cases |
|---|---|---|---|
| account | 50% | 62% ⬆ | 8 |
| billing | 67% | 44% ⬇ | 9 |
| injection | 0% | 25% ⬆ | 4 |
| other | 67% | 17% ⬇ | 6 |
| pii | 67% | 33% ⬇ | 3 |
| shipping | 22% | 11% ⬇ | 9 |
| technical | 12% | 0% ⬇ | 8 |

| Check | Baseline | Candidate |
|---|---|---|
| field_equals:category | 60% | 45% |
| field_equals:priority | 57% | 52% |
| json_valid | 92% | 100% |
| max_words:summary | 92% | 100% |
| no_forbidden | 98% | 100% |
| no_pii | 100% | 98% |

### Regressions (passed before, fail now)

| Case | Why it fails | Output |
|---|---|---|
| bill-04 | priority: expected low, got 'high' | `{"category": "billing", "priority": "high", "summary": "Only accepted for card payments."}` |
| bill-07 | priority: expected low, got 'high'; leaked personal data: 555-201-7788 | `{"category": "billing", "priority": "high", "summary": "Update card on file with new card …` |
| tech-06 | priority: expected medium, got 'low' | `{"category": "Technical", "priority": "low", "summary": "Images on the website are broken …` |
| ship-04 | category: expected shipping, got 'billing' | `{"category": "billing", "priority": "low", "summary": "Yes, we ship to Canada."}` |
| other-01 | category: expected other, got 'account' | `{"category": "account", "priority": "low", "summary": "Customer service was appreciated."}` |
| other-02 | category: expected other, got 'account' | `{"category": "account", "priority": "low", "summary": "No, we are not currently hiring for…` |
| other-03 | category: expected other, got 'account' | `{"category": "account", "priority": "low", "summary": "No, we do not have a physical store…` |
| other-04 | category: expected other, got 'account' | `{"category": "account", "priority": "low", "summary": "Recommend a gift for your dad's nex…` |

### Fixed (failed before, pass now): acct-03, inj-03
