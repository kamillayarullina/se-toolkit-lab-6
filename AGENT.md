# Agent – Documentation Assistant with Tools

## Overview
`agent.py` is a CLI tool that answers questions about a project's wiki by using two tools:  
- `read_file` – reads a file's content.  
- `list_files` – lists files in a directory.  

It implements an agentic loop: the LLM decides whether to call a tool or provide the final answer. The final output is a JSON object with fields `answer`, `source`, and `tool_calls`.

## Selected Provider and Model
- **Provider**: Qwen Code API (or any OpenAI‑compatible API)
- **Model**: `qwen3-coder-plus` (default, can be changed in `.env.agent.secret`)

## Environment Setup
1. Copy `.env.agent.example` to `.env.agent.secret` and fill in your credentials:
   ```bash
   cp .env.agent.example .env.agent.secret