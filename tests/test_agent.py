import subprocess
import json
import sys

def test_agent():
    """Запускает agent.py с тестовым вопросом и проверяет структуру JSON."""
    question = "What does REST stand for?"
    
    try:
        # Запускаем agent.py через uv run
        result = subprocess.run(
            ['uv', 'run', 'agent.py', question],
            capture_output=True,
            text=True,
            timeout=70  # чуть больше таймаута агента (60 сек)
        )
    except subprocess.TimeoutExpired:
        print("Test failed: agent.py exceeded 70 seconds", file=sys.stderr)
        sys.exit(1)

    # Проверяем код возврата — должен быть 0
    assert result.returncode == 0, f"Expected return code 0, got {result.returncode}\nstderr: {result.stderr}"

    # Парсим stdout как JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        assert False, f"stdout is not valid JSON: {e}\nstdout: {result.stdout}"

    # Проверяем наличие обязательных полей
    assert 'answer' in output, "Field 'answer' is missing"
    assert 'tool_calls' in output, "Field 'tool_calls' is missing"
    assert isinstance(output['tool_calls'], list), "Field 'tool_calls' must be a list"
    assert len(output['tool_calls']) == 0, "tool_calls list must be empty"

    # Дополнительно можно проверить, что ответ не пустой
    assert output['answer'], "Answer should not be empty"

    print("Test passed successfully")

if __name__ == '__main__':
    test_agent()