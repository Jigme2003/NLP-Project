"""Select grading modules from evidence actually extracted from one upload."""


class AssessmentRouter:
    @staticmethod
    def select(visual_metrics, speech_metrics, content_analysis, gaze_metrics, ml_available, ml_rank_eligible=False):
        visual_signal = any(
            float(visual_metrics.get(metric, 0) or 0) > 0
            for metric in ("avg_sharpness", "avg_brightness", "avg_motion")
        )
        visual_available = bool(
            float(visual_metrics.get("duration_sec", 0) or 0) > 0
            or visual_metrics.get("resolution", "0x0") not in ("0x0", "", None)
            or visual_signal
        )

        audio_signal = any(
            float(speech_metrics.get(metric, 0) or 0) > 0
            for metric in ("speech_ratio", "pitch_variation", "energy_variation", "avg_word_prob")
        )
        audio_available = bool(
            int(speech_metrics.get("word_count", 0) or 0) > 0
            or audio_signal
        )

        content_available = bool(
            content_analysis
            and content_analysis.get("score") is not None
        )

        gaze_signal = any(
            float(gaze_metrics.get(metric, 0) or 0) > 0
            for metric in ("reading_confidence_score", "downward_gaze_ratio", "gaze_variance")
        )
        gaze_available = bool(
            gaze_metrics
            and (
                bool(gaze_metrics.get("available"))
                or int(gaze_metrics.get("samples", 0) or 0) > 0
                or gaze_signal
            )
        )
        expression_available = bool(
            gaze_metrics
            and gaze_metrics.get("facial_expressiveness_available")
            and gaze_metrics.get("facial_expressiveness_score") is not None
        )

        ml_input_available = (
            audio_available
            and ml_available
            and (
                int(speech_metrics.get("word_count", 0) or 0) > 0
                or float(speech_metrics.get("avg_word_prob", 0) or 0) > 0
                or float(speech_metrics.get("speech_ratio", 0) or 0) > 0
            )
        )
        modules = {
            "visual": visual_available,
            "audio": audio_available,
            "content": content_available,
            "gaze": gaze_available,
            "expression": expression_available,
            "learned": ml_input_available and ml_rank_eligible,
        }
        reasons = {
            "visual": (
                "Image metrics detected."
                if visual_available
                else "No usable video frames were decoded. Try a playable MP4 or MOV file."
            ),
            "audio": (
                "Speech or voice activity detected."
                if audio_available
                else "No speech or voice activity was detected. Check that the video has an audible voice track."
            ),
            "content": (
                "Transcript available."
                if content_available
                else "No transcript was produced. Use a clear voice recording and ensure the local speech model is available."
            ),
            "gaze": (
                "Face landmarks available."
                if gaze_available
                else "Eye-line needs at least 3 usable face samples. Face the camera in even light and keep your face unobstructed."
            ),
            "expression": (
                "Facial movement cues available; this does not infer motivation or emotion"
                if expression_available
                else "Facial movement needs at least 5 usable face samples. Face the camera in even light; this is not an emotion score."
            ),
            "learned": (
                "Production-calibrated model contributes to rank."
                if ml_input_available and ml_rank_eligible
                else "Excluded from grading until calibrated against verified human-scored examples."
            ),
        }
        return {
            "modules": modules,
            "active": [name for name, enabled in modules.items() if enabled],
            "excluded": [name for name, enabled in modules.items() if not enabled],
            "reasons": reasons,
            "learned_available": ml_input_available,
            "learned_rank_eligible": bool(ml_input_available and ml_rank_eligible),
            "note": "Only modules with usable evidence contribute to the overall score.",
        }
