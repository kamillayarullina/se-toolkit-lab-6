import subprocess
import json
import sys
import time

def run_agent(question):
    """Helper to run agent.py with a question and return the result."""
    try:
        result = subprocess.run(
            ['uv', 'run', 'agent.py', question],
            capture_output=True,
            text=True,
            timeout=70
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Test failed: agent.py exceeded 70 seconds for question: {question}", file=sys.stderr)
        sys.exit(1)

def test_agent_basic():
    """Test basic functionality (no tools needed)."""
    question = "What does REST stand for?"
    result = run_agent(question)

    assert result.returncode == 0, f"Return code {result.returncode}\nstderr: {result.stderr}"
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        assert False, f"Invalid JSON: {e}\nstdout: {result.stdout}"

    assert 'answer' in output, "Missing 'answer'"
    assert 'tool_calls' in output, "Missing 'tool_calls'"
    assert isinstance(output['tool_calls'], list), "'tool_calls' must be a list"
    assert output['answer'], "Answer should not be empty"
    # For this question, likely no tools are used, but that's okay
    print("Basic test passed")

def test_merge_conflict():
    """Test that the agent uses read_file and returns a source for merge conflict question."""
    question = "How do you resolve a merge conflict?"
    result = run_agent(question)

    assert result.returncode == 0, f"Return code {result.returncode}\nstderr: {result.stderr}"
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        assert False, f"Invalid JSON: {e}\nstdout: {result.stdout}"

    assert 'answer' in output, "Missing 'answer'"
    assert 'source' in output, "Missing 'source'"
    assert 'tool_calls' in output, "Missing 'tool_calls'"

    # Check that source contains the expected wiki file
    assert 'wiki/git-workflow.md' in output['source'], f"Source '{output['source']}' does not contain 'wiki/git-workflow.md'"

    # Check that at least one tool call is read_file
    tool_names = [call['tool'] for call in output['tool_calls']]
    assert 'read_file' in tool_names, f"Expected read_file tool call, got {tool_names}"

    print("Merge conflict test passed")

def test_list_files():
    """Test that the agent uses list_files when asked about wiki contents."""
    question = "What files are in the wiki?"
    result = run_agent(question)

    assert result.returncode == 0, f"Return code {result.returncode}\nstderr: {result.stderr}"
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        assert False, f"Invalid JSON: {e}\nstdout: {result.stdout}"

    assert 'answer' in output, "Missing 'answer'"
    assert 'tool_calls' in output, "Missing 'tool_calls'"

    # Check that at least one tool call is list_files
    tool_names = [call['tool'] for call in output['tool_calls']]
    assert 'list_files' in tool_names, f"Expected list_files tool call, got {tool_names}"

    # Optionally verify that the result of list_files contains some entries
    list_calls = [call for call in output['tool_calls'] if call['tool'] == 'list_files']
    if list_calls:
        result_text = list_calls[0]['result']
        # The result should contain filenames (like .md files)
        assert any('.md' in line for line in result_text.splitlines()), "list_files result doesn't seem to contain markdown files"

    print("List files test passed")
def test_backend_framework():
    """Agent should use read_file to find the framework from source code."""
    question = "What framework does the backend use?"
    result = run_agent(question)

    assert result.returncode == 0, f"Return code {result.returncode}\nstderr: {result.stderr}"
    output = json.loads(result.stdout)
    assert 'answer' in output
    assert 'tool_calls' in output

    # Check that at least one tool call is read_file
    tool_names = [call['tool'] for call in output['tool_calls']]
    assert 'read_file' in tool_names, f"Expected read_file, got {tool_names}"
    # Answer should mention FastAPI (or whatever the project uses)
    assert 'fastapi' in output['answer'].lower() or 'flask' in output['answer'].lower(), \
        f"Answer does not mention a framework: {output['answer']}"
    print("Backend framework test passed")

def test_item_count():
    """Agent should use query_api to get the number of items."""
    question = "How many items are in the database?"
    result = run_agent(question)

    assert result.returncode == 0, f"Return code {result.returncode}\nstderr: {result.stderr}"
    output = json.loads(result.stdout)
    assert 'answer' in output
    assert 'tool_calls' in output

    tool_names = [call['tool'] for call in output['tool_calls']]
    assert 'query_api' in tool_names, f"Expected query_api, got {tool_names}"
    # Check that the answer contains a number (could be zero or more)
    import re
    assert re.search(r'\d+', output['answer']), f"Answer does not contain a number: {output['answer']}"
    print("Item count test passed")

if __name__ == '__main__':
    # Run all tests
    test_agent_basic()
    test_merge_conflict()
    test_list_files()
    test_backend_framework()
    test_item_count()
    print("\nAll tests passed successfully!")