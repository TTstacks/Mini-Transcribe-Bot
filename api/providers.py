import time
from abc import ABC, abstractmethod

import requests
from django.conf import settings

from api.reporting import parse_and_validate_report


class ProviderError(Exception):
    pass


class TranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path):
        raise NotImplementedError


class LLMProvider(ABC):
    @abstractmethod
    def analyze(self, transcript):
        raise NotImplementedError


class GroqClient:
    base_url = "https://api.groq.com/openai/v1"

    def __init__(self, api_key=None, timeout=None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.timeout = timeout or settings.PROVIDER_TIMEOUT_SECONDS
        if not self.api_key:
            raise ProviderError("GROQ_API_KEY is not configured.")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    def request_with_retry(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        last_error = None
        extra_headers = kwargs.pop("headers", {})
        files = kwargs.get("files", {})

        for attempt in range(2):
            for file_obj in files.values():
                if hasattr(file_obj, "seek"):
                    file_obj.seek(0)

            try:
                response = requests.request(
                    method,
                    url,
                    headers={**self.headers, **extra_headers},
                    timeout=self.timeout,
                    **kwargs,
                )
            except requests.Timeout as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(0.2)
                    continue
                raise ProviderError("Provider request timed out.") from exc
            except requests.RequestException as exc:
                raise ProviderError("Provider network request failed.") from exc

            if response.status_code >= 500 and attempt == 0:
                last_error = ProviderError(
                    f"Provider returned temporary error {response.status_code}."
                )
                time.sleep(0.2)
                continue

            if response.status_code >= 400:
                raise ProviderError(
                    f"Provider returned error {response.status_code}: {response.text[:200]}"
                )

            try:
                return response.json()
            except ValueError as exc:
                raise ProviderError("Provider returned invalid JSON.") from exc

        raise ProviderError(str(last_error or "Provider request failed."))


class GroqWhisperProvider(TranscriptionProvider):
    def __init__(self, client=None, model=None):
        self.client = client or GroqClient()
        self.model = model or settings.GROQ_TRANSCRIPTION_MODEL

    def transcribe(self, audio_path):
        with open(audio_path, "rb") as audio_file:
            payload = self.client.request_with_retry(
                "POST",
                "/audio/transcriptions",
                files={"file": audio_file},
                data={"model": self.model},
            )

        transcript = payload.get("text")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ProviderError("Transcription provider returned an empty transcript.")
        return transcript


class GroqLLMProvider(LLMProvider):
    def __init__(self, client=None, model=None):
        self.client = client or GroqClient()
        self.model = model or settings.GROQ_LLM_MODEL

    def analyze(self, transcript):
        payload = self.client.request_with_retry(
            "POST",
            "/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return only JSON with keys summary, topics, sentiment, "
                            "and action_items. Sentiment must be positive, neutral, "
                            "or negative."
                        ),
                    },
                    {"role": "user", "content": transcript},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("LLM provider returned an unexpected response.") from exc

        return parse_and_validate_report(content)
