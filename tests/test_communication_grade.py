import unittest

import ollama_grader
from assessment_router import AssessmentRouter
from content_analyzer import ContentAnalyzer
from communication_grade import WeightedCommunicationScorer
from gaze_detector import MediaPipeGazeDetector
from ml_scoring_engine import MLScoringEngine
from ollama_grader import OllamaGrader
from presenter_rubric import PresenterRubric
from speaker_tracker import compare_script
from speech_scorer import SpeakingSkillsScorer


class WeightedCommunicationScorerTests(unittest.TestCase):
    def test_uses_weighted_feature_breakdown_for_good_speaker(self):
        result = WeightedCommunicationScorer.evaluate(
            {
                "avg_sharpness": 450.0,
                "avg_brightness": 140.0,
                "avg_motion": 12.0,
            },
            {
                "wpm": 135,
                "filler_count": 1,
                "pitch_variation": 40.0,
                "pause_seconds": 8,
                "duration_sec": 90,
            },
            script_score=90,
        )

        self.assertGreater(result["overall_score"], 80)
        self.assertIn(result["grade"], {"Excellent", "Strong", "Good"})
        self.assertIn("visual_quality", result["breakdown"])
        self.assertIn("fluency", result["breakdown"])

    def test_penalizes_weak_delivery_and_low_visual_clarity(self):
        result = WeightedCommunicationScorer.evaluate(
            {
                "avg_sharpness": 20.0,
                "avg_brightness": 20.0,
                "avg_motion": 50.0,
            },
            {
                "wpm": 60,
                "filler_count": 12,
                "pitch_variation": 5.0,
                "pause_seconds": 45,
                "duration_sec": 90,
            },
            script_score=25,
        )

        self.assertLess(result["overall_score"], 50)
        self.assertIn("Need to Improve", result["grade"])
        self.assertTrue(result["recommendations"])

    def test_scores_strong_presentation_evidence_in_the_high_band(self):
        transcript = (
            "Today I will explain the topic. First, here is the evidence and data from our "
            "experience. Second, the result demonstrates why we should take action. "
            "Finally, to summarize, thank you."
        )
        content = ContentAnalyzer.analyze(transcript)
        result = WeightedCommunicationScorer.evaluate(
            {
                "duration_sec": 120,
                "resolution": "1920x1080",
                "avg_sharpness": 450,
                "avg_brightness": 140,
                "avg_motion": 8,
            },
            {
                "wpm": 140,
                "word_count": 280,
                "filler_count": 2,
                "pitch_variation": 36,
                "pause_seconds": 6,
                "duration_sec": 120,
                "speech_ratio": 0.86,
                "energy_variation": 0.6,
                "avg_word_prob": 0.9,
            },
            content_analysis=content,
            active_modules=("visual", "audio", "content"),
        )

        self.assertGreaterEqual(result["overall_score"], 80)
        self.assertIn(result["grade"], {"Strong", "Excellent"})

    def test_missing_transcript_is_not_scored_as_zero_pace_or_pronunciation(self):
        result = WeightedCommunicationScorer.evaluate(
            {"avg_sharpness": 0, "avg_brightness": 0, "avg_motion": 0},
            {
                "transcript": "",
                "word_count": 0,
                "wpm": 0,
                "filler_count": 0,
                "pitch_variation": 368.63,
                "pause_seconds": 14.75,
                "duration_sec": 73.77,
                "speech_ratio": 0.8,
                "energy_variation": 0.6,
                "avg_word_prob": 0,
            },
            content_analysis={"available": False, "score": None, "metrics": {}},
            active_modules=("audio",),
        )
        rubric = PresenterRubric.build(result["breakdown"])

        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 100)
        self.assertAlmostEqual(sum(result["overall_metrics"]["weights"].values()), 1.0)
        self.assertIsNone(result["breakdown"]["pronunciation"])
        self.assertIsNone(result["breakdown"]["visual_quality"])
        self.assertIsNone(result["breakdown"]["message_structure"])
        self.assertEqual(result["rates_per_minute"]["fillers"], None)
        self.assertFalse(any("pacing toward" in item for item in result["recommendations"]))
        self.assertFalse(any("articulation" in item for item in result["recommendations"]))
        self.assertIsNone(next(item for item in rubric["dimensions"] if item["key"] == "articulation")["score"])

    def test_script_only_content_is_not_marked_as_skipped(self):
        analysis = ContentAnalyzer.analyze("", script_score=72)
        router = AssessmentRouter.select(
            {"duration_sec": 120, "resolution": "1920x1080"},
            {"duration_sec": 90, "word_count": 0, "speech_ratio": 0.6, "pitch_variation": 10},
            analysis,
            {"available": True, "samples": 10},
            ml_available=False,
        )

        self.assertTrue(analysis["available"])
        self.assertEqual(analysis["score"], 72)
        self.assertIn("content", router["active"])

    def test_partial_but_usable_evidence_is_not_dropped(self):
        router = AssessmentRouter.select(
            {
                "duration_sec": 12,
                "resolution": "0x0",
                "avg_sharpness": 25,
                "avg_brightness": 55,
                "avg_motion": 6,
            },
            {
                "duration_sec": 18,
                "word_count": 8,
                "speech_ratio": 0.08,
                "pitch_variation": 2,
                "energy_variation": 0.1,
                "avg_word_prob": 0.7,
            },
            {"available": True, "score": 66, "metrics": {}},
            {"available": True, "samples": 2, "reading_confidence_score": 18},
            ml_available=True,
        )

        self.assertIn("visual", router["active"])
        self.assertIn("content", router["active"])
        self.assertIn("gaze", router["active"])
        self.assertNotIn("learned", router["active"])

    def test_available_facial_movement_is_routed_as_its_own_evidence(self):
        router = AssessmentRouter.select(
            {"duration_sec": 20, "resolution": "640x480"},
            {"duration_sec": 20, "speech_ratio": 0.8},
            {"available": False, "score": None},
            {
                "available": False,
                "facial_expressiveness_available": True,
                "facial_expression_samples": 12,
                "facial_expressiveness_score": 88.0,
            },
            ml_available=False,
        )

        self.assertIn("expression", router["active"])
        self.assertNotIn("gaze", router["active"])
        self.assertIn("does not infer motivation", router["reasons"]["expression"])

    def test_good_evidence_scores_above_poor_evidence_and_exposes_math(self):
        strong_content = ContentAnalyzer.analyze(
            "Today I will explain our topic. First, research and data show the result. "
            "Second, for example we should act. Finally, to summarize, thank you."
        )
        weak_content = ContentAnalyzer.analyze("um like bad words.")
        strong = WeightedCommunicationScorer.evaluate(
            {"avg_sharpness": 450, "avg_brightness": 140, "avg_motion": 6},
            {
                "transcript": "today first example finally",
                "word_count": 240,
                "wpm": 140,
                "filler_count": 1,
                "duration_sec": 100,
                "pause_seconds": 5,
                "pitch_variation": 30,
                "pitch_variation_semitones": 1.8,
                "energy_variation": 0.55,
                "speech_ratio": 0.9,
                "avg_word_prob": 0.9,
            },
            content_analysis=strong_content,
            active_modules=("visual", "audio", "content", "expression"),
            expression_metrics={
                "facial_expressiveness_available": True,
                "facial_expressiveness_score": 90,
            },
        )
        weak = WeightedCommunicationScorer.evaluate(
            {"avg_sharpness": 20, "avg_brightness": 20, "avg_motion": 50},
            {
                "transcript": "um like bad words",
                "word_count": 20,
                "wpm": 60,
                "filler_count": 15,
                "duration_sec": 60,
                "pause_seconds": 40,
                "pitch_variation": 2,
                "pitch_variation_semitones": 0.1,
                "energy_variation": 0.05,
                "speech_ratio": 0.3,
                "avg_word_prob": 0.3,
            },
            content_analysis=weak_content,
            active_modules=("visual", "audio", "content", "expression"),
            expression_metrics={
                "facial_expressiveness_available": True,
                "facial_expressiveness_score": 75,
            },
        )

        self.assertGreater(strong["overall_score"], weak["overall_score"])
        self.assertAlmostEqual(sum(strong["overall_metrics"]["weights"].values()), 1.0)
        contribution_total = sum(strong["overall_metrics"]["weighted_contributions"].values())
        self.assertAlmostEqual(contribution_total, strong["overall_score"], delta=1.0)
        self.assertIn("content_quality", strong["overall_metrics"]["scores"])
        self.assertIn("recognition_confidence", strong["overall_metrics"]["scores"])
        self.assertAlmostEqual(strong["overall_metrics"]["coverage_percent"], 90.0)

    def test_content_score_rewards_real_structure_and_penalizes_filler_rambling(self):
        strong = ContentAnalyzer.analyze(
            "Today I will explain why we need clean water. First, our research shows "
            "illness fell by 30 percent after the new filters were installed. For example, "
            "one school reduced absences from 20 to 8 each month. Second, the filters cost "
            "less than bottled water and can be maintained locally. What can our community "
            "do? We should fund three pilot sites this year. Finally, to summarize, clean "
            "water improves health and school attendance. Thank you."
        )
        weak = ContentAnalyzer.analyze(
            "Um like so this is thing and thing is really thing and you know basically "
            "maybe it is good and bad and then thing um like thing. It is what it is and "
            "I think you know."
        )

        self.assertGreaterEqual(strong["score"], 85)
        self.assertLessEqual(weak["score"], 45)
        self.assertGreaterEqual(strong["score"] - weak["score"], 40)
        self.assertFalse(weak["metrics"]["structure_markers"]["sequence"])
        self.assertGreater(len(weak["metrics"]["repeated_terms"]), 0)

    def test_zero_content_subscores_are_not_replaced_by_fallback_score(self):
        result = WeightedCommunicationScorer.evaluate(
            {},
            {"duration_sec": 60, "speech_ratio": 0.5},
            content_analysis={
                "available": True,
                "score": 40,
                "metrics": {
                    "structure_score": 0,
                    "clarity_score": 0,
                    "evidence_score": 0,
                    "engagement_score": 0,
                },
            },
            active_modules=("content",),
        )

        self.assertEqual(result["breakdown"]["message_structure"], 0)
        self.assertEqual(result["breakdown"]["message_clarity"], 0)
        self.assertEqual(result["breakdown"]["evidence"], 0)

    def test_skill_coaching_uses_measured_evidence_and_gives_practice_targets(self):
        content = ContentAnalyzer.analyze(
            "The project exists. It needs work. The team has no data."
        )
        result = WeightedCommunicationScorer.evaluate(
            {"avg_sharpness": 280, "avg_brightness": 140, "avg_motion": 5},
            {
                "transcript": "The project exists. It needs work. The team has no data.",
                "word_count": 11,
                "wpm": 190,
                "filler_count": 4,
                "duration_sec": 30,
                "pause_seconds": 2,
                "speech_ratio": 0.8,
                "energy_variation": 0.4,
            },
            content_analysis=content,
            active_modules=("audio", "content", "visual"),
        )

        plan = result["skill_coaching"]
        self.assertTrue(plan)
        self.assertLessEqual(len(plan), 3)
        pace = next(item for item in plan if item["area"] == "Speaking pace")
        self.assertIn("190 words per minute", pace["observed"])
        self.assertTrue(pace["practice"])
        self.assertTrue(pace["target"])
        self.assertTrue(any(item["area"] == "Talk structure" for item in plan))

    def test_optional_unavailable_metrics_are_not_forced_into_grading(self):
        selection = AssessmentRouter.select(
            {"duration_sec": 30, "resolution": "1280x720", "avg_sharpness": 0, "avg_brightness": 0, "avg_motion": 0},
            {"transcript": "Today I speak.", "word_count": 3, "wpm": 60, "speech_ratio": 0.5},
            ContentAnalyzer.analyze("Today I speak."),
            {"available": False, "samples": 0, "facial_expressiveness_available": False},
            ml_available=False,
        )

        self.assertIn("visual", selection["active"])
        self.assertIn("audio", selection["active"])
        self.assertIn("content", selection["active"])
        self.assertNotIn("gaze", selection["active"])
        self.assertNotIn("expression", selection["active"])
        self.assertIn("3 usable face samples", selection["reasons"]["gaze"])
        self.assertIn("verified human-scored examples", selection["reasons"]["learned"])

    def test_missing_transcript_recommendation_is_actionable_not_a_skip_notice(self):
        result = WeightedCommunicationScorer.evaluate(
            {},
            {
                "transcript": "",
                "word_count": 0,
                "wpm": 0,
                "filler_count": 0,
                "duration_sec": 60,
                "speech_ratio": 0.5,
                "pause_seconds": 10,
            },
            content_analysis={"available": False, "score": None, "metrics": {}},
            active_modules=("audio",),
        )

        self.assertTrue(result["recommendations"])
        self.assertTrue(
            any("three-part talk" in item.lower() for item in result["recommendations"])
        )
        self.assertFalse(
            any("scoring was skipped" in item.lower() for item in result["recommendations"])
        )
        self.assertEqual(result["skill_coaching"][0]["area"], "Three-part talk practice")
        self.assertIn("60 seconds", result["skill_coaching"][0]["practice"])

    def test_neutral_face_is_not_treated_as_negative_emotion(self):
        neutral = [
            {name: 0.0 for name in MediaPipeGazeDetector.EXPRESSION_BLENDSHAPES}
            for _ in range(6)
        ]
        moving = [
            {
                name: 0.0 if index % 2 == 0 else 0.5
                for name in MediaPipeGazeDetector.EXPRESSION_BLENDSHAPES
            }
            for index in range(6)
        ]
        neutral_result = MediaPipeGazeDetector._expression_result(neutral)
        moving_result = MediaPipeGazeDetector._expression_result(moving)

        self.assertTrue(neutral_result["facial_expressiveness_available"])
        self.assertEqual(neutral_result["facial_expressiveness_score"], 75.0)
        self.assertGreater(
            moving_result["facial_expressiveness_score"],
            neutral_result["facial_expressiveness_score"],
        )

    def test_synthetic_or_unverified_model_cannot_change_rank(self):
        self.assertFalse(
            MLScoringEngine._is_rank_eligible({
                "production_calibrated": True,
                "training_source": "synthetic offline calibration data",
            })
        )
        self.assertFalse(
            MLScoringEngine._is_rank_eligible({
                "production_calibrated": False,
                "training_source": "labeled.csv",
            })
        )
        self.assertTrue(
            MLScoringEngine._is_rank_eligible({
                "production_calibrated": True,
                "training_source": "verified_human_labeled.csv",
            })
        )

    def test_silent_video_is_not_mistaken_for_audio_evidence(self):
        router = AssessmentRouter.select(
            {},
            {
                "transcript": "",
                "duration_sec": 120,
                "word_count": 0,
                "wpm": 0,
                "speech_ratio": 0,
                "pitch_variation": 0,
                "energy_variation": 0,
                "avg_word_prob": 0,
            },
            {"available": False, "score": None},
            {},
            ml_available=False,
        )

        self.assertNotIn("audio", router["active"])

    def test_script_adherence_is_unavailable_without_transcribed_speech(self):
        result = compare_script("", "Today I will explain the results.")

        self.assertTrue(result["provided"])
        self.assertIsNone(result["score"])
        self.assertEqual(result["status"], "Transcript unavailable")

    def test_missing_transcript_cannot_receive_a_full_speaking_score(self):
        result = SpeakingSkillsScorer.evaluate({
            "transcript": "",
            "word_count": 0,
            "wpm": 0,
            "filler_count": 0,
            "pitch_variation": 40,
            "pause_seconds": 0,
            "duration_sec": 60,
        })

        self.assertLessEqual(result["speaking_score"], 60)
        self.assertEqual(result["status"], "Partial evidence")

    def test_uses_historical_calibration_when_available(self):
        result = WeightedCommunicationScorer.evaluate(
            {
                "avg_sharpness": 260.0,
                "avg_brightness": 130.0,
                "avg_motion": 8.0,
            },
            {
                "wpm": 125,
                "filler_count": 2,
                "pitch_variation": 30.0,
                "pause_seconds": 10,
                "duration_sec": 90,
            },
            script_score=75,
            historical_scores=[70, 72, 78, 80],
        )

        self.assertIsInstance(result["overall_score"], int)
        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 100)
        self.assertTrue(result["recommendations"])

    def test_ollama_grader_uses_local_only_config_and_falls_back_offline(self):
        grader = OllamaGrader()

        self.assertTrue(
            grader.base_url.startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0", "http://[::1]"))
        )
        self.assertFalse(grader.base_url.startswith("https://"))
        self.assertFalse(hasattr(ollama_grader, "requests"))

        result = grader.review("demo.mp4", {"avg_sharpness": 400.0}, {"overall_score": 85})

        self.assertIn(result["summary"].lower(), ["offline review complete for demo.mp4. the deterministic grading engine remains the final source of truth for this assessment.", "review completed."])
        self.assertIn("strengths", result)
        self.assertIn("improvements", result)


if __name__ == "__main__":
    unittest.main()
