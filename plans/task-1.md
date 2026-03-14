# Task 1: Call an LLM from Code — Implementation Plan

## LLM Provider and Model Selection
- **Provider**: Qwen Code API (deployed on a local VM) — recommended in the task.
- **Model**: `qwen3-coder-plus` (supports tool calling, will be useful in future tasks).
- **API Compatibility**: OpenAI format `/chat/completions`.

## Structure of `agent.py`
1. Load environment variables from `.env.agent.secret` using `python-dotenv`.
2. Get the question from the first command-line argument (`sys.argv[1]`).
3. Set a timeout of 60 seconds for the entire operation (use `requests.post(..., timeout=60)`).
4. Send a POST request to `LLM_API_BASE/chat/completions` with the authorization header.
   - Request body:
     ```json
     {
       "model": LLM_MODEL,
       "messages": [
         {"role": "system", "content": "You are a helpful assistant."},
         {"role": "user", "content": question}
       ]
     }