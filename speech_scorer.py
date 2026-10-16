class SpeakingSkillsScorer:
    @staticmethod
    def evaluate(metrics):
        score = 100
        feedback = []

        duration_minutes = max(float(metrics.get("duration_sec", 1) or 1) / 60.0, 1 / 60.0)
        has_transcript = bool(
            metrics.get("transcript")
            or int(metrics.get("word_count", 0) or 0) > 0
        )
        if not has_transcript:
            score = 60
            feedback.append("Transcript unavailable; pace and filler words were not scored.")

        if has_transcript:
            wpm = float(metrics["wpm"])
            if wpm < 110:
                score -= 15
                feedback.append("Pace is slow. Try speaking slightly faster while keeping words clear.")
            elif wpm > 165:
                score -= 15
                feedback.append("Pace is fast. Slow down to make the message easier to follow.")

            fillers_per_minute = float(metrics["filler_count"]) / duration_minutes
            if fillers_per_minute > 4:
                penalty = min(25, int(round(fillers_per_minute * 4)))
                score -= penalty
                feedback.append(
                    f"Frequent fillers detected ({fillers_per_minute:.1f} per minute). "
                    "Try replacing them with a short silent pause."
                )

        pitch_var = float(
            metrics.get("pitch_variation_semitones", metrics.get("pitch_variation", 0)) or 0
        )
        pitch_threshold = 0.3 if "pitch_variation_semitones" in metrics else 15.0
        if pitch_var < pitch_threshold:
            score -= 20
            feedback.append("Pitch varies very little. Add natural emphasis to important words.")

        # 4. Evaluate Pauses / Silences
        pause_ratio = metrics["pause_seconds"] / max(1, metrics["duration_sec"])
        if pause_ratio > 0.35:
            score -= 15
            feedback.append("Too many long pauses detected. Prepare script outline to maintain flow.")

        # Status Classification
        final_score = max(0, score)
        if not has_transcript:
            status = "Partial evidence"
        elif final_score >= 80:
            status = "Pass / Good Speaker"
        elif final_score >= 50:
            status = "Improve"
        else:
            status = "Need to Improve"

        return {
            "speaking_score": final_score,
            "status": status,
            "feedback": " | ".join(feedback) if feedback else "Great delivery! Good pace, vocal variety, and low filler count."
        }