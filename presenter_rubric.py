"""Presenter-focused rubric used to organize explainable report dimensions."""


class PresenterRubric:
    DIMENSIONS = (
        ("content_quality", "Message & content", "structure, clarity, evidence, vocabulary, and engagement", 0.20),
        ("delivery", "Delivery & fluency", "pace, pauses, filler control, and speech activity", 0.20),
        ("articulation", "Speech clarity proxy", "transcript confidence and delivery cues", 0.10),
        ("confidence", "Vocal control (proxy)", "observable pace, pauses, and voice variation", 0.12),
        ("vocal_expression", "Vocal expression", "pitch and loudness variation in the voice", 0.10),
        ("technical", "Video quality", "lighting, stability, and image readability", 0.08),
        ("recognition_confidence", "Transcript confidence", "speech recognizer confidence proxy", 0.05),
        ("script_adherence", "Script alignment", "word overlap with the optional reference script", 0.03),
        ("gaze_quality", "Eye-line proxy", "measured eye direction; not intent", 0.04),
        ("facial_expressiveness", "Facial movement proxy", "visible expression movement; not emotion or motivation", 0.05),
        ("learned_score", "Learned score", "used in the grade only with real labeled calibration", 0.03),
    )

    @classmethod
    def build(cls, breakdown, scoring_weights=None):
        key_map = {
            "content_quality": "content_quality",
            "delivery": "fluency",
            "articulation": "pronunciation",
            "confidence": "confidence",
            "vocal_expression": "vocal_expression",
            "technical": "visual_quality",
            "recognition_confidence": "recognition_confidence",
            "gaze_quality": "gaze_quality",
            "facial_expressiveness": "facial_expressiveness",
            "script_adherence": "script_adherence",
            "learned_score": "learned_score",
        }
        dimensions = []
        for key, title, description, weight in cls.DIMENSIONS:
            value = breakdown.get(key_map[key])
            score = float(value) if value is not None else None
            if scoring_weights is not None:
                weight = float(scoring_weights.get(key_map[key], 0.0))
            dimensions.append({
                "key": key,
                "title": title,
                "description": description,
                "weight": weight,
                "score": round(score, 1) if score is not None else None,
            })
        return {
            "name": "Presenter Performance Rubric",
            "dimensions": dimensions,
            "note": "Displayed weights are the normalized weights used by the overall score. Facial and gaze values are observable proxies, not conclusions about emotion or intent.",
        }
