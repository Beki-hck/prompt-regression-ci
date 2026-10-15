## Noise check: `ollama:qwen2.5:1.5b`, `prompts/triage/v1.txt`, temperature 0.8

Pass rates over 6 identical runs: 45.0%, 47.5%, 47.5%, 47.5%, 50.0%, 42.5% (spread 7.5 points). 4 of 40 cases changed verdict at least once.

| Gate rule | False alarms (30 comparisons, prompt unchanged) |
|---|---|
| naive: any drop fails | 17/30 |
| drop > 5 pts + tag + critical (default) | 15/30 |
| default + McNemar p < 0.05 on drops | 15/30 |
| critical-case rule alone | 15/30 |
| McNemar-gated drops, no critical rule | 0/30 |
