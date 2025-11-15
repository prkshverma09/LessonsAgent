# LessonsAgent

## Local Setup (Task 0)

1. **Create & activate the virtual environment**

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
   # edit .env with your HOLISTIC_AI_TEAM_ID, HOLISTIC_AI_API_TOKEN, and VALYU_API_KEY
   ```

4. **Verify setup**

   ```bash
   python -c "import langchain, pydantic; print('env ready')"
   ```
