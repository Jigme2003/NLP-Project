"""Offline validation suite for the local presentation grading system."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from communication_grade import WeightedCommunicationScorer
from gaze_detector import MediaPipeGazeDetector
from ml_scoring_engine import MLScoringEngine
from ollama_grader import CoachingResponse, OllamaGrader


def validate_ollama_schema():
    payload = {
        "response": json.dumps({
            "summary": "A concise local review.",
            "strengths": ["Clear pace", "Stable framing", "Useful structure"],
            "improvements": ["Reduce fillers", "Improve lighting", "Use stronger evidence"],
            "next_step": "Record one rehearsal focused on filler reduction.",
        })
    }
    grader = OllamaGrader(base_url="http://127.0.0.1:11434")
    with patch.object(grader, "is_available", return_value=True), patch("ollama_grader.urlopen") as opener:
        opener.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        result = grader.review("validation.mp4", {}, {})
    parsed = CoachingResponse.model_validate({
        key: result[key] for key in ("summary", "strengths", "improvements", "next_step")
    })
    assert len(parsed.strengths) == 3
    assert len(parsed.improvements) == 3


def validate_stability_curve():
    score_5 = WeightedCommunicationScorer._stability_score(5)
    score_15 = WeightedCommunicationScorer._stability_score(15)
    score_25 = WeightedCommunicationScorer._stability_score(25)
    assert score_5 == 100
    assert score_5 > score_15 > score_25 >= 0


def validate_uncoupled_scoring():
    visual = {"avg_sharpness": 300, "avg_brightness": 120, "avg_motion": 8}
    speech = {"wpm": 140, "filler_count": 1, "duration_sec": 60, "pause_seconds": 4, "pitch_variation": 30}
    first = WeightedCommunicationScorer.evaluate(visual, speech, historical_scores=[10, 20])
    second = WeightedCommunicationScorer.evaluate(visual, speech, historical_scores=[90, 95])
    assert first["overall_score"] == second["overall_score"]


def validate_ml_and_vision():
    score = MLScoringEngine().predict_score({
        "wpm": 140, "filler_count": 1, "duration_sec": 60,
        "pitch_variation": 30, "pause_seconds": 4, "avg_word_prob": 0.8,
    }, {"gaze_variance": 0.01})
    assert isinstance(score, float)
    assert 0 <= score <= 100
    assert MLScoringEngine().rank_eligible is False
    detector = MediaPipeGazeDetector(sample_interval_sec=0.5)
    assert detector.sample_interval_sec == 0.5
    empty = detector.empty_result("validation")
    assert empty["low_confidence"] is True


def main():
    validate_ollama_schema()
    validate_stability_curve()
    validate_uncoupled_scoring()
    validate_ml_and_vision()
    print("Offline validation passed")


if __name__ == "__main__":
    main()