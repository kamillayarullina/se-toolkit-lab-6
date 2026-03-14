# Task 3: The System Agent – Implementation Plan

## Objective
Extend the documentation agent from Task 2 with a new tool `query_api` that can call the deployed backend API. This allows the agent to answer questions about the live system: static facts (framework, ports, status codes) and data‑dependent queries (item count, scores). The agent will use the same loop but now has three tools: `read_file`, `list_files`, and `query_api`.

## Tool Schema: `query_api`
- **name**: `query_api`
- **description**: "Call the backend API. Use this to get live data from the running service."
- **parameters**:
  - `method` (string, required): HTTP method (GET, POST, etc.)
  - `path` (string, required): API endpoint path, e.g. `/items/`
  - `body` (string, optional): JSON request body (only for POST/PUT)
- **returns**: A JSON string containing `{"status_code": int, "body": <parsed response>}`.

## Implementation Details
- The backend base URL is read from the environment variable `AGENT_API_BASE_URL` (default `http://localhost:42002`).
- Authentication uses `LMS_API_KEY` from `.env.docker.secret` (different from the LLM key).
- The tool handles both successful and error responses; the status code and body are always returned so the LLM can interpret them.
- The function returns a string (JSON) as required by the tool output format.

## System Prompt Update
The system prompt is expanded to explain the purpose of each tool:
- `read_file` / `list_files`: for project wiki and source code.
- `query_api`: for interacting with the running backend (live data, error codes, etc.).

The prompt also instructs the LLM to prefer `query_api` when the question asks for current data (e.g., "how many items") or HTTP status codes, and to use file tools when the answer lies in documentation or source code.

## Benchmark Diagnosis (First Run)
Initial run of `run_eval.py` on the Task 2 agent produced:
- Passed: wiki lookup questions (0‑3)
- Failed: questions 4‑7 (require `query_api`)
- Score: 4/10

### Failures and Iteration Strategy
1. **Question 4** ("How many items …"): agent did not call `query_api`.  
   → Fix: improve tool description and add an example in the system prompt.
2. **Question 5** ("status code without auth"): agent called `query_api` but with wrong path or method.  
   → Fix: clarify in the tool description that `path` must include the full endpoint (e.g., `/items/`).
3. **Question 6‑7** (bug diagnosis): agent called `query_api` but then did not call `read_file` to find the bug.  
   → Fix: strengthen prompt to chain tools: after getting an error from the API, read the relevant source file to explain the bug.
4. **Question 8‑9** (LLM‑judged): currently too short answers; need to prompt for more detail.

## Iteration Plan
- After implementing `query_api`, run `run_eval.py` repeatedly, adjust the system prompt and tool descriptions based on each failure.
- Keep a log of improvements until all 10 questions pass.

## Environment Variables
All required variables are read from the environment (no hardcoding):
- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` – from `.env.agent.secret`
- `LMS_API_KEY` – from `.env.docker.secret`
- `AGENT_API_BASE_URL` – optional, defaults to `http://localhost:42002`