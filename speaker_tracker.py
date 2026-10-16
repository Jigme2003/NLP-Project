"""Local speaker progress and script-adherence tracking."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

STORAGE_DIR = Path(__file__).resolve().parent / "storage"
STORAGE_DIR.mkdir(exist_ok=True, parents=True)
HISTORY_PATH = STORAGE_DIR / "speaker_progress.json"


def _tokens(text):
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def compare_script(transcript, script):
    expected = _tokens(script)
    spoken = _tokens(transcript)
    if not expected:
        return {
            "provided": False,
            "score": None,
            "status": "No script provided",
            "matched_words": 0,
            "script_words": 0,
            "missing_keywords": [],
        }

    spoken_set = set(spoken)
    if not spoken_set:
        return {
            "provided": True,
            "score": None,
            "status": "Transcript unavailable",
            "matched_words": 0,
            "script_words": len(expected),
            "missing_keywords": [],
        }
    matched_words = sum(1 for word in expected if word in spoken_set)
    score = round((matched_words / len(expected)) * 100)
    missing = []
    for word in expected:
        if len(word) > 4 and word not in spoken_set and word not in missing:
            missing.append(word)
    status = "Strong adherence" if score >= 85 else "Partial adherence" if score >= 60 else "Low adherence"
    return {
        "provided": True,
        "score": score,
        "status": status,
        "matched_words": matched_words,
        "script_words": len(expected),
        "missing_keywords": missing[:8],
    }


def _read_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def record_progress(speaker, report):
    history = _read_history()
    filename = report.get("filename") or report.get("overview", {}).get("filename") or "video"
    entry = {
        "speaker": speaker or "Default speaker",
        "filename": filename,
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_score": report.get("overview", {}).get("overall_score"),
        "speaking_score": report.get("presentation", {}).get("score"),
        "script_adherence": report.get("script_adherence", {}).get("score"),
    }
    history.append(entry)
    with open(HISTORY_PATH, "w", encoding="utf-8") as handle:
        json.dump(history[-100:], handle, indent=2)
    return entry


def progress_for(speaker=None):
    history = _read_history()
    if speaker:
        history = [entry for entry in history if entry["speaker"].lower() == speaker.lower()]
    return history


def historical_scores_for(speaker=None, limit=10):
    history = progress_for(speaker)
    scores = []
    for entry in history[-limit:]:
        value = entry.get("overall_score")
        if value is not None:
            scores.append(float(value))
    return scores
