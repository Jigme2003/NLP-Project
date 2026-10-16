"""Train the local presentation scorer from a labeled CSV dataset.

Example:
    python train_model.py data/presentation_scores.csv --target score
"""

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from ml_scoring_engine import MLScoringEngine


def generate_synthetic_data(rows=1200, random_state=42):
    generator = __import__("numpy").random.default_rng(random_state)
    frame = pd.DataFrame({
        "wpm": generator.normal(138, 18, rows).clip(70, 210),
        "fillers_per_min": generator.gamma(shape=2.2, scale=2.0, size=rows).clip(0, 10),
        "pitch_std": generator.normal(26, 11, rows).clip(5, 55),
        "pause_ratio": generator.beta(2.5, 5.0, rows).clip(0.03, 0.45),
        "gaze_variance": generator.beta(2.0, 10.0, rows).clip(0.0, 0.12),
        "avg_word_prob": generator.beta(4.5, 2.0, rows).clip(0.35, 0.98),
    })

    pace = 100 - abs(frame["wpm"] - 140) * 0.75
    articulation = 100 - frame["fillers_per_min"] * 7.5
    pitch_signal = (frame["pitch_std"].clip(0, 45) / 45) * 100
    pause_signal = (100 - frame["pause_ratio"] * 180).clip(0, 100)
    gaze_signal = (100 - frame["gaze_variance"] * 600).clip(0, 100)
    confidence_signal = frame["avg_word_prob"] * 100

    score = (
        pace * 0.28
        + articulation * 0.22
        + pitch_signal * 0.18
        + pause_signal * 0.14
        + gaze_signal * 0.08
        + confidence_signal * 0.10
    )
    frame["score"] = (score + generator.normal(0, 3, rows)).clip(0, 100)
    return frame


def train(
    dataset_path=None,
    target="score",
    output_path="models/presentation_scorer.joblib",
    production_calibrated=False,
):
    frame = pd.read_csv(dataset_path) if dataset_path else generate_synthetic_data()
    missing = [name for name in MLScoringEngine.FEATURE_NAMES if name not in frame.columns]
    if missing:
        raise ValueError(f"Dataset is missing feature columns: {', '.join(missing)}")
    if target not in frame.columns:
        raise ValueError(f"Dataset is missing target column: {target}")
    features = frame[list(MLScoringEngine.FEATURE_NAMES)].apply(pd.to_numeric, errors="coerce")
    labels = pd.to_numeric(frame[target], errors="coerce")
    valid = labels.notna()
    if valid.sum() < 2:
        raise ValueError("At least two labeled rows are required")
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("regressor", RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1, min_samples_leaf=2, max_depth=None)),
    ])
    pipeline.fit(features.loc[valid], labels.loc[valid].clip(0, 100))
    pipeline.presentation_model_metadata = {
        "production_calibrated": bool(dataset_path and production_calibrated),
        "training_source": str(dataset_path or "synthetic offline calibration data"),
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, destination)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the local presentation scoring model")
    parser.add_argument("dataset", nargs="?", help="CSV file containing the six feature columns and target")
    parser.add_argument("--target", default="score")
    parser.add_argument("--output", default="models/presentation_scorer.joblib")
    parser.add_argument(
        "--production-calibrated",
        action="store_true",
        help="Allow ranking only when this dataset contains real, human-labeled presentations",
    )
    arguments = parser.parse_args()
    print(f"Saved model to {train(arguments.dataset, arguments.target, arguments.output, arguments.production_calibrated)}")
