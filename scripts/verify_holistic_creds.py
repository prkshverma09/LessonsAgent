#!/usr/bin/env python
"""Quick Holistic credential check."""

import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tutorials.holistic_ai_bedrock import get_chat_model  # noqa: E402


def main() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    print("🔐 Verifying HOLISTIC_AI_* credentials ...")
    try:
        llm = get_chat_model("claude-3-5-sonnet")
        print("✅ Credentials loaded. Sending test prompt …")
        response = llm.invoke([HumanMessage(content="Ping")])
        print("✅ Success! Model responded:", response.content)
    except Exception as exc:
        print("❌ Credential or access failure:")
        print(exc)


if __name__ == "__main__":
    main()

