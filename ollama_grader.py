"""Local open-source coaching for the grading system.

This project can use a local Ollama instance installed on the same machine when
available, but it never relies on any external cloud AI API. If Ollama is not
running, the app gracefully falls back to deterministic offline coaching.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CoachingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(max_length=400)
    strengths: list[str] = Field(min_length=3, max_length=3)
    improvements: list[str] = Field(min_length=3, max_length=3)
    next_step: str = Field(min_length=1)

    @field_validator("summary")
    @classmethod
    def summary_must_be_short(cls, value):
        if len(value.split()) > 60:
            raise ValueError("summary must contain at most 60 words")
        return value.strip()

    @field_validator("strengths", "improvements")
    @classmethod
    def items_must_be_nonempty(cls, values):
        return [str(value).strip() for value in values]


class OllamaGrader:
    def __init__(self, base_url=None, model=None, timeout=90):
        configured = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        if configured.startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0", "http://[::1]")):
            self.base_url = configured
        else:
            self.base_url = "http://127.0.0.1:11434"
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.timeout = timeout

    def is_available(self):
        if not self.base_url or not self.base_url.startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0", "http://[::1]")):
            return False
        try:
            with urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                return response.status == 200
        except (OSError, HTTPError, URLError):
            return False

    def review(self, video_name, features, evaluation, speech_metrics=None, speech_evaluation=None):
        if self.is_available():
            return self._review_with_local_ollama(video_name, features, evaluation, speech_metrics, speech_evaluation)

        summary, strengths, improvements, next_step = self._offline_feedback(
            video_name,
            features,
            evaluation,
            speech_metrics or {},
            speech_evaluation or {},
        )
        return {
            "available": False,
            "model": self.model,
            "summary": summary,
            "strengths": strengths,
            "improvements": improvements,
            "next_step": next_step,
        }

    def _review_with_local_ollama(self, video_name, features, evaluation, speech_metrics=None, speech_evaluation=None):
        prompt = self._build_prompt(video_name, features, evaluation, speech_metrics, speech_evaluation)
        payload = {
            "model": self.model,
            "stream": False,
            "format": CoachingResponse.model_json_schema(),
            "options": {"temperature": 0.2},
            "prompt": prompt,
        }
        request = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            parsed = CoachingResponse.model_validate(json.loads(result.get("response", "{}")))
            return {
                "available": True,
                "model": self.model,
                **parsed.model_dump(),
            }
        except (OSError, HTTPError, URLError, ValueError, json.JSONDecodeError):
            return self._fallback_review(video_name, features, evaluation, speech_metrics, speech_evaluation)

    def _fallback_review(self, video_name, features, evaluation, speech_metrics=None, speech_evaluation=None):
        summary, strengths, improvements, next_step = self._offline_feedback(
            video_name,
            features,
            evaluation,
            speech_metrics or {},
            speech_evaluation or {},
        )
        return {
            "available": False,
            "model": self.model,
            "summary": summary,
            "strengths": strengths,
            "improvements": improvements,
            "next_step": next_step,
        }

    @staticmethod
    def _offline_feedback(video_name, features, evaluation, speech_metrics, speech_evaluation):
        visual_score = evaluation.get("overall_score", 0) if isinstance(evaluation, dict) else 0
        speech_score = speech_evaluation.get("speaking_score", 0) if isinstance(speech_evaluation, dict) else 0

        strengths = []
        improvements = []

        if visual_score >= 75:
            strengths.append("Visual framing and clarity are strong enough to support a credible presentation.")
        elif visual_score > 0:
            improvements.append("Increase visual clarity by improving lighting, framing, and on-screen focus.")

        if speech_score >= 75:
            strengths.append("The delivery appears steady and easy to follow for the audience.")
        elif speech_score > 0:
            improvements.append("Improve pacing, vocal variety, and filler control to strengthen delivery.")

        motion = features.get("avg_motion", 0) if isinstance(features, dict) else 0
        brightness = features.get("avg_brightness", 0) if isinstance(features, dict) else 0
        if motion and motion > 20:
            improvements.append("Reduce unnecessary motion so the speaker remains visually stable and focused.")
        if brightness and brightness < 60:
            improvements.append("Increase lighting consistency to improve visual readability and professionalism.")

        strengths.append("The scoring engine completed a local, deterministic assessment for this presentation.")
        improvements.append("Keep refining the message structure and delivery to strengthen impact over time.")

        summary = (
            f"Offline review complete for {video_name}. "
            "The deterministic grading engine remains the final source of truth for this assessment."
        )
        next_step = "Use the detailed scoring breakdown to improve clarity, pacing, and presentation consistency."
        return summary, (strengths + ["Use the detailed scoring breakdown to guide the next rehearsal."])[:3], (improvements + ["Repeat the assessment after applying one focused delivery change."])[:3], next_step

    @staticmethod
    def _build_prompt(video_name, features, evaluation, speech_metrics, speech_evaluation):
        evidence = json.dumps({
            "video_name": video_name,
            "visual_metrics": features,
            "visual_evaluation": evaluation,
            "speech_metrics": speech_metrics or {},
            "speech_evaluation": speech_evaluation or {},
        }, ensure_ascii=True)
        return (
            "You are a precise presentation coach running entirely on a local machine. "
            "Return only JSON matching the supplied schema. Ground every statement strictly "
            "in the supplied metrics; do not invent events, intentions, or observations. "
            "Give exactly three concrete strengths, exactly three improvements, and one "
            "actionable next step. Treat gaze and reading signals as probabilistic proxies.\n\n"
            f"Assessment evidence:\n{evidence}"
        )
