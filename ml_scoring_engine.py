"""Local learned presentation scoring with a deterministic fallback."""

from pathlib import Path

import numpy as np
import pandas as pd

try:
    import joblib
except ImportError:
    joblib = None


class MLScoringEngine:
    FEATURE_NAMES = ("wpm", "fillers_per_min", "pitch_std", "pause_ratio", "gaze_variance", "avg_word_prob")

    @staticmethod
    def _is_rank_eligible(metadata):
        training_source = str(metadata.get("training_source", "")).lower()
        return bool(
            metadata.get("production_calibrated") is True
            and training_source
            and "synthetic" not in training_source
        )

    def __init__(self, model_path="models/presentation_scorer.joblib"):
        self.model_path = Path(model_path)
        self.model = None
        self.rank_eligible = False
        self.rank_exclusion_reason = "Model is advisory until trained on real labeled presentations"
        if joblib is not None and self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                metadata = getattr(self.model, "presentation_model_metadata", {})
                self.rank_eligible = self._is_rank_eligible(metadata)
                if not self.rank_eligible:
                    self.rank_exclusion_reason = (
                        "Model is advisory until explicitly calibrated on real labeled presentations"
                    )
                else:
                    self.rank_exclusion_reason = "Local learned model is enabled"
            except (OSError, ValueError, ImportError):
                self.model = None
                self.rank_exclusion_reason = "Model could not be loaded"

    @property
    def available(self):
        return self.model is not None

    @staticmethod
    def _duration_minutes(metrics):
        return max(float(metrics.get("duration_sec", 1) or 1) / 60.0, 1 / 60.0)

    def build_features(self, speech_metrics, gaze_metrics=None):
        gaze_metrics = gaze_metrics or {}
        duration_minutes = self._duration_minutes(speech_metrics)
        features = [
            float(speech_metrics.get("wpm", 0) or 0),
            float(speech_metrics.get("filler_count", 0) or 0) / duration_minutes,
            float(speech_metrics.get("pitch_variation", speech_metrics.get("pitch_std", 0)) or 0),
            float(speech_metrics.get("pause_seconds", 0) or 0) / max(float(speech_metrics.get("duration_sec", 1) or 1), 1),
            float(gaze_metrics.get("gaze_variance", 0) or 0),
            float(speech_metrics.get("avg_word_prob", 0) or 0),
        ]
        return np.asarray(features, dtype=np.float32).reshape(1, -1)

    def predict(self, speech_metrics, gaze_metrics=None):
        features = self.build_features(speech_metrics, gaze_metrics)
        if self.model is not None:
            try:
                model_features = pd.DataFrame(features, columns=self.FEATURE_NAMES)
                score = float(self.model.predict(model_features)[0])
            except (ValueError, AttributeError, TypeError):
                score = self._fallback_score(speech_metrics, gaze_metrics)
        else:
            score = self._fallback_score(speech_metrics, gaze_metrics)
        return round(float(np.clip(score, 0, 100)), 2)

    def predict_score(self, speech_metrics, gaze_metrics=None):
        return self.predict(speech_metrics, gaze_metrics)

    @staticmethod
    def _fallback_score(speech_metrics, gaze_metrics=None):
        gaze_metrics = gaze_metrics or {}
        duration = max(float(speech_metrics.get("duration_sec", 1) or 1), 1)
        wpm = float(speech_metrics.get("wpm", 0) or 0)
        fillers_per_min = float(speech_metrics.get("filler_count", 0) or 0) / (duration / 60)
        pitch = float(speech_metrics.get("pitch_variation", 0) or 0)
        pause_ratio = float(speech_metrics.get("pause_seconds", 0) or 0) / duration
        avg_word_prob = float(speech_metrics.get("avg_word_prob", 0.5) or 0.5)
        gaze_penalty = float(gaze_metrics.get("reading_confidence_score", 0) or 0) * 0.2
        pace = max(0, 100 - abs(wpm - 140) * 1.05) if wpm else 35
        quality = (
            pace * 0.28
            + max(0, 100 - fillers_per_min * 10) * 0.22
            + min(100, pitch * 2.8) * 0.18
            + max(0, 100 - pause_ratio * 220) * 0.18
            + max(0, avg_word_prob * 100 - 15) * 0.14
        )
        quality -= gaze_penalty
        quality -= max(0, 70 - (avg_word_prob * 100)) * 0.25
        return float(np.clip(quality, 0, 100))
