# Agent — LLM invocation from the command line

## Overview
`agent.py` is a simple CLI tool that takes a question, sends it to an LLM via an OpenAI-compatible API, and returns a structured JSON response with the fields `answer` and `tool_calls` (empty for now).

## Selected provider and model
- **Provider**: Qwen Code API (deployed locally on a VM) or any other with an OpenAI-compatible interface.
- **Model**: `qwen3-coder-plus` (default). Can be changed in `.env.agent.secret`.

## Environment setup
1. Copy the environment variables file:
   ```bash
   cp .env.agent.example .env.agent.secret