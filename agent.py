#!/usr/bin/env python3
"""
agent.py – Documentation agent with read_file and list_files tools.
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

LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE')
LLM_MODEL = os.getenv('LLM_MODEL')

if not all([LLM_API_KEY, LLM_API_BASE, LLM_MODEL]):
    print("Error: missing required environment variables (LLM_API_KEY, LLM_API_BASE, LLM_MODEL)", file=sys.stderr)
    sys.exit(1)

# Project root = directory where agent.py resides
PROJECT_ROOT = Path(__file__).parent.absolute()

# ----------------------------------------------------------------------
# Tool implementations (with security checks)
# ----------------------------------------------------------------------
def read_file(path: str) -> str:
    """Read a file from the project repository."""
    try:
        # Safely resolve the path
        requested_path = (PROJECT_ROOT / path).resolve()
        # Ensure it's still inside the project root
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

# ----------------------------------------------------------------------
# Tool schemas (OpenAI function calling format)
# ----------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from the project root (e.g., 'wiki/git-workflow.md')."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories inside a given folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from the project root (e.g., 'wiki')."
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# ----------------------------------------------------------------------
# Agentic loop
# ----------------------------------------------------------------------
def call_llm(messages):
    """Send a request to the LLM and return the JSON response."""
    headers = {
        'Authorization': f'Bearer {LLM_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': LLM_MODEL,
        'messages': messages,
        'tools': TOOLS,
        'tool_choice': 'auto'  # let the model decide
    }
    try:
        resp = requests.post(
            f'{LLM_API_BASE.rstrip("/")}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"LLM call failed: {e}", file=sys.stderr)
        sys.exit(1)

def extract_source_from_answer(answer_text):
    """
    Try to extract a source reference from the answer.
    Expected format: "... [Source: path#anchor]"
    Returns (cleaned_answer, source) or (answer, "") if no source found.
    """
    import re
    pattern = r'\[Source:\s*(.+?)\]'
    match = re.search(pattern, answer_text)
    if match:
        source = match.group(1).strip()
        # Remove the source marker from the answer
        cleaned = re.sub(pattern, '', answer_text).strip()
        return cleaned, source
    return answer_text, ""

def main():
    if len(sys.argv) < 2:
        print("Error: question not provided. Usage: uv run agent.py \"Your question\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # System prompt instructing the agent to use tools and include source
    system_prompt = (
        "You are a documentation assistant for a software project. "
        "You have access to two tools: read_file (to read file contents) and list_files (to list directory contents). "
        "Your goal is to answer the user's question based on the project wiki. "
        "First, use list_files to discover available wiki files, then use read_file on relevant files to find the answer. "
        "When you provide the final answer, include the source file and section anchor in the format: [Source: path#anchor]"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_calls_log = []  # to record all tool calls with args and results
    max_iterations = 10
    final_answer = None
    final_source = ""

    for _ in range(max_iterations):
        llm_response = call_llm(messages)
        choice = llm_response['choices'][0]
        message = choice['message']

        # If the model wants to call tools
        if 'tool_calls' in message and message['tool_calls']:
            # Record the tool calls (for logging/output)
            for tc in message['tool_calls']:
                func_name = tc['function']['name']
                args = json.loads(tc['function']['arguments'])
                # Execute the appropriate tool
                if func_name == 'read_file':
                    result = read_file(args['path'])
                elif func_name == 'list_files':
                    result = list_files(args['path'])
                else:
                    result = f"Unknown tool: {func_name}"

                # Log this call
                tool_calls_log.append({
                    "tool": func_name,
                    "args": args,
                    "result": result
                })

                # Append tool result to messages (as a new message with role 'tool')
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc['id'],
                    "content": result
                })

            # Continue loop – the assistant's tool call message is already in history,
            # but we need to add the assistant message that requested the tools?
            # Actually the structure: user, assistant (with tool_calls), then tool responses.
            # After tool responses, the next assistant message will be generated.
            # Our messages list already contains the assistant message (from this response) with tool_calls.
            # We have appended tool responses; now we continue to next iteration.
            continue
        else:
            # No tool calls: this is the final answer
            answer_text = message['content']
            final_answer, final_source = extract_source_from_answer(answer_text)
            break
    else:
        # If loop exhausted without final answer, use whatever last response we have
        # (could be the last assistant message after tools, but we didn't capture it)
        # As fallback, take the content of the last assistant message
        if not final_answer:
            # We might have never broken; the last iteration's message may have been tool call?
            # This case should not happen because if the loop ends due to max_iterations,
            # we should have an assistant message with content. But we'll handle gracefully.
            last_msg = messages[-1]
            if last_msg['role'] == 'assistant' and 'content' in last_msg:
                final_answer, final_source = extract_source_from_answer(last_msg['content'])
            else:
                final_answer = "Sorry, I couldn't find an answer within the allowed steps."
                final_source = ""

    # Prepare the final JSON output
    output = {
        "answer": final_answer,
        "source": final_source,
        "tool_calls": tool_calls_log
    }

    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)

if __name__ == '__main__':
    main()