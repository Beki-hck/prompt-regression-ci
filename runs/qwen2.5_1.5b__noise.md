## Noise check: `ollama:qwen2.5:1.5b`, `prompts/triage/v1.txt`, temperature 0.8

Pass rates over 6 identical runs: 45.0%, 47.5%, 47.5%, 47.5%, 50.0%, 42.5% (spread 7.5 points). Cases flipped vs run 1: [3, 1, 1, 2, 1].

| Gate rule | False alarms (prompt unchanged) |
|---|---|
| naive: any drop > 0 points | 1/5 |
| threshold: drop > 5 points + critical cases | 0/5 |
| threshold + McNemar p < 0.05 | 0/5 |
