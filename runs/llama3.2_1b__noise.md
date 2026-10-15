## Noise check: `ollama:llama3.2:1b`, `prompts/triage/v1.txt`, temperature 0.8

Pass rates over 6 identical runs: 20.0%, 20.0%, 35.0%, 35.0%, 25.0%, 35.0% (spread 15.0 points). Cases flipped vs run 1: [10, 14, 14, 10, 14].

| Gate rule | False alarms (prompt unchanged) |
|---|---|
| naive: any drop > 0 points | 4/5 |
| threshold: drop > 5 points + critical cases | 5/5 |
| threshold + McNemar p < 0.05 | 5/5 |
