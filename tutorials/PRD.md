# **Product Requirements Document (PRD): Autonomous Agentic Web Testing Swarm**

### **1. Overview**

This document outlines the requirements for an autonomous web testing system, "AgenticTest," built for a hackathon. The system will leverage a multi-agent architecture orchestrated by LangGraph to autonomously discover, plan, and execute tests on any given website. The primary goal is speed of implementation and extensibility, achieved by integrating specialized, high-level APIs for web crawling (FireCrawl) and browser automation (Browser Use).

### **2. Project Goal**

To create a "plan-and-execute" agentic system that accepts a single URL, autonomously discovers all testable pages, generates a comprehensive suite of tests (including broken link checks and user flow validation), executes these tests in parallel, and provides a consolidated report of all findings.

### **3. Core Technologies**

  * **Orchestration:** LangGraph (Python).
  * **Agentic Components:** LangChain (for prompts, LLMs, and tool definitions).
  * **URL Discovery (Scoping):** FireCrawl (`firecrawl-py`).
  * **Browser Execution (Testing):** Browser Use (`browser-use`).
  * **Model:** OpenAI (e.g., GPT-4o) or another high-capacity, tool-calling model.

### **4. System Architecture: The 5-Phase Flow**

The system will be implemented as a single, stateful LangGraph graph representing a "Test Coordinator" agent. This agent manages a five-phase workflow:

1.  **Phase 1: Scope:** The agent accepts a target URL. It uses a **FireCrawl** tool to map the entire website and discover all crawlable URLs.
2.  **Phase 2: Plan:** The agent iterates through the discovered URLs. For each URL, it uses a **FireCrawl** tool to scrape its content (markdown and links). It then uses an LLM to analyze this content and generate a list of "Test Plans" (e.g., "Verify all links on page X," "Test the login form on page Y with invalid credentials").
3.  **Phase 3: Dispatch (Fan-Out):** The agent takes the complete list of test plans and dispatches them for parallel execution using LangGraph's "fan-out" capability.
4.  **Phase 4: Execute:** Each test plan is sent to a parallel worker. This worker's *only* job is to make a single, high-level API call to the **Browser Use** service, passing the test plan as a natural language task (e.g., "Go to /login, fill username with 'user', fill password with 'pass', click 'submit', and verify 'Welcome' text is visible").
5.  **Phase 5: Aggregate (Fan-In):** The agent waits for all parallel workers to complete. It collects the pass/fail results from all `browser-use` executions and uses an LLM to synthesize a final, human-readable bug report.

### **5. Core Agent: `TestCoordinator`**

The system's core is a single, custom `StateGraph`, not the `langgraph.prebuilt.create_react_agent`. The prebuilt agent is designed for simple message-based state, whereas this project requires a complex, custom state to track URL maps, test plans, and aggregated results.

The agent's state will be defined using a `TypedDict` and must include a key for collecting parallel results safely.

### **6. Key Functionalities**

  * **Broken Link Detection:** The "Plan" phase must explicitly generate test plans to check every link discovered on every page.
  * **User Flow Testing:** The "Plan" phase must analyze page content (e.g., forms, buttons) and generate test plans for both "happy path" (e.g., successful login) and "negative" (e.g., failed login) scenarios.
  * **Parallel Execution:** The system must execute all generated test plans concurrently to ensure speed.
  * **Consolidated Reporting:** The final output must be a single report summarizing all test plans, their status (Pass/Fail), and any errors encountered.

### **7. Extensibility (Future-Proofing)**

The architecture must be extensible. Adding new test types (e.g., basic security checks, accessibility scans) should be as simple as:

1.  Updating the "Planner" agent's prompt to generate new types of test plans.
2.  Ensuring the `browser-use` agent can understand these new high-level tasks.

-----

## **Implementation Plan for Coding Agent**

Follow these tasks sequentially to build the "AgenticTest" system.

### **Task 0: Environment Setup**

1.  Create a new project directory and a Python virtual environment.
2.  Install all required libraries:bash
    pip install "langgraph" "langchain" "langchain-openai" "firecrawl-py" "browser-use"
    ```
    ```
3.  Create a `.env` file and add your API keys:
    ```
    OPENAI_API_KEY="sk-..."
    FIRECRAWL_API_KEY="fc-..."
    BROWSER_USE_API_KEY="bu_..."
    ```
4.  Load these environment variables at the start of your main script.

### **Task 1: Define Graph State (`state.py`)**

Create a file `state.py`. Define the `StateGraph`'s state using `TypedDict`. This state will be used to pass information between all nodes.

```python
import operator
from typing import TypedDict, Annotated, List, Dict, Any

class TestCoordinatorState(TypedDict):
    """
    The global state for the test coordinator agent.
    """
    target_url: str                # The initial URL to test
    url_map: List]  # List of all URLs found by Firecrawl
    test_plans: List] # List of all test plans generated by the LLM

    # This key is critical for parallel execution (fan-in)
    # It uses a reducer to safely append results from parallel workers
    results: Annotated], operator.add]

    final_report: str              # The final summary report
```

### **Task 2: Define Agent Tools (`tools.py`)**

Create a file `tools.py`. This file will contain all the external services our agent can call, wrapped as `langchain_core.tools.tool`.

```python
import os
from langchain_core.tools import tool
from firecrawl import Firecrawl
from browser_use import Agent as BrowserUseAgent, Browser, ChatBrowserUse
import asyncio

# Initialize API clients
firecrawl_client = Firecrawl(api_key=os.environ.get("FIRECRAWL_API_KEY"))
browser_use_llm = ChatBrowserUse() # Uses BROWSER_USE_API_KEY from env

@tool
def tool_discover_site_urls(url: str) -> dict:
    """
    Discovers all URLs on a given website.
    Input: a single URL string.
    Output: A dictionary containing a 'links' key with a list of URL objects.
    """
    try:
        # Use Firecrawl's map endpoint for fast URL discovery
        res = firecrawl_client.map(url=url, sitemap="include", limit=50)
        return {"links": res}
    except Exception as e:
        return {"error": f"Error discovering URLs: {str(e)}"}

@tool
def tool_get_page_content(url: str) -> dict:
    """
    Scrapes a single URL for its markdown content and all outgoing links.
    Input: a single URL string.
    Output: A dictionary with 'markdown' and 'links' keys.
    """
    try:
        # Use Firecrawl's scrape endpoint
        res = firecrawl_client.scrape(url=url, formats=['markdown', 'links'])
        return {"markdown": res.markdown, "links": res.links}
    except Exception as e:
        return {"error": f"Error scraping page {url}: {str(e)}"}

@tool
async def tool_execute_test_plan(test_plan_prompt: str, url: str) -> dict:
    """
    Executes a single, high-level test plan using the browser-use agent.
    Input: a natural language 'test_plan_prompt' and the 'url' to test.
    Output: A dictionary with the test result.
    """
    try:
        # This is the hackathon shortcut.
        # We use browser-use to handle all browser automation.
        browser = Browser(use_cloud=True) # Use managed cloud browsers
        agent = BrowserUseAgent(
            task=test_plan_prompt,
            llm=browser_use_llm,
            browser=browser,
            start_url=url
        )
        history = await agent.run()

        # Get the final observation from the browser agent
        final_result = history[-1].observation if history else "No result"

        # Simplified pass/fail logic for the report
        status = "PASS"
        if "error" in str(final_result).lower() or "fail" in str(final_result).lower():
            status = "FAIL"

        return {
            "plan": test_plan_prompt,
            "status": status,
            "result": str(final_result)
        }
    except Exception as e:
        return {
            "plan": test_plan_prompt,
            "status": "FAIL",
            "result": f"Critical execution error: {str(e)}"
        }
```

### **Task 3: Define Prompts (`prompts.py`)**

Create a file `prompts.py`. This holds the "brains" of our agent.

```python
from langchain_core.prompts import ChatPromptTemplate

PLANNER_PROMPT = ChatPromptTemplate.from_messages(
"""),
    ("human", "URL: {url}\n\nMARKDOWN:\n{markdown}\n\nLINKS:\n{links}")
])

REPORTER_PROMPT = ChatPromptTemplate.from_messages()
```

### **Task 4: Define Graph Nodes (`graph_nodes.py`)**

Create a file `graph_nodes.py`. These are the Python functions that will be the nodes in our `StateGraph`.

```python
import json
from langchain_openai import ChatOpenAI
from state import TestCoordinatorState
from tools import tool_discover_site_urls, tool_get_page_content, tool_execute_test_plan
from prompts import PLANNER_PROMPT, REPORTER_PROMPT
from langgraph.graph import Send

# Initialize the LLM for planning and reporting
llm = ChatOpenAI(model="gpt-4o", temperature=0)
planner_agent = PLANNER_PROMPT | llm
reporter_agent = REPORTER_PROMPT | llm

def node_discover_urls(state: TestCoordinatorState):
    """Node 1: Discover all URLs for the target website."""
    print("--- PHASE 1: DISCOVERING URLS ---")
    url = state['target_url']
    result = tool_discover_site_urls.invoke({"url": url})
    if "error" in result:
        print(f"Error: {result['error']}")
        return {"results":}]}

    url_map = result.get('links',)
    print(f"Discovered {len(url_map)} URLs.")
    return {"url_map": url_map}

def node_generate_test_plans(state: TestCoordinatorState):
    """Node 2: Generate test plans for each discovered URL."""
    print("--- PHASE 2: GENERATING TEST PLANS ---")
    url_map = state['url_map']
    all_test_plans =

    for page in url_map:
        url = page.get('url')
        if not url:
            continue

        print(f"Planning tests for: {url}")
        content_result = tool_get_page_content.invoke({"url": url})
        if "error" in content_result:
            all_test_plans.append({"url": url, "plan": f"Verify page is accessible. Result: {content_result['error']}"})
            continue

        markdown = content_result.get('markdown', '')
        links = content_result.get('links',)

        # Truncate for token limits
        markdown_snippet = markdown[:4000]

        try:
            response = planner_agent.invoke({
                "url": url,
                "markdown": markdown_snippet,
                "links": links
            })
            plans = json.loads(response.content)
            all_test_plans.extend(plans)
        except Exception as e:
            print(f"Error generating plans for {url}: {str(e)}")

    print(f"Generated {len(all_test_plans)} total test plans.")
    return {"test_plans": all_test_plans}

def node_dispatch_tests(state: TestCoordinatorState):
    """
    Node 3: Dispatch all test plans to parallel workers (Fan-Out).
    This node returns a list of Send objects, which LangGraph
    will execute in parallel.
    """
    print("--- PHASE 3: DISPATCHING TESTS ---")
    test_plans = state['test_plans']

    # Create a list of tasks for the worker node
    worker_tasks =
    for plan in test_plans:
        # Each 'Send' targets the 'execute_worker' node with a specific payload
        task_payload = {"url": plan['url'], "plan": plan['plan']}
        worker_tasks.append(Send(to="execute_worker", arg=task_payload))

    print(f"Dispatching {len(worker_tasks)} tests to parallel workers.")
    return worker_tasks

async def node_execute_test(props: dict):
    """
    Node 4: The Worker Node. Executes one test plan.
    This node will be run in parallel for every task dispatched.
    """
    url = props['url']
    plan = props['plan']
    print(f"--- EXECUTING --- \nURL: {url}\nPlan: {plan}")

    # Use the async version of the tool
    result = await tool_execute_test_plan.ainvoke({"test_plan_prompt": plan, "url": url})

    print(f"--- COMPLETE --- \nURL: {url}\nStatus: {result['status']}")
    # The return value will be aggregated in the 'results' state key
    # (due to the `operator.add` reducer)
    return {"results": [result]}

def node_compile_report(state: TestCoordinatorState):
    """Node 5: Compile the final report (Fan-In)."""
    print("--- PHASE 5: COMPILING REPORT ---")
    results = state['results']

    response = reporter_agent.invoke({"results": json.dumps(results, indent=2)})
    report = response.content

    print("\n--- --- ---")
    print("--- FINAL TEST REPORT ---")
    print(report)
    print("--- --- ---")
    return {"final_report": report}
```

### **Task 5: Build and Run the Graph (`main.py`)**

Create a file `main.py`. This file assembles and runs the LangGraph workflow.

```python
import asyncio
from langgraph.graph import StateGraph, START, END
from state import TestCoordinatorState
from graph_nodes import (
    node_discover_urls,
    node_generate_test_plans,
    node_dispatch_tests,
    node_execute_test,
    node_compile_report
)

# 1. Initialize the StateGraph
builder = StateGraph(TestCoordinatorState)

# 2. Add all the nodes
builder.add_node("discover", node_discover_urls)
builder.add_node("plan", node_generate_test_plans)
builder.add_node("dispatch", node_dispatch_tests)
builder.add_node("execute_worker", node_execute_test)
builder.add_node("compile_report", node_compile_report)

# 3. Define the graph edges (the workflow)
builder.add_edge(START, "discover")
builder.add_edge("discover", "plan")
builder.add_edge("plan", "dispatch")

# This is the parallel fan-out. 'dispatch' sends tasks to 'execute_worker'
builder.add_edge("dispatch", "execute_worker")

# This is the parallel fan-in. After *all* 'execute_worker' tasks are
# done, it proceeds to 'compile_report'.
builder.add_edge("execute_worker", "compile_report")

builder.add_edge("compile_report", END)

# 4. Compile the graph
app = builder.compile()

# 5. Run the agent
async def run_test():
    target_url = "[https://www.firecrawl.dev](https://www.firecrawl.dev)" # <-- Change this to your target URL

    # Use 'astream' to run the graph asynchronously
    async for step in app.astream(
        {"target_url": target_url, "results":},
        # Set max_concurrency for parallel execution
        config={"max_concurrency": 5}
    ):
        print(f"--- Step: {list(step.keys())} ---")

    print("--- ---")

if __name__ == "__main__":
    # Ensure.env is loaded (or keys are set)
    from dotenv import load_dotenv
    load_dotenv()

    asyncio.run(run_test())
```

```

I've enclosed the entire document in a Markdown block for you. Let me know if you need anything else.
```
