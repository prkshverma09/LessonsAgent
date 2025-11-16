## Product Requirements Document (PRD): DeepResearch Lesson Agent

### 1. Overview

The **DeepResearch Lesson Agent** is an AI-powered research and content-generation system that, given a topic or query, performs deep research and produces **multi-section lesson plans** containing both **textual content and image assets**. The agent will be implemented using **LangChain's ReAct agent pattern**, powered by an **appropriate Amazon Bedrock LLM** accessed via the existing `HolisticAIBedrockChat` wrapper and the `HOLISTIC_AI_API_TOKEN`.

The system will run as a Python application in this repository, leveraging patterns from the existing tutorials:

- **`01_basic_agent.ipynb`**: base ReAct-style agent loop and prompt patterns.
- **`02_custom_tools.ipynb`**: defining and wiring custom tools for web research and file I/O.
- **`03_structured_output.ipynb`**: Pydantic-based structured output via `with_structured_output`.
- **`04_model_monitoring.ipynb`**: basic instrumentation and logging hooks.
- **`06_benchmark_evaluation.ipynb` / `07_reinforcement_learning.ipynb` / `08_attack_red_teaming.ipynb`**: optional evaluation, optimization, and safety hardening phases.

The **primary deliverable** is a set of **JSON lesson plan files** written to disk, each describing a coherent lesson (with sections, learning objectives, text content, and image prompts/URLs) derived from a deep research process on the input topic.

---

### 2. Project Goals

- **Deep research on arbitrary topics**: Given a topic or query, the agent should autonomously plan, search, read, and synthesize information from multiple sources (web pages, PDFs, etc.).
- **Pedagogically structured lesson plans**: Output should be structured into lessons and sections with objectives, prerequisite knowledge, key ideas, and activities.
- **Text and image content**: Each lesson can include both **textual explanations** and **image assets** (represented as prompts and/or URLs) appropriate for slides, handouts, or interactive materials.
- **Structured output as JSON**: All lesson plans must be emitted as **JSON files** following a well-defined schema, leveraging LangChain structured output with Pydantic models and the Holistic AI Bedrock `response_format` integration.
- **ReAct agent pattern**: Use **LangChain’s ReAct agent** pattern (reasoning traces + tool use) for research, not a simple single-call LLM.
- **Configurable depth and level**: Allow controlling depth (shallow vs deep), target learner level (e.g., beginner/intermediate/advanced), and number of lessons per topic.

---

### 3. Non-Goals

- **No full frontend UI**: The initial scope is a CLI/SDK-style Python tool; building a web UI is out of scope (can be added later).
- **No binary image generation pipeline**: The system will focus on **image prompts and URLs**; generating and storing actual image binaries is optional and out-of-scope for v1.
- **No multi-user workflow management**: Only single-user, single-run usage is targeted (no concurrency or user management).

---

### 4. Target Users and Use Cases

- **AI / LLM learners** following the tutorials who want a real project that integrates ReAct agents, tools, and structured output.
- **Educators and content creators** who need AI-generated lesson plans on new or niche topics.
- **Developers** who want a starting point for building curriculum-generation systems on top of Bedrock via Holistic AI.

**Primary use cases**:

- **U1: Single-topic lesson bundle**: User runs a CLI command with a topic (e.g., "Introduction to LangChain ReAct agents") and obtains 2–3 JSON lesson plans.
- **U2: Multi-level curriculum**: User specifies topic plus levels (beginner, intermediate) and gets separate sets of lessons for each level.
- **U3: Resource-aware plans**: User passes one or more local PDFs or URLs; the agent must prioritize these resources when constructing lessons.

---

### 5. Functional Requirements

- **FR1 – Topic intake**
  - Accept topic/query via CLI arguments or a Python function call.
  - Optional parameters: `target_level` (e.g., `"beginner" | "intermediate" | "advanced"`), `num_lessons`, `estimated_duration_minutes_per_lesson`, `output_dir`, `max_research_time`.

- **FR2 – Research planning (ReAct)**
  - Use a LangChain ReAct agent to:
    - Break the topic into subtopics and research questions.
    - Decide which tools to call (web search, page fetch, PDF loader).
    - Keep an explicit reasoning scratchpad (ReAct-style “Thought / Action / Observation”).

- **FR3 – Web and document research**
  - Implement tools for:
    - **Web search (Valyu.ai)**: use the **Valyu.ai** search API as the primary web search backend to return high-quality candidate URLs with snippets relevant to the topic and learner level.
    - **HTTP fetch**: download HTML / text from URLs.
    - **PDF/markdown loader**: load and chunk user-provided documents in `resources/` or via paths.
  - The agent should accumulate **research notes** with citations (URLs, doc identifiers).

- **FR4 – Lesson plan synthesis**
  - Use the Bedrock LLM (via `HolisticAIBedrockChat`) with **structured output** to:
    - Convert research notes into a set of lesson plans according to the JSON schema (see Section 7).
    - Guarantee valid JSON/typed output using the `with_structured_output` helper and Pydantic models.

- **FR5 – Text content generation**
  - For each lesson section:
    - Generate clear explanations, examples, and optional exercises.
    - Ensure progression from basic to more advanced concepts within or across lessons.

- **FR6 – Image prompt and asset generation**
  - For each relevant section:
    - Generate **image prompts** (and optionally suggested captions) describing visuals that would support the lesson.
    - Optionally, use a tool to:
      - Produce **image URLs** from a stock or generative image API (configurable and pluggable).
    - Store images as `{"type": "image", "prompt": "...", "caption": "...", "url": "... (optional)"}` blocks inside the JSON.

- **FR7 – JSON file output**
  - Write each lesson plan to a **separate JSON file** in `output_dir`:
    - File naming: `lesson_<topic_slug>_<level>_<index>.json`.
    - Ensure files validate against the defined Pydantic schema.

- **FR8 – Configuration and environment**
  - Read:
    - `HOLISTIC_AI_TEAM_ID` and `HOLISTIC_AI_API_TOKEN` from environment (or `.env`), and use `get_chat_model()` from `tutorials/holistic_ai_bedrock.py`.
  - Allow configuration via:
    - `.env` for API keys.
    - `pyproject.toml` / `config.yaml` for default settings (e.g., default model, temperature, search backend).

- **FR9 – Monitoring and logging**
  - Log:
    - All tool calls and high-level agent steps (without logging secrets).
    - Basic token usage estimates if available.
  - Align with the patterns used in `04_model_monitoring.ipynb`, keeping hooks for later evaluation.

- **FR10 – CLI interface**
  - Provide a CLI entry point, e.g.:
    - `python -m lessons_agent.generate --topic "Generative AI safety" --level beginner --num-lessons 3 --output-dir ./output`
  - Display progress (phases: planning, research, synthesis, writing).

---

### 6. Non-Functional Requirements

- **NFR1 – Reliability**
  - Recover gracefully from individual tool failures (e.g., bad URLs) and continue research with remaining sources.
  - Ensure JSON output is always valid or fail loudly with a clear error.

- **NFR2 – Performance**
  - Default to a reasonably fast, high-quality Bedrock model (e.g., `claude-3-5-sonnet` via Holistic AI).
  - Allow configuration of `temperature`, `max_tokens`, and timeouts.

- **NFR3 – Security**
  - Never log API tokens.
  - Only call configured external APIs; keep endpoints centralized in config.

- **NFR4 – Extensibility**
  - Make it easy to:
    - Add new tools (e.g., code repo search) without changing core agent logic.
    - Extend the lesson schema with additional fields (quizzes, assessments).

---

### 7. Data & JSON Schema (High-Level)

Implement the core schema using **Pydantic models** in a new module (e.g., `lessons_agent/schemas.py`), then use `with_structured_output` with `HolisticAIBedrockChat` to enforce it.

- **LessonPlan**
  - `topic: str`
  - `level: Literal["beginner", "intermediate", "advanced"]`
  - `estimated_duration_minutes: int`
  - `audience: str`
  - `learning_objectives: List[str]`
  - `prerequisites: List[str]`
  - `sections: List[LessonSection]`
  - `recommended_resources: List[ReferenceResource]`
  - `sources: List[SourceCitation]` (URLs/doc IDs used)

- **LessonSection**
  - `title: str`
  - `summary: str`
  - `key_points: List[str]`
  - `content_blocks: List[ContentBlock]`

- **ContentBlock** (discriminated union)
  - `type: Literal["text", "image"]`
  - `text: Optional[str]` (for `type="text"`)
  - `image_prompt: Optional[str]` (for `type="image"`)
  - `image_caption: Optional[str]`
  - `image_url: Optional[str]` (optional if integrated with an image API)

- **ReferenceResource**
  - `title: str`
  - `url: Optional[str]`
  - `type: Literal["article", "video", "paper", "book", "documentation", "other"]`

- **SourceCitation**
  - `source_id: str` (URL or local path)
  - `description: str`

The agent may generate **multiple `LessonPlan` objects per topic**; a top-level container model such as `LessonPlanBundle` (`topic`, `level`, `lessons: List[LessonPlan]`) can be used for one-shot generation of a bundle.

---

### 8. System Architecture & Components

- **8.1 High-Level Flow**
  1. **Input parsing**: Read CLI arguments / function parameters.
  2. **Agent configuration**: Instantiate Bedrock LLM via `get_chat_model("claude-3-5-sonnet")` and wrap in a ReAct agent with tools.
  3. **Planning phase (ReAct)**:
     - Agent decomposes topic into research tasks.
     - Selects tools and queries web search / loaders.
  4. **Research phase (ReAct loop)**:
     - Agent iteratively calls tools, inspects results, and builds up internal notes.
  5. **Synthesis phase (structured output)**:
     - A dedicated call to `llm.with_structured_output(LessonPlanBundle)` converts the summarized notes into lesson plans.
  6. **Persistence phase**:
     - Write each lesson as a separate JSON file to disk.
  7. **Reporting**:
     - Print a summary of generated lessons and output paths.

- **8.2 Modules (proposed)**
  - `lessons_agent/llm.py`
    - Wrapper around `get_chat_model()` from `tutorials/holistic_ai_bedrock.py`.
    - Convenience functions for creating base and structured-output models.
  - `lessons_agent/schemas.py`
    - Pydantic models for `LessonPlan`, `LessonSection`, etc.
  - `lessons_agent/tools.py`
    - Web search tool, HTTP fetch tool, PDF loader, optional image API tool.
    - Implemented following patterns from `02_custom_tools.ipynb`.
  - `lessons_agent/agent.py`
    - ReAct agent construction using LangChain (prompt templates, tools, agent executor).
    - System and human prompts tuned for research + pedagogy.
  - `lessons_agent/pipeline.py`
    - Orchestrates the full pipeline: plan → research → synthesize → write JSON.
  - `lessons_agent/cli.py`
    - CLI parsing and integration with `pipeline.py`.

- **8.3 LLM & Prompting**
  - **Base LLM**: `claude-3-5-sonnet` via `HolisticAIBedrockChat` (using `HOLISTIC_AI_API_TOKEN`).
  - **ReAct prompt**:
    - Follow the style from `01_basic_agent.ipynb`, with explicit Thought/Action/Observation markers.
  - **Structured output prompt**:
    - Teacher-facing instructions like: “You are an expert instructional designer; produce a JSON object matching the given schema.”

---

### 9. Risks and Mitigations

- **R1 – Hallucinated sources**
  - Mitigation: Enforce that all citations must come from actual tool outputs (URLs / docs); instruct the agent explicitly and validate URLs where possible.

- **R2 – Invalid JSON**
  - Mitigation: Use Pydantic and `with_structured_output` to enforce schema; if parsing fails, retry once with a stricter prompt.

- **R3 – Overly long or shallow lessons**
  - Mitigation: Include explicit constraints in prompts (target word count, depth, learner level) and allow user-configurable depth settings.

- **R4 – Tool/API failures**
  - Mitigation: Wrap tools with error handling and timeouts; have the agent fall back to fewer sources and report partial results.

---

### 10. Implementation Plan (Tasks)

#### Task 0 – Environment & Dependencies

- **T0.1**: Create/activate a Python virtual environment for this project.
- **T0.2**: Add a dependency file (`requirements.txt` or `pyproject.toml`) including at minimum:
  - `langchain`, `langchain-core`, `langchain-community`
  - `pydantic`
  - `python-dotenv`
  - `requests`
  - Any web search/PDF libraries selected (e.g., `tavily-python`, `pypdf`).
- **T0.3**: Ensure `.env` loading as in the tutorials, and set `HOLISTIC_AI_TEAM_ID` and `HOLISTIC_AI_API_TOKEN`.

- **Testing for Task 0**:
  - Run `python -c "import langchain, pydantic; print('ok')"` to confirm core dependencies import correctly.
  - Run a tiny script that loads `.env` and prints whether `HOLISTIC_AI_TEAM_ID` and `HOLISTIC_AI_API_TOKEN` are present (without printing actual values).

#### Task 1 – Schemas & Structured Output

- **T1.1**: Implement `LessonPlan`, `LessonSection`, `ContentBlock`, `ReferenceResource`, `SourceCitation`, and optional `LessonPlanBundle` in `lessons_agent/schemas.py`.
- **T1.2**: Add unit tests or a small test script to validate JSON serialization/deserialization of these models.
- **T1.3**: Implement a helper that returns `llm.with_structured_output(LessonPlanBundle)` using `get_chat_model()` from `holistic_ai_bedrock.py`, following `03_structured_output.ipynb`.

- **Testing for Task 1**:
  - Write a small script or test (e.g., `tests/test_schemas.py`) that:
    - Instantiates sample `LessonPlan` / `LessonPlanBundle` objects, serializes them to JSON, and deserializes back without errors.
    - Calls the structured-output helper with a trivial prompt (e.g., “Return an empty bundle for topic X”) and asserts that the returned object is a `LessonPlanBundle` instance.

#### Task 2 – LLM & Configuration Layer

- **T2.1**: Implement `lessons_agent/llm.py` to:
  - Wrap `get_chat_model(model_name="claude-3-5-sonnet")`.
  - Expose functions for base LLM and structured-output LLM.
- **T2.2**: Add configuration handling (model name, temperature, max tokens, timeouts) using environment variables or a config file.

- **Testing for Task 2**:
  - Run a small script (e.g., `scripts/test_llm.py`) that:
    - Imports `lessons_agent.llm`, obtains a chat model, and sends a simple prompt (like “say hello”) to verify a non-empty response.
    - Verifies that changing an environment variable (e.g., temperature) is reflected in the constructed model’s configuration.

#### Task 3 – Research Tools

- **T3.1**: Implement a **web search tool** backed by **Valyu.ai** as a LangChain `Tool`, inspired by `02_custom_tools.ipynb`, including configuration for the Valyu.ai API key and endpoint.
- **T3.2**: Implement an **HTTP fetch tool** that retrieves the text of a given URL, with basic cleaning.
- **T3.3**: Implement a **document loader tool** for local files (PDF/Markdown) under `resources/` or provided paths.
- **T3.4**: (Optional) Implement an **image generation or image search tool** that, given an image prompt, returns a URL or confirms generation.

- **Testing for Task 3**:
  - Create a script or test module (e.g., `tests/test_tools.py`) that:
    - Calls the Valyu.ai search tool with a simple query and asserts that it returns a non-empty list of results with titles/URLs.
    - Uses the HTTP fetch tool on a known URL and asserts the returned text is non-empty.
    - Uses the document loader on a sample file in `resources/` and checks that text or chunks are returned successfully.

#### Task 4 – ReAct Research Agent

- **T4.1**: Define ReAct-style prompts (system + human) that:
  - Emphasize careful research, citation tracking, and planning.
  - Instruct the agent to think step-by-step, using Thought/Action/Observation.
- **T4.2**: Create the ReAct agent using LangChain (e.g., `create_react_agent` or an equivalent pattern) with the tools from Task 3.
- **T4.3**: Implement an agent executor that:
  - Accepts topic and config.
  - Runs a bounded number of steps to gather enough information.
- **T4.4**: Implement a **research notes abstraction** (e.g., a Python dataclass or simple dict) that accumulates summaries, key points, and citations from the agent’s observations.

- **Testing for Task 4**:
  - Run a script (e.g., `scripts/test_agent_research.py`) that:
    - Invokes the ReAct agent on a simple topic (e.g., “What is LangChain?”) with a low step limit.
    - Asserts that research notes contain multiple key points and at least one citation (URL or document ID).
    - Confirms that the agent trace follows the Thought/Action/Observation pattern without runtime errors.

#### Task 5 – Lesson Synthesis Pipeline

- **T5.1**: Implement `lessons_agent/pipeline.py` that orchestrates:
  - Running the ReAct research agent to produce summarized notes.
  - Calling the structured-output LLM to convert notes → `LessonPlanBundle`.
- **T5.2**: Ensure the synthesis prompt includes the schema description and pedagogical requirements (learning objectives, progression, etc.).
- **T5.3**: Add validation: if Pydantic validation fails, retry with an adjusted prompt once and log the failure if it still fails.

- **Testing for Task 5**:
  - Run the pipeline for a small topic (e.g., “Basics of Python lists”) with `num_lessons=1`:
    - Assert that the pipeline returns a `LessonPlanBundle` instance with at least one lesson.
    - Verify that each lesson has non-empty `learning_objectives`, `sections`, and at least one `content_block`.

#### Task 6 – JSON Output & File Management

- **T6.1**: Implement utilities to slugify topic names and build output file paths.
- **T6.2**: Write each `LessonPlan` from the bundle to its own JSON file, and optionally produce an index file listing all generated lessons.
- **T6.3**: Add basic tests for output correctness (existence, JSON validity, schema compliance).

- **Testing for Task 6**:
  - Run a small end-to-end flow that produces a `LessonPlanBundle` and writes it to an `output/` directory:
    - Confirm that the directory contains one JSON file per lesson plus an index file if implemented.
    - Load each JSON file back into the `LessonPlan` schema to ensure it validates without errors.

#### Task 7 – CLI Interface

- **T7.1**: Implement `lessons_agent/cli.py` using `argparse` or `typer` for commands like:
  - `generate-lessons` with options (`--topic`, `--level`, `--num-lessons`, `--output-dir`, etc.).
- **T7.2**: Wire the CLI to the pipeline from Task 5.
- **T7.3**: Add helpful CLI output (progress messages, summary of generated files).

- **Testing for Task 7**:
  - From the command line, run a sample command such as:
    - `python -m lessons_agent.cli generate-lessons --topic "Test Topic" --level beginner --num-lessons 1 --output-dir ./output_test`
  - Verify that:
    - The CLI prints progress messages for research, synthesis, and writing.
    - The expected JSON files are created in `./output_test` and validate against the schema.

#### Task 8 – Monitoring, Evaluation, and Hardening

- **T8.1**: Add simple logging hooks (e.g., structured logs of tool calls and agent traces) consistent with `04_model_monitoring.ipynb`.
- **T8.2**: Create a small benchmark set (topics + expectations) and a script to generate lesson plans and inspect quality, inspired by `06_benchmark_evaluation.ipynb`.
- **T8.3**: Add safety-focused checks and prompt instructions to avoid harmful content, referencing ideas from `08_attack_red_teaming.ipynb`.

- **Testing for Task 8**:
  - Run the benchmark script on 2–3 predefined topics and:
    - Inspect logs to confirm that tool calls and agent steps are recorded as expected.
    - Review outputs for obvious safety issues and verify that safety prompts/guards behave as intended.

#### Task 9 – Documentation

- **T9.1**: Update the root `README.md` with:
  - A quickstart example.
  - Example output snippets (small JSON fragments).
- **T9.2**: Document configuration options (env vars, CLI flags) and pointers back to the tutorials for users who want to understand the internals.

- **Testing for Task 9**:
  - Follow the documented quickstart steps in `README.md` on a fresh environment:
    - Confirm that a new user can reproduce an end-to-end run from installation to lesson JSON generation using only the documented instructions.

---

### 11. Definition of Done

- A user can install dependencies, set Holistic AI environment variables, and run a CLI command to generate lesson plans for an arbitrary topic.
- The system performs tool-based research via a LangChain ReAct agent and logs its steps.
- The final output consists of one or more **valid JSON files** per run, each conforming to the `LessonPlan` schema, with both textual and image content blocks.
- Basic tests (schema validation, minimal E2E run) pass, and the project is documented in `README.md`.


