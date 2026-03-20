import json
from typing import Any, Dict, List

import requests


class LLMClient:
    def __init__(
        self,
        endpoint: str,
        model: str,
        timeout_seconds: int = 120,
    ):
        self.endpoint = endpoint
        self.model = model
        self.timeout_seconds = timeout_seconds

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = self._build_chat_endpoint()
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "stream": False,
        }

        response = requests.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                "LLM request failed: "
                f"status={response.status_code}, "
                f"endpoint={endpoint}, "
                f"response={self._format_error_body(response)}"
            )

        data = response.json()
        choices: List[Dict[str, Any]] = data.get("choices", [])
        if not choices:
            raise ValueError("LLM response has no choices field")

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        if isinstance(content, list):
            content = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

        if not isinstance(content, str) or not content:
            text_content = choice.get("text", "")
            if isinstance(text_content, str) and text_content:
                return text_content
            raise ValueError(
                "LLM response content is empty or not string: "
                f"{json.dumps(data, ensure_ascii=False)[:1000]}"
            )

        return content

    def _build_chat_endpoint(self) -> str:
        endpoint = self.endpoint.rstrip("/")

        if endpoint.endswith("/chat/completions"):
            return endpoint

        if endpoint.endswith("/v1"):
            return f"{endpoint}/chat/completions"

        return f"{endpoint}/v1/chat/completions"

    @staticmethod
    def _format_error_body(response: requests.Response) -> str:
        try:
            body = response.json()
            return json.dumps(body, ensure_ascii=False)[:2000]
        except ValueError:
            return response.text[:2000]
