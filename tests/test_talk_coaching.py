import unittest

from content_analyzer import ContentAnalyzer


class TalkCoachingTests(unittest.TestCase):
    def test_detects_talk_structure_cues_without_creating_a_grade(self):
        result = ContentAnalyzer.analyze_talk(
            "What if we could change this? I remember when I was a student. "
            "The key takeaway is that small steps matter. For example, our study "
            "found a 20% improvement. In conclusion, remember what we can do."
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["signal_count"], 6)
        self.assertEqual(result["total_signals"], 6)
        self.assertTrue(all(signal["detected"] for signal in result["signals"]))
        self.assertNotIn("score", result)

    def test_missing_cues_include_specific_coaching(self):
        result = ContentAnalyzer.analyze_talk(
            "The weather changed. The road was wet. The car stopped."
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["signal_count"], 0)
        self.assertTrue(all(not signal["detected"] for signal in result["signals"]))
        self.assertTrue(all(signal["suggestion"] for signal in result["signals"]))

    def test_empty_transcript_returns_unavailable_coaching(self):
        result = ContentAnalyzer.analyze_talk("  ")

        self.assertFalse(result["available"])
        self.assertEqual(result["signals"], [])
        self.assertIn("does not affect the numeric grade", result["note"])

    def test_content_structure_requires_opening_and_closing_cues_in_their_sections(self):
        result = ContentAnalyzer.analyze(
            "The debate began in a town. Our topic changed later. "
            "First, we reviewed the research. Finally, we discussed the result. "
            "The evidence stayed important."
        )

        self.assertFalse(result["metrics"]["structure_markers"]["opening"])
        self.assertFalse(result["metrics"]["structure_markers"]["closing"])
        self.assertTrue(result["metrics"]["structure_markers"]["sequence"])

    def test_content_sequence_markers_must_appear_in_order(self):
        result = ContentAnalyzer.analyze(
            "First, we reviewed the topic. Finally, we considered the example. "
            "Then we discussed the result."
        )

        self.assertFalse(result["metrics"]["structure_markers"]["sequence"])


if __name__ == "__main__":
    unittest.main()
