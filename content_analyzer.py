"""Explainable content and message-quality analysis for spoken videos."""

import re
from collections import Counter


class ContentAnalyzer:
    STRUCTURE_MARKERS = {
        "opening": ("today", "introduction", "first", "begin", "start", "topic"),
        "sequence": ("first", "second", "then", "next", "finally"),
        "evidence": ("example", "evidence", "data", "result", "research", "experience"),
        "closing": ("finally", "in conclusion", "to summarize", "overall", "thank you"),
    }
    TALK_SIGNALS = (
        (
            "hook",
            "Opening hook",
            ("imagine", "what if", "picture this", "have you ever", "why do we"),
            "Open with an audience-centered question, a vivid image, or a surprising fact.",
        ),
        (
            "idea",
            "One clear idea",
            ("the big idea", "my main point", "the key takeaway", "what i want you to remember", "the idea is"),
            "State one concise idea you want the audience to remember.",
        ),
        (
            "story",
            "Human story",
            ("i remember", "when i was", "i used to", "one day", "years ago", "my first", "my mother", "my father"),
            "Make the idea tangible with a brief personal moment or a specific human example.",
        ),
        (
            "evidence",
            "Evidence or example",
            ("for example", "evidence", "data", "research", "study", "studies", "according to", "the result"),
            "Support the central claim with a concrete example or a source the audience can verify.",
        ),
        (
            "audience",
            "Audience connection",
            (),
            "Connect the idea to the audience's choices, experience, or next step.",
        ),
        (
            "closing",
            "Memorable close",
            ("in conclusion", "to summarize", "thank you", "what i hope", "remember", "take action", "the takeaway"),
            "End with a concise takeaway, a call to action, or a callback to the opening.",
        ),
    )
    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
        "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "we",
        "were", "with", "you", "um", "uh", "like", "know", "actually", "basically", "so",
    }

    @staticmethod
    def _contains_phrase(text, phrase):
        pattern = r"(?<!\w)" + r"\s+".join(re.escape(word) for word in phrase.split()) + r"(?!\w)"
        return re.search(pattern, text) is not None

    @classmethod
    def analyze_talk(cls, transcript):
        """Identify transparent TED-style structure cues without changing the grade."""
        text = " ".join((transcript or "").split())
        words = re.findall(r"[A-Za-z0-9']+", text)
        if not words:
            return {
                "available": False,
                "signal_count": 0,
                "total_signals": len(cls.TALK_SIGNALS),
                "signals": [],
                "note": "A transcript is needed to identify talk-structure cues. This coaching does not affect the numeric grade.",
            }

        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        opening = " ".join(sentences[:2]).lower()
        closing = " ".join(sentences[-2:]).lower()
        lowered_text = text.lower()
        signals = []

        for key, title, markers, suggestion in cls.TALK_SIGNALS:
            evidence = ""
            if key == "hook":
                marker = next((item for item in markers if cls._contains_phrase(opening, item)), None)
                detected = "?" in opening or marker is not None
                if detected:
                    evidence = "A question appears in the opening." if "?" in opening else f"Opening cue: '{marker}'"
            elif key == "idea":
                marker = next((item for item in markers if cls._contains_phrase(lowered_text, item)), None)
                detected = marker is not None
                if marker:
                    evidence = f"Signpost detected: '{marker}'"
            elif key == "story":
                marker = next((item for item in markers if cls._contains_phrase(lowered_text, item)), None)
                detected = marker is not None
                if marker:
                    evidence = f"Narrative cue detected: '{marker}'"
            elif key == "evidence":
                marker = next((item for item in markers if cls._contains_phrase(lowered_text, item)), None)
                detected = marker is not None or re.search(r"\b\d+(?:\.\d+)?%?\b", text) is not None
                if marker:
                    evidence = f"Evidence cue detected: '{marker}'"
                elif detected:
                    evidence = "A number appears in the transcript; its accuracy is not verified."
            elif key == "audience":
                detected = re.search(r"\b(you|your|we|us|our)\b", lowered_text) is not None
                if detected:
                    evidence = "Direct audience language detected (you, your, we, us, or our)."
            else:
                marker = next((item for item in markers if cls._contains_phrase(closing, item)), None)
                detected = marker is not None
                if marker:
                    evidence = f"Closing cue: '{marker}'"

            signals.append({
                "key": key,
                "title": title,
                "detected": detected,
                "evidence": evidence or "No obvious transcript cue detected.",
                "suggestion": suggestion,
            })

        return {
            "available": True,
            "signal_count": sum(signal["detected"] for signal in signals),
            "total_signals": len(signals),
            "signals": signals,
            "note": "These are keyword and structure cues from the transcript, not a judgment of talk quality or factual accuracy. They do not affect the numeric grade.",
        }

    @classmethod
    def analyze(cls, transcript, script_score=None):
        text = " ".join((transcript or "").split())
        words = re.findall(r"[A-Za-z0-9']+", text.lower())
        sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
        content_words = [word for word in words if word not in cls.STOP_WORDS]
        unique_words = set(content_words)
        word_count = len(words)
        sentence_count = len(sentences)
        lexical_diversity = (len(unique_words) / len(content_words)) * 100 if content_words else 0
        average_sentence_length = word_count / sentence_count if sentence_count else 0
        question_count = len(re.findall(r"\?", text))
        action_count = len(re.findall(r"\b(should|need to|must|will|can|recommend)\b", text.lower()))
        lowered_text = text.lower()
        section_size = max(1, (len(sentences) + 4) // 5)
        opening_text = " ".join(sentences[:section_size]).lower()
        closing_text = " ".join(sentences[-section_size:]).lower()
        sequence_positions = []
        for order, marker in enumerate(cls.STRUCTURE_MARKERS["sequence"]):
            match = re.search(
                r"(?<!\w)" + r"\s+".join(re.escape(word) for word in marker.split()) + r"(?!\w)",
                lowered_text,
            )
            if match:
                sequence_positions.append((match.start(), order))
        sequence_positions.sort()
        sequence_is_ordered = (
            len(sequence_positions) >= 2
            and all(
                earlier[1] < later[1]
                for earlier, later in zip(sequence_positions, sequence_positions[1:])
            )
        )
        markers = {
            "opening": any(
                cls._contains_phrase(opening_text, marker)
                for marker in cls.STRUCTURE_MARKERS["opening"]
            ),
            "sequence": sequence_is_ordered,
            "evidence": any(
                cls._contains_phrase(lowered_text, marker)
                for marker in cls.STRUCTURE_MARKERS["evidence"]
            ),
            "closing": any(
                cls._contains_phrase(closing_text, marker)
                for marker in cls.STRUCTURE_MARKERS["closing"]
            ),
        }
        repeated_terms = [
            {"term": term, "count": count}
            for term, count in Counter(content_words).most_common(8)
            if count >= 3
        ]

        if not words:
            if script_score is None:
                return {
                    "available": False,
                    "status": "Transcript unavailable",
                    "score": None,
                    "metrics": {
                        "word_count": 0,
                        "sentence_count": 0,
                        "lexical_diversity": 0,
                        "average_sentence_length": 0,
                        "structure_score": 0,
                        "clarity_score": 0,
                        "vocabulary_score": 0,
                        "evidence_score": 0,
                        "engagement_score": 0,
                        "question_count": 0,
                        "action_language_count": 0,
                        "structure_markers": markers,
                        "repeated_terms": [],
                    },
                    "strengths": [],
                    "improvements": ["Enable or download the local speech model to assess message content and pronunciation."],
                }
            return {
                "available": True,
                "status": "Script-only content signal available",
                "score": round(float(script_score), 1),
                "metrics": {
                    "word_count": 0,
                    "sentence_count": 0,
                    "lexical_diversity": 0,
                    "average_sentence_length": 0,
                    "structure_score": 0,
                    "clarity_score": 0,
                    "vocabulary_score": 0,
                    "evidence_score": 0,
                    "engagement_score": 0,
                    "question_count": 0,
                    "action_language_count": 0,
                    "structure_markers": markers,
                    "repeated_terms": [],
                },
                "strengths": ["The prepared script provides a content baseline for review."],
                "improvements": ["Add a transcript for deeper delivery and clarity feedback."],
            }

        structure_score = sum(markers.values()) / len(markers) * 100
        clarity_score = 100 if 8 <= average_sentence_length <= 28 else max(35, 100 - abs(18 - average_sentence_length) * 3)
        vocabulary_score = min(100, lexical_diversity * 1.35)
        evidence_score = 100 if markers["evidence"] else min(70, 35 + action_count * 8)
        engagement_score = min(100, 35 + question_count * 20 + action_count * 8 + (20 if markers["opening"] else 0) + (15 if markers["closing"] else 0))
        repeated_word_count = sum(item["count"] - 1 for item in repeated_terms)
        repetition_penalty = min(
            25,
            repeated_word_count / max(len(content_words), 1) * 100,
        )
        content_score = round(max(0, min(100, structure_score * 0.25 + clarity_score * 0.25 + vocabulary_score * 0.20 + evidence_score * 0.15 + engagement_score * 0.15 - repetition_penalty)))
        if script_score is not None:
            content_score = round(content_score * 0.75 + float(script_score) * 0.25)

        strengths = []
        improvements = []
        if structure_score >= 60:
            strengths.append("The message shows recognizable organization and progression.")
        if vocabulary_score >= 60:
            strengths.append("The speaker uses a reasonably varied vocabulary.")
        if clarity_score < 70:
            improvements.append("Use shorter, clearer sentences and pause between major ideas.")
        if structure_score < 60:
            improvements.append("Add a clear opening, ordered points, supporting example, and concise conclusion.")
        if repetition_penalty:
            improvements.append("Reduce repeated terms and replace them with precise wording.")
        if script_score is not None and script_score < 70:
            improvements.append("Keep the main message closer to the intended topic and key points.")
        if not strengths:
            strengths.append("The transcript provides a basis for targeted content feedback.")
        if not improvements:
            improvements.append("Content structure and clarity are consistent; continue strengthening evidence and examples.")

        return {
            "available": True,
            "status": "Content analyzed",
            "score": content_score,
            "metrics": {
                "word_count": word_count,
                "sentence_count": sentence_count,
                "lexical_diversity": round(lexical_diversity, 1),
                "average_sentence_length": round(average_sentence_length, 1),
                "structure_score": round(structure_score, 1),
                "clarity_score": round(clarity_score, 1),
                "vocabulary_score": round(vocabulary_score, 1),
                "evidence_score": round(evidence_score, 1),
                "engagement_score": round(engagement_score, 1),
                "question_count": question_count,
                "action_language_count": action_count,
                "structure_markers": markers,
                "repeated_terms": repeated_terms,
            },
            "strengths": strengths,
            "improvements": improvements,
        }
