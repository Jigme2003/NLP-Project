class WeightedCommunicationScorer:
    """Transparent weighted speaker communication scoring model.

    This project does not use pretrained model weights. Instead it converts the
    extracted video/audio features into explainable weighted scores for visual
    quality, speaking flow, pronunciation proxy, and presentation clarity.
    Each assessment is independent and uses only the supplied presentation features.
    """

    @staticmethod
    def _clamp(value, minimum=0, maximum=100):
        return max(minimum, min(maximum, value))

    @staticmethod
    def _sharpness_score(sharpness):
        if sharpness <= 0:
            return 20
        if sharpness < 100:
            return 30 + (sharpness / 100.0) * 30
        if sharpness < 300:
            return 60 + ((sharpness - 100) / 200.0) * 35
        return 100

    @staticmethod
    def _brightness_score(brightness):
        if brightness < 30:
            return max(0, 100 - (30 - brightness) * 2.2)
        if brightness <= 200:
            return 100
        return max(0, 100 - (brightness - 200) * 0.7)

    @staticmethod
    def _stability_score(motion):
        if motion <= 8:
            return 100
        if motion <= 20:
            return max(0, 100 - (motion - 8) * 4)
        return max(0, 52 - (motion - 20) * 2.5)

    @staticmethod
    def _pace_score(wpm):
        if 120 <= wpm <= 160:
            return 100
        if wpm <= 0:
            return 55
        diff = min(abs(wpm - 140), 80)
        return max(0, 100 - diff * 1.1)

    @staticmethod
    def _filler_score(fillers_per_minute):
        return max(0, 100 - fillers_per_minute * 10)

    @staticmethod
    def _pitch_score(pitch_variation):
        if pitch_variation <= 0:
            return 20
        return WeightedCommunicationScorer._clamp((pitch_variation / 45.0) * 100)

    @staticmethod
    def _pause_score(pause_seconds, duration_sec):
        if duration_sec <= 0:
            return 50
        pause_ratio = pause_seconds / duration_sec
        return WeightedCommunicationScorer._clamp(100 - max(0, pause_ratio - 0.12) * 100)

    @staticmethod
    def _speech_presence_score(speech_metrics):
        ratio = float(speech_metrics.get("speech_ratio", 0) or 0)
        energy_variation = float(speech_metrics.get("energy_variation", 0) or 0)
        activity_score = ratio * 100
        energy_score = min(100, energy_variation * 55)
        return WeightedCommunicationScorer._clamp(activity_score * 0.75 + energy_score * 0.25)

    @staticmethod
    def _vocal_expression_score(speech_metrics):
        if "pitch_variation_semitones" in speech_metrics:
            pitch = float(speech_metrics.get("pitch_variation_semitones", 0) or 0)
            pitch_score = WeightedCommunicationScorer._clamp((pitch - 0.3) / 2.2 * 100)
        else:
            pitch_score = WeightedCommunicationScorer._pitch_score(
                float(speech_metrics.get("pitch_variation", 0) or 0)
            )
        energy_score = WeightedCommunicationScorer._clamp(
            float(speech_metrics.get("energy_variation", 0) or 0) / 0.8 * 100
        )
        return WeightedCommunicationScorer._clamp(pitch_score * 0.6 + energy_score * 0.4)

    @staticmethod
    def _pronunciation_proxy(speech_metrics):
        has_transcript = (
            int(speech_metrics.get("word_count", 0) or 0) > 0
            or float(speech_metrics.get("wpm", 0) or 0) > 0
            or bool(str(speech_metrics.get("transcript", "") or "").strip())
        )
        if not has_transcript:
            return None

        wpm = float(speech_metrics.get("wpm", 0) or 0)
        fillers = int(speech_metrics.get("filler_count", 0) or 0)
        pauses = float(speech_metrics.get("pause_seconds", 0) or 0)
        duration = float(speech_metrics.get("duration_sec", 1) or 1)
        pitch = float(speech_metrics.get("pitch_variation", 0) or 0)

        duration_minutes = max(duration / 60.0, 1 / 60.0)
        filler_penalty = (fillers / duration_minutes) * 7
        pause_penalty = (pauses / duration_minutes) * (50 / 60.0)
        pace_penalty = max(0, abs(wpm - 140) * 0.35)
        tone_bonus = min(15, pitch * 0.2)
        score = 100 - filler_penalty - pause_penalty - pace_penalty + tone_bonus
        return WeightedCommunicationScorer._clamp(score)

    @staticmethod
    def _grade_from_score(score):
        if score >= 90:
            return "Excellent"
        if score >= 80:
            return "Strong"
        if score >= 70:
            return "Good"
        if score >= 60:
            return "Fair"
        return "Need to Improve"

    @staticmethod
    def _tailored_recommendations(
        speech_metrics,
        visual_quality,
        message_structure,
        message_clarity,
        evidence_score,
        audience_engagement,
        fluency_score,
        pronunciation_score,
        confidence_score,
        speech_presence_score,
        script_score=None,
        ml_score=None,
        active=None,
    ):
        active = set(active or ())
        recommendations = []
        wpm = float((speech_metrics or {}).get("wpm", 0) or 0)
        has_transcript = (
            int((speech_metrics or {}).get("word_count", 0) or 0) > 0
            or wpm > 0
            or bool(str((speech_metrics or {}).get("transcript", "") or "").strip())
        )
        filler_count = float((speech_metrics or {}).get("filler_count", 0) or 0)
        pause_seconds = float((speech_metrics or {}).get("pause_seconds", 0) or 0)
        duration_sec = max(float((speech_metrics or {}).get("duration_sec", 1) or 1), 1)
        pause_ratio = pause_seconds / duration_sec
        fillers_per_minute = float((speech_metrics or {}).get("fillers_per_minute", 0) or 0)
        if has_transcript and not fillers_per_minute and wpm:
            duration_minutes = max(duration_sec / 60.0, 1 / 60.0)
            fillers_per_minute = filler_count / duration_minutes

        if "audio" in active and has_transcript and fillers_per_minute > 6:
            recommendations.append(
                f"Trim filler words: your delivery is currently around {fillers_per_minute:.1f} fillers per minute, so cutting the hesitations will make the message feel more decisive."
            )
        if "audio" in active and pause_ratio > 0.25:
            recommendations.append(
                f"Reduce extended silence between points; about {pause_ratio:.0%} of this presentation is currently pause time."
            )
        if "audio" in active and has_transcript and (wpm < 110 or wpm > 165):
            recommendations.append(
                f"Adjust pacing toward a stronger speaking rhythm; the current rate is {wpm:.0f} wpm and would benefit from a steadier, more deliberate cadence."
            )
        if "content" in active and message_structure is not None and message_structure < 72:
            recommendations.append(
                f"Strengthen the opening and structure so the core point lands sooner; the current message structure is only {message_structure:.0f}/100."
            )
        if "content" in active and message_clarity is not None and message_clarity < 72:
            recommendations.append(
                f"Simplify the wording and keep each point to one clear message; the current clarity score is {message_clarity:.0f}/100."
            )
        if "visual" in active and visual_quality < 72:
            recommendations.append(
                f"Improve lighting and framing: the visual signal is only {visual_quality:.0f}/100, which is making the presentation look less polished than the message itself."
            )
        if "audio" in active and confidence_score < 72:
            recommendations.append(
                f"Project more assurance in the first 20 seconds and keep the energy steady; confidence is currently {confidence_score:.0f}/100."
            )
        if "audio" in active and pronunciation_score is not None and pronunciation_score < 72:
            recommendations.append(
                f"Work on clearer articulation and more controlled emphasis, because pronunciation is landing at {pronunciation_score:.0f}/100."
            )
        if "audio" in active and fluency_score < 72:
            recommendations.append(
                f"Reduce speaker drift and filler bursts to improve flow; delivery is currently operating at {fluency_score:.0f}/100."
            )
        if "content" in active and evidence_score is not None and evidence_score < 72:
            recommendations.append(
                "Support your main claim with a concrete example, result, or audience-relevant proof point to make the argument feel stronger and more credible."
            )
        if "content" in active and audience_engagement is not None and audience_engagement < 72:
            recommendations.append(
                "Create a stronger audience hook and final call to action so the presentation feels more engaging and persuasive from start to finish."
            )
        if "content" in active and script_score is not None and script_score < 72:
            recommendations.append(
                f"Align the delivered message more closely with the prepared script; current script adherence is {script_score:.0f}/100, so tighten the phrasing and emphasis."
            )
        if "learned" in active and ml_score is not None and ml_score < 60:
            recommendations.append(
                f"The learned quality signal is weaker than expected at {ml_score:.0f}/100, so focus on cleaner pacing, stronger structure, and more confident delivery."
            )
        if "audio" in active and speech_presence_score < 63:
            recommendations.append(
                "Check microphone placement and room noise so the voice remains consistent and clean throughout the presentation."
            )
        if "content" not in active:
            recommendations.append(
                "Practice a three-part talk: open with one sentence stating your main idea, support it with two ordered points and a specific example, then close with one takeaway for the audience."
            )
        if not recommendations:
            recommendations.append("Strong presentation profile. Keep this pacing and structure consistent and protect the delivery rhythm in the next take.")
        deduped = []
        seen = set()
        for item in recommendations:
            key = item.lower()
            if key not in seen:
                deduped.append(item)
                seen.add(key)
        return deduped[:5]

    @staticmethod
    def _skill_coaching_plan(
        speech_metrics,
        visual_metrics,
        content_analysis,
        active_modules,
    ):
        active = set(active_modules or ())
        content_metrics = (content_analysis or {}).get("metrics", {})
        plan = []
        has_transcript = (
            int((speech_metrics or {}).get("word_count", 0) or 0) > 0
            or bool(str((speech_metrics or {}).get("transcript", "") or "").strip())
        )

        def add(priority, area, observed, action, drill, target):
            plan.append({
                "priority": priority,
                "area": area,
                "observed": observed,
                "action": action,
                "practice": drill,
                "target": target,
            })

        if "audio" in active and has_transcript:
            wpm = float((speech_metrics or {}).get("wpm", 0) or 0)
            if wpm > 0 and not 120 <= wpm <= 160:
                direction = "slow down" if wpm > 160 else "increase pace slightly"
                add(
                    1,
                    "Speaking pace",
                    f"Transcript pace measured at {wpm:.0f} words per minute.",
                    f"Try to {direction}, while keeping pauses between ideas.",
                    "Rehearse one 60-second section, record it, and count the words; repeat once with deliberate pauses.",
                    "Use 120–160 words per minute as a practice reference, not a universal pass/fail rule.",
                )

            duration_minutes = max(
                float((speech_metrics or {}).get("duration_sec", 1) or 1) / 60.0,
                1 / 60.0,
            )
            fillers_per_minute = float((speech_metrics or {}).get("filler_count", 0) or 0) / duration_minutes
            if fillers_per_minute > 6:
                add(
                    1,
                    "Filler words",
                    f"About {fillers_per_minute:.1f} detected fillers per minute.",
                    "Replace habitual fillers with a short, silent breath; do not rush to fill every pause.",
                    "Mark each filler on a transcript during a one-minute practice take, then repeat the same section.",
                    "Aim to reduce the count on the next take without increasing speaking speed.",
                )

            duration = max(float((speech_metrics or {}).get("duration_sec", 1) or 1), 1)
            pause_ratio = float((speech_metrics or {}).get("pause_seconds", 0) or 0) / duration
            if pause_ratio > 0.25:
                add(
                    2,
                    "Pause control",
                    f"Detected silence accounts for about {pause_ratio:.0%} of analyzed audio.",
                    "Keep purposeful pauses after key points, and check whether long gaps are recording silence.",
                    "Rehearse with a marked outline and pause only at section breaks; compare the recording with the outline.",
                    "Preserve emphasis pauses while reducing unintended gaps.",
                )

        if "content" in active and content_metrics:
            markers = content_metrics.get("structure_markers", {})
            missing_sections = [
                label for key, label in (
                    ("opening", "opening"),
                    ("sequence", "ordered points"),
                    ("closing", "conclusion"),
                )
                if key in markers and not markers[key]
            ]
            if missing_sections:
                add(
                    1,
                    "Talk structure",
                    "The transcript analyzer did not detect: " + ", ".join(missing_sections) + ".",
                    "Make the main idea explicit, order the supporting points, and finish with a one-sentence takeaway.",
                    "Write a three-line outline: audience hook, one main idea with two ordered points, and a closing takeaway.",
                    "Use the outline as a rehearsal aid; transcript cues can miss phrasing and do not judge delivery quality.",
                )

            clarity = float(content_metrics.get("clarity_score", 100) or 0)
            if clarity < 72:
                sentence_length = float(content_metrics.get("average_sentence_length", 0) or 0)
                add(
                    2,
                    "Sentence clarity",
                    f"Average transcript sentence length is {sentence_length:.1f} words (clarity proxy {clarity:.0f}/100).",
                    "Split long sentences into one claim at a time and leave a beat between ideas.",
                    "Rewrite the longest sentence in the transcript as two short sentences, then say them aloud.",
                    "Compare the revised take for shorter, easier-to-follow sentences.",
                )

            evidence = float(content_metrics.get("evidence_score", 100) or 0)
            if evidence < 72:
                add(
                    2,
                    "Supporting evidence",
                    "The transcript contains few recognizable evidence or example cues.",
                    "Add one specific example, result, or named source that directly supports the central claim.",
                    "For each key claim, write one sentence answering: what example or source would help the audience verify this?",
                    "Check that the example is relevant and the source or number is accurate.",
                )

        if "content" not in active:
            add(
                1,
                "Three-part talk practice",
                "A transcript was not available to assess message structure.",
                "Practice one main idea, two supporting points, and a clear audience takeaway.",
                "Write a three-line outline, deliver it in 60 seconds, then replay the video and check that each point is easy to follow.",
                "Keep the main idea to one sentence and make the closing takeaway explicit.",
            )

        if "visual" in active:
            brightness = float((visual_metrics or {}).get("avg_brightness", 0) or 0)
            sharpness = float((visual_metrics or {}).get("avg_sharpness", 0) or 0)
            if brightness < 50 or brightness > 200:
                advice = "Add soft light in front of you" if brightness < 50 else "Reduce the light or exposure"
                add(
                    1,
                    "Lighting",
                    f"Average frame brightness measured at {brightness:.0f}/255.",
                    f"{advice} and keep the background from being much brighter than your face.",
                    "Record a 10-second test clip, review the face exposure, and adjust one light at a time.",
                    "Recheck the next clip for a clearly visible face without washed-out highlights.",
                )
            if sharpness < 100:
                add(
                    2,
                    "Camera focus",
                    f"Average frame sharpness measured at {sharpness:.0f}.",
                    "Clean the lens, stabilize the camera, and check focus before recording.",
                    "Record a short test and inspect the eyes and face at normal playback size.",
                    "Aim for a clearly focused face; the sharpness score is a technical proxy.",
                )

        plan.sort(key=lambda item: item["priority"])
        return plan[:3]

    @classmethod
    def evaluate(
        cls,
        visual_metrics,
        speech_metrics,
        script_score=None,
        historical_scores=None,
        content_analysis=None,
        gaze_metrics=None,
        ml_score=None,
        active_modules=None,
        expression_metrics=None,
    ):
        gaze_metrics = gaze_metrics or {}
        expression_metrics = expression_metrics or gaze_metrics
        visual_quality = (
            cls._sharpness_score(float(visual_metrics.get("avg_sharpness", 0))) * 0.40
            + cls._brightness_score(float(visual_metrics.get("avg_brightness", 0))) * 0.30
            + cls._stability_score(float(visual_metrics.get("avg_motion", 0))) * 0.30
        )

        has_transcript = (
            int(speech_metrics.get("word_count", 0) or 0) > 0
            or float(speech_metrics.get("wpm", 0) or 0) > 0
            or bool(str(speech_metrics.get("transcript", "") or "").strip())
        )
        duration_minutes = max(float(speech_metrics.get("duration_sec", 1) or 1) / 60.0, 1 / 60.0)
        pauses_per_minute = float(speech_metrics.get("pause_seconds", 0) or 0) / duration_minutes
        fillers_per_minute = (
            float(speech_metrics.get("filler_count", 0) or 0) / duration_minutes
            if has_transcript
            else None
        )
        speech_presence_score = cls._speech_presence_score(speech_metrics)
        pause_score = cls._pause_score(
            float(speech_metrics.get("pause_seconds", 0) or 0),
            float(speech_metrics.get("duration_sec", 1) or 1),
        )
        pace_score = cls._pace_score(float(speech_metrics.get("wpm", 0) or 0))
        vocal_expression_score = cls._vocal_expression_score(speech_metrics)
        fluency_components = [
            (pause_score, 0.20),
            (speech_presence_score, 0.20),
        ]
        if has_transcript:
            fluency_components.extend([
                (pace_score, 0.35),
                (cls._filler_score(fillers_per_minute), 0.25),
            ])
        fluency_score = sum(score * weight for score, weight in fluency_components) / sum(
            weight for _, weight in fluency_components
        )

        pronunciation_score = cls._pronunciation_proxy(speech_metrics)
        confidence_components = [
            (pause_score, 0.20),
            (vocal_expression_score, 0.30),
            (speech_presence_score, 0.20),
        ]
        if has_transcript:
            confidence_components.extend([
                (pace_score, 0.15),
                (cls._filler_score(fillers_per_minute), 0.15),
            ])
        confidence_score = cls._clamp(
            sum(score * weight for score, weight in confidence_components)
            / sum(weight for _, weight in confidence_components)
        )

        content_component = 45.0
        content_available = False
        if content_analysis and content_analysis.get("score") is not None:
            content_component = float(content_analysis["score"])
            content_available = bool(content_analysis.get("available", True))
        elif script_score is not None:
            content_component = float(script_score)
            content_available = True

        content_metrics = (content_analysis or {}).get("metrics", {})
        if content_available:
            message_structure = float(content_metrics.get("structure_score", content_component))
            message_clarity = float(content_metrics.get("clarity_score", content_component))
            evidence_score = float(content_metrics.get("evidence_score", content_component))
            audience_engagement = cls._clamp(
                float(content_metrics.get("engagement_score", content_component)) * 0.65
                + vocal_expression_score * 0.35
            )
        else:
            message_structure = None
            message_clarity = None
            evidence_score = None
            audience_engagement = None
        active = set(
            ("visual", "audio", "content", "gaze", "learned")
            if active_modules is None
            else active_modules
        )
        overall_metrics = {}
        overall_weights = {}

        def add_metric(name, score, weight):
            overall_metrics[name] = cls._clamp(score)
            overall_weights[name] = weight

        if "visual" in active:
            add_metric("visual_quality", visual_quality, 0.08)
        if "content" in active and content_available:
            add_metric("content_quality", content_component, 0.20)
        if "audio" in active:
            add_metric("fluency", fluency_score, 0.20)
            if pronunciation_score is not None:
                add_metric("pronunciation", pronunciation_score, 0.10)
            add_metric("confidence", confidence_score, 0.12)
            add_metric("vocal_expression", vocal_expression_score, 0.10)
            if float(speech_metrics.get("avg_word_prob", 0) or 0) > 0:
                add_metric(
                    "recognition_confidence",
                    float(speech_metrics["avg_word_prob"]) * 100,
                    0.05,
                )
        if script_score is not None and has_transcript and "content" in active:
            add_metric("script_adherence", script_score, 0.03)
        if ml_score is not None and "learned" in active:
            overall_metrics["learned_score"] = cls._clamp(float(ml_score))
            overall_weights["learned_score"] = 0.03
        if gaze_metrics and gaze_metrics.get("available") and "gaze" in active:
            overall_metrics["gaze_quality"] = cls._clamp(100 - float(gaze_metrics.get("reading_confidence_score", 0) or 0))
            overall_weights["gaze_quality"] = 0.04
        if (
            "expression" in active
            and expression_metrics.get("facial_expressiveness_available")
            and expression_metrics.get("facial_expressiveness_score") is not None
        ):
            add_metric(
                "facial_expressiveness",
                float(expression_metrics["facial_expressiveness_score"]),
                0.05,
            )
        configured_weight_total = sum(overall_weights.values())
        weighted_score = (
            sum(overall_metrics[name] * weight for name, weight in overall_weights.items())
            / configured_weight_total
        ) if configured_weight_total else 0
        normalized_weights = {
            name: weight / configured_weight_total
            for name, weight in overall_weights.items()
        } if configured_weight_total else {}
        contributions = {
            name: overall_metrics[name] * normalized_weights[name]
            for name in overall_metrics
        }

        overall_score = round(cls._clamp(weighted_score))
        raw_score = overall_score

        recommendations = cls._tailored_recommendations(
            speech_metrics=speech_metrics,
            visual_quality=visual_quality,
            message_structure=message_structure,
            message_clarity=message_clarity,
            evidence_score=evidence_score,
            audience_engagement=audience_engagement,
            fluency_score=fluency_score,
            pronunciation_score=pronunciation_score,
            confidence_score=confidence_score,
            speech_presence_score=speech_presence_score,
            script_score=script_score,
            ml_score=ml_score,
            active=active,
        )
        skill_coaching = cls._skill_coaching_plan(
            speech_metrics=speech_metrics,
            visual_metrics=visual_metrics,
            content_analysis=content_analysis,
            active_modules=active,
        )

        return {
            "overall_score": overall_score,
            "raw_score": raw_score,
            "grade": cls._grade_from_score(overall_score),
            "overall_metrics": {
                "scores": {name: round(value, 2) for name, value in overall_metrics.items()},
                "weights": normalized_weights,
                "weighted_contributions": {
                    name: round(value, 2) for name, value in contributions.items()
                },
                "weight_total": round(sum(normalized_weights.values()), 4),
                "configured_weight_total": round(configured_weight_total, 2),
                "coverage_percent": round(min(100.0, configured_weight_total * 100), 1),
                "active_modules": sorted(active),
            },
            "weights": normalized_weights,
            "breakdown": {
                "visual_quality": round(cls._clamp(visual_quality), 2) if "visual" in active else None,
                "message_structure": round(cls._clamp(message_structure), 2) if message_structure is not None else None,
                "message_clarity": round(cls._clamp(message_clarity), 2) if message_clarity is not None else None,
                "evidence": round(cls._clamp(evidence_score), 2) if evidence_score is not None else None,
                "fluency": round(cls._clamp(fluency_score), 2),
                "pronunciation": round(cls._clamp(pronunciation_score), 2) if pronunciation_score is not None else None,
                "audience_engagement": round(cls._clamp(audience_engagement), 2) if audience_engagement is not None else None,
                "confidence": round(cls._clamp(confidence_score), 2),
                "speech_presence": round(cls._clamp(speech_presence_score), 2),
                "vocal_expression": round(cls._clamp(vocal_expression_score), 2),
                "facial_expressiveness": (
                    round(cls._clamp(float(expression_metrics.get("facial_expressiveness_score"))), 2)
                    if expression_metrics.get("facial_expressiveness_available")
                    and expression_metrics.get("facial_expressiveness_score") is not None
                    else None
                ),
                "content_quality": round(cls._clamp(content_component), 2) if content_available else None,
                "script_adherence": round(cls._clamp(float(script_score)), 2) if script_score is not None else None,
                "recognition_confidence": (
                    round(cls._clamp(float(speech_metrics["avg_word_prob"]) * 100), 2)
                    if float(speech_metrics.get("avg_word_prob", 0) or 0) > 0
                    else None
                ),
                "gaze_quality": (
                    round(cls._clamp(100 - float(gaze_metrics.get("reading_confidence_score", 0) or 0)), 2)
                    if gaze_metrics.get("available") and "gaze" in active
                    else None
                ),
                "learned_score": (
                    round(cls._clamp(float(ml_score)), 2)
                    if ml_score is not None and "learned" in active
                    else None
                ),
            },
            "recommendations": recommendations,
            "skill_coaching": skill_coaching,
            "historical_calibration": [],
            "rates_per_minute": {
                "fillers": round(fillers_per_minute, 2) if fillers_per_minute is not None else None,
                "pauses": round(pauses_per_minute, 2),
            },
        }
