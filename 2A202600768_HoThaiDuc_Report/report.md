# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_mini.json
- Mode: real
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.74 | 0.94 | 0.2 |
| Avg attempts | 1 | 1.37 | 0.37 |
| Avg token estimate | 1696.55 | 3048.52 | 1351.97 |
| Avg latency (ms) | 3633.2 | 8443.27 | 4810.07 |

## Failure modes
```json
{
  "react": {
    "none": 74,
    "wrong_final_answer": 26
  },
  "reflexion": {
    "wrong_final_answer": 6,
    "none": 94
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.
