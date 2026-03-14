#!/usr/bin/env python3
"""
agent.py – отправляет вопрос к LLM и возвращает JSON с ответом.
Использование: uv run agent.py "Ваш вопрос"
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

def main():
    # Загружаем переменные окружения из файла .env.agent.secret
    load_dotenv('.env.agent.secret')

    # Получаем настройки из окружения
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')

    # Проверяем, что все необходимые переменные заданы
    if not api_key or not api_base or not model:
        print("Error: missing required environment variables (LLM_API_KEY, LLM_API_BASE, LLM_MODEL)", file=sys.stderr)
        sys.exit(1)

    # Проверяем, передан ли вопрос в аргументах командной строки
    if len(sys.argv) < 2:
        print("Error: question not provided. Usage: uv run agent.py \"Your question\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Формируем заголовки запроса
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # Формируем тело запроса в формате OpenAI Chat Completions
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': question}
        ]
    }

    try:
        # Выполняем POST-запрос к API с таймаутом 60 секунд
        response = requests.post(
            f'{api_base.rstrip("/")}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()  # Генерирует исключение для HTTP-ошибок
        data = response.json()
        answer = data['choices'][0]['message']['content']
    except requests.exceptions.Timeout:
        print('Error: request timed out after 60 seconds', file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f'Error during request: {e}', file=sys.stderr)
        sys.exit(1)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f'Error parsing API response: {e}', file=sys.stderr)
        sys.exit(1)

    # Формируем итоговый JSON-вывод
    output = {
        'answer': answer,
        'tool_calls': []  # Пока пустой, будет заполняться в следующих задачах
    }

    # Выводим только JSON в stdout (всё остальное — в stderr)
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)

if __name__ == '__main__':
    main()