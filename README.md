# LessonsAgent

> DeepResearch Lesson Agent that performs Valyu.ai-powered research and emits structured lesson JSON files.

## Features

- LangChain/ LangGraph ReAct agent with Valyu.ai search, HTTP fetch, and local resource ingestion.
- Pydantic-enforced lesson schema with structured output via Holistic AI Bedrock (Claude 3.5 Sonnet).
- CLI to generate lessons (mock or live) and write JSON bundles + index files.
- Monitoring hooks with structured logging, validation, and a benchmark script to sanity-check multiple topics.

## Prerequisites

- Python 3.12+
- Access tokens:
  - `HOLISTIC_AI_TEAM_ID`
  - `HOLISTIC_AI_API_TOKEN`
  - `VALYU_API_KEY`

## Local Setup

1. **Create & activate the venv**

   ```bash
   cd /Users/paverma/PersonalProjects/LessonsAgent
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt --index-url https://pypi.org/simple
   ```

3. **Configure environment variables**

   ```bash
   cp env.example .env
   # Edit .env with HOLISTIC_AI_TEAM_ID, HOLISTIC_AI_API_TOKEN, VALYU_API_KEY, VALYU_API_BASE_URL (optional)
   ```

4. **Verify imports**

   ```bash
   python -c "import langchain, pydantic; print('env ready')"
   ```

## CLI Usage

Mock run (no external API calls):

```bash
python -m lessons_agent.cli generate-lessons "LangChain Basics" \
  --level beginner \
  --num-lessons 1 \
  --output-dir ./output \
  --mock-run
```

Live run (requires env vars):

```bash
python -m lessons_agent.cli generate-lessons "RAG Best Practices" \
  --level intermediate \
  --num-lessons 2 \
  --output-dir ./output/live \
  --verbose
```

- `--verbose` enables detailed logging (monitoring events).
- Lesson JSON files plus an index file will be written to the target directory.

## Benchmark Script

Executes a small suite of built-in topics to validate the pipeline:

```bash
python scripts/benchmark_topics.py --output-dir ./benchmark_output
```

Logs for each topic are emitted via the monitoring helpers.

## Tests

Run the focused suites:

```bash
source .venv/bin/activate
python -m tests.test_monitoring
python -m tests.test_pipeline
python -m tests.test_cli
```

Or execute the full pytest suite if preferred.

## Project Structure

- `lessons_agent/agent.py` – ReAct research agent orchestration.
- `lessons_agent/pipeline.py` – Research + synthesis pipeline.
- `lessons_agent/tools.py` – Valyu search, HTTP fetch, document loaders.
- `lessons_agent/output.py` – JSON file writers and index.
- `lessons_agent/cli.py` – CLI entrypoint.
- `tests/` – Unit tests covering schemas, pipeline, CLI, monitoring.
