# Task 2: The Documentation Agent — Implementation Plan

## Tool Definitions
We will implement two tools:
- **read_file(path)**: Reads and returns the content of a file.  
  Security: ensures the resolved absolute path stays within the project root (using `os.path.abspath` and checking prefix).
- **list_files(path)**: Lists files and directories at the given path.  
  Security: same path restriction.

## Tool Schemas (OpenAI Function Calling format)
Both tools will be described as JSON schemas and passed to the LLM in each request.

## Agentic Loop
1. Send the user question plus tool definitions to the LLM.
2. Receive response.
3. If `tool_calls` present:
   - Execute each tool call, collecting results.
   - Append each result as a new message with role `tool`.
   - Repeat step 1 (maximum 10 iterations).
4. If no `tool_calls`, treat the response as final answer.
   - Extract the answer text.
   - Extract the source reference (the LLM will be prompted to include it in a specific format, e.g., `[Source: path#anchor]`).
5. Build the final JSON output with fields:
   - `answer`: the final answer string.
   - `source`: the source reference (file path + anchor).
   - `tool_calls`: an array of all tool calls made, each containing `tool`, `args`, and `result`.

## Security
- Project root: the directory containing `agent.py`.
- All file operations will resolve the requested path against the project root and verify that the resolved path is still inside the project root (no `..` traversal allowed).
- If a path is invalid or outside the project, return an error message instead of reading/listing.

## Testing (additional 2 tests)
- `test_merge_conflict`: Ask "How do you resolve a merge conflict?"  
  Expect: `tool_calls` contains at least one `read_file` call, `source` contains `wiki/git-workflow.md#...`, exit code 0.
- `test_list_files`: Ask "What files are in the wiki?"  
  Expect: `tool_calls` contains a `list_files` call, result contains file names, exit code 0.