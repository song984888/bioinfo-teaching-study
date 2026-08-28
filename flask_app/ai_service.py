import re
import json
import sys
import os
import requests

# Add parent directory to path for prompt_templates_test3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from prompt_templates_test3 import CODING_PROMPT

from config import Config


class QuestionGenerator:
    def generate_question(self, topic: str, difficulty: int, language: str) -> dict:
        prompt = CODING_PROMPT.format(topic=topic, difficulty=difficulty, language=language)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    Config.OLLAMA_ENDPOINT,
                    json={
                        "model": Config.MODEL_NAME,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    },
                    timeout=Config.OLLAMA_TIMEOUT
                )
                response.raise_for_status()
                data = self._parse_response(response.json().get("response", "{}"))
                return self._validate_hints(data)
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    continue
                raise Exception("Ollama service timeout. Check server status.")
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"Failed to generate question: {str(e)}")
        return {}

    def _parse_response(self, raw_response: str) -> dict:
        cleaned = re.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', raw_response)
        return json.loads(cleaned)

    def _validate_hints(self, data):
        if not isinstance(data.get('hints'), list):
            data['hints'] = []
        if len(data['hints']) == 0:
            data['hints'].append("Refer to the sample code structure")
        return data


def auto_grade(question_text, sample_answer, student_code):
    """Auto-grade student code via Ollama. Returns {score, comment}."""
    prompt_text = f"""Please grade the following code answer:

Question: {question_text}
Reference Answer: {sample_answer}
Student Answer: {student_code}
Grading criteria (0-100): syntax correctness, logic correctness, code style
Output format: {{"score": <number>, "comment": "<feedback>"}}"""

    response = requests.post(
        Config.OLLAMA_ENDPOINT,
        json={
            "model": Config.MODEL_NAME,
            "prompt": prompt_text,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2}
        },
        timeout=Config.OLLAMA_TIMEOUT
    )
    response.raise_for_status()
    result_raw = response.json().get("response", "{}")
    return json.loads(result_raw)
