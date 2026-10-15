## Noise check: `ollama:llama3.2:1b`, `prompts/triage/v1.txt`, temperature 0.8

Pass rates over 6 identical runs: 20.0%, 20.0%, 35.0%, 35.0%, 25.0%, 35.0% (spread 15.0 points). 23 of 40 cases changed verdict at least once.

| Gate rule | False alarms (30 comparisons, prompt unchanged) |
|---|---|
| naive: any drop fails | 26/30 |
| drop > 5 pts + tag + critical (default) | 23/30 |
| default + McNemar p < 0.05 on drops | 21/30 |
| critical-case rule alone | 21/30 |
| McNemar-gated drops, no critical rule | 0/30 |
