# LessonsAgent Usage Guide

## Environment Variables

| Variable | Description |
| --- | --- |
| `HOLISTIC_AI_TEAM_ID` | Team identifier for Holistic AI Bedrock proxy |
| `HOLISTIC_AI_API_TOKEN` | Token used by `tutorials/holistic_ai_bedrock.py` |
| `VALYU_API_KEY` | API key for Valyu.ai search |
| `VALYU_API_BASE_URL` | Optional override for Valyu base URL |

Load these via `.env` (see `env.example`) or your shell.

## CLI Commands

```bash
python -m lessons_agent.cli generate-lessons "Topic" \
  --level intermediate \
  --audience "Data scientists" \
  --num-lessons 3 \
  --estimated-duration 60 \
  --output-dir ./output/topic \
  [--mock-run] [--verbose]
```

- `--mock-run` generates deterministic content without hitting Valyu/Bedrock.
- `--verbose` enables detailed monitoring logs.

## Benchmarking

```bash
python scripts/benchmark_topics.py --output-dir ./benchmark_output
```

This script iterates over a small suite of topics and writes results for quick regression checks.

## Testing

```bash
python -m tests.test_monitoring
python -m tests.test_pipeline
python -m tests.test_cli
```

These suites provide coverage for monitoring hooks, pipeline orchestration, and CLI behavior.

