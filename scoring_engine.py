class VideoScorer:
    SHARPNESS_LOW = 100.0
    SHARPNESS_GOOD = 300.0
    BRIGHTNESS_LOW = 50.0
    BRIGHTNESS_HIGH = 200.0
    MOTION_STILL = 1.0
    MOTION_HIGH = 25.0

    @staticmethod
    def evaluate(features):
        score = 100
        improvements = []
        classifications = {}

        # Evaluate Sharpness
        sharpness = features["avg_sharpness"]
        if sharpness < VideoScorer.SHARPNESS_LOW:
            score -= 30
            classifications["sharpness"] = "Need to Improve"
            improvements.append("High blur detected. Improve camera focus or lens quality.")
        elif sharpness < VideoScorer.SHARPNESS_GOOD:
            score -= 10
            classifications["sharpness"] = "Improve"
            improvements.append("Slightly soft focus. Enhance lighting or fine-tune focus.")
        else:
            classifications["sharpness"] = "Good"

        # Evaluate Brightness
        brightness = features["avg_brightness"]
        if brightness < VideoScorer.BRIGHTNESS_LOW:
            score -= 25
            classifications["brightness"] = "Need to Improve"
            improvements.append("Video is too dark (under-exposed). Increase lighting.")
        elif brightness > VideoScorer.BRIGHTNESS_HIGH:
            score -= 25
            classifications["brightness"] = "Need to Improve"
            improvements.append("Video is over-exposed. Reduce lighting or lower ISO.")
        else:
            classifications["brightness"] = "Good"

        # Evaluate Motion Stability
        motion = features["avg_motion"]
        if motion > VideoScorer.MOTION_HIGH:
            score -= 20
            classifications["stability"] = "Need to Improve"
            improvements.append("High camera motion/shakiness detected. Use a tripod or image stabilization.")
        elif motion < VideoScorer.MOTION_STILL:
            classifications["stability"] = "Static"
            improvements.append("Video is static. Consider adding movement if visual variety is needed.")
        else:
            classifications["stability"] = "Good"

        # Overall Status Logic
        final_score = max(0, score)
        if final_score >= 80:
            overall_status = "Pass / Good"
        elif final_score >= 50:
            overall_status = "Improve"
        else:
            overall_status = "Need to Improve"

        return {
            "overall_score": final_score,
            "overall_status": overall_status,
            "classifications": classifications,
            "improvements_needed": " | ".join(improvements) if improvements else "None"
        }