#!/usr/bin/env python3
"""
agent.py – System agent with read_file, list_files, and query_api tools.
Usage: uv run agent.py "Your question"
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# ----------------------------------------------------------------------
# Configuration & environment
# ----------------------------------------------------------------------
load_dotenv('.env.agent.secret')
load_dotenv('.env.docker.secret')          # for LMS_API_KEY

LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE')
LLM_MODEL = os.getenv('LLM_MODEL')
LMS_API_KEY = os.getenv('LMS_API_KEY')
AGENT_API_BASE_URL = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
print(f"DEBUG LOAD: LLM_API_BASE={LLM_API_BASE}", file=sys.stderr)

if not all([LLM_API_KEY, LLM_API_BASE, LLM_MODEL, LMS_API_KEY]):
    print("Error: missing required environment variables (LLM_API_KEY, LLM_API_BASE, LLM_MODEL, LMS_API_KEY)", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.absolute()

# ----------------------------------------------------------------------
# Tool implementations
# ----------------------------------------------------------------------
def read_file(path: str) -> str:
    """Read a file from the project repository."""
    try:
        requested_path = (PROJECT_ROOT / path).resolve()
        if not str(requested_path).startswith(str(PROJECT_ROOT)):
            return f"Error: Access denied – path '{path}' is outside the project directory."
        if not requested_path.exists():
            return f"Error: File '{path}' does not exist."
        if not requested_path.is_file():
            return f"Error: '{path}' is not a file."
        return requested_path.read_text(encoding='utf-8')
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

def list_files(path: str) -> str:
    """List files and directories at a given path."""
    try:
        requested_path = (PROJECT_ROOT / path).resolve()
        if not str(requested_path).startswith(str(PROJECT_ROOT)):
            return f"Error: Access denied – path '{path}' is outside the project directory."
        if not requested_path.exists():
            return f"Error: Path '{path}' does not exist."
        if not requested_path.is_dir():
            return f"Error: '{path}' is not a directory."
        entries = sorted([p.name for p in requested_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory '{path}': {str(e)}"

def query_api(method: str, path: str, body: str = None) -> str:
    """Call the backend API with the given method, path, and optional body."""
    url = AGENT_API_BASE_URL.rstrip('/') + path
    headers = {
        'Authorization': f'Bearer {LMS_API_KEY}',
        'Content-Type': 'application/json'
    }
    try:
        if method.upper() == 'GET':
            resp = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == 'POST':
            resp = requests.post(url, headers=headers, json=json.loads(body) if body else None, timeout=30)
        elif method.upper() == 'PUT':
            resp = requests.put(url, headers=headers, json=json.loads(body) if body else None, timeout=30)
        elif method.upper() == 'DELETE':
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            return json.dumps({"status_code": 400, "body": f"Unsupported method: {method}"})
        # Return both status code and response body (as Python object converted to string)
        try:
            body_json = resp.json()
        except:
            body_json = resp.text
        return json.dumps({"status_code": resp.status_code, "body": body_json})
    except Exception as e:
        return json.dumps({"status_code": 500, "body": f"API call failed: {str(e)}"})

# ----------------------------------------------------------------------
# Tool schemas
# ----------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to get information from the wiki or source code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from the project root (e.g., 'wiki/git-workflow.md')."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories inside a given folder. Use this to discover available files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path from the project root (e.g., 'wiki')."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the backend API to get live data. Use this for questions about the current state of the system, such as item counts, error codes, or data from endpoints. Returns a JSON with status_code and body.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "description": "HTTP method."},
                    "path": {"type": "string", "description": "API endpoint path, e.g. '/items/' or '/analytics/completion-rate?lab=lab-99'."},
                    "body": {"type": "string", "description": "Optional JSON request body (for POST/PUT)."}
                },
                "required": ["method", "path"]
            }
        }
    }
]

# ----------------------------------------------------------------------
# Agentic loop
# ----------------------------------------------------------------------
def call_llm(messages):
    headers = {
        'Authorization': f'Bearer {LLM_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': LLM_MODEL,
        'messages': messages,
        'tools': TOOLS,
        'tool_choice': 'auto'
    }
    try:
        resp = requests.post(
            f'{LLM_API_BASE.rstrip("/")}/chat/completions',
            headers=headers,
            json=payload,
            timeout=180
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        sys.exit(1)

def extract_source_from_answer(answer_text):
    import re
    pattern = r'\[Source:\s*(.+?)\]'
    match = re.search(pattern, answer_text)
    if match:
        source = match.group(1).strip()
        cleaned = re.sub(pattern, '', answer_text).strip()
        return cleaned, source
    return answer_text, ""

def main():
    if len(sys.argv) < 2:
        print("Error: question not provided. Usage: uv run agent.py \"Your question\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    system_prompt = (
        "You are a system assistant for a software project. You have three tools:\n"
        "1. read_file – read a file from the project (wiki or source code).\n"
        "2. list_files – list files in a directory.\n"
        "3. query_api – call the backend API to get live data.\n\n"
        "For questions about the project's documentation or source code, use read_file/list_files.\n"
        "For questions about the running system (e.g., how many items, what status code), use query_api.\n"
        "If you get an error from the API, you may need to read the source code to explain the bug.\n"
        "When you provide the final answer, include the source file and section anchor if applicable in the format: [Source: path#anchor]. For API answers, no source is needed."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_calls_log = []
    max_iterations = 10
    final_answer = None
    final_source = ""

    for _ in range(max_iterations):
        llm_response = call_llm(messages)
        choice = llm_response['choices'][0]
        message = choice['message']

        if 'tool_calls' in message and message['tool_calls']:
            for tc in message['tool_calls']:
                func_name = tc['function']['name']
                args = json.loads(tc['function']['arguments'])
                if func_name == 'read_file':
                    result = read_file(args['path'])
                elif func_name == 'list_files':
                    result = list_files(args['path'])
                elif func_name == 'query_api':
                    method = args.get('method', 'GET')
                    path = args.get('path', '')
                    body = args.get('body', None)
                    result = query_api(method, path, body)
                else:
                    result = f"Unknown tool: {func_name}"

                tool_calls_log.append({
                    "tool": func_name,
                    "args": args,
                    "result": result
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc['id'],
                    "content": result
                })
            continue
        else:
            answer_text = message.get('content')
            if answer_text is None:
                answer_text = ""
            final_answer, final_source = extract_source_from_answer(answer_text)
            break
    else:
        if not final_answer:
            last_msg = messages[-1]
            if last_msg['role'] == 'assistant' and 'content' in last_msg:
                final_answer, final_source = extract_source_from_answer(last_msg['content'])
            else:
                final_answer = "Sorry, I couldn't find an answer within the allowed steps."
                final_source = ""

    output = {
        "answer": final_answer,
        "source": final_source,
        "tool_calls": tool_calls_log
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)

if __name__ == '__main__':
    main()
