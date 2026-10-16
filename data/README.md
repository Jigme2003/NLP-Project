# Bootstrap scoring data

`bootstrap_presentation_scores.csv` is a small, locally generated calibration dataset based on the scoring engine's documented feature ranges. It is provided to make the local RandomForest pipeline runnable immediately; its labels are not human-annotated ground truth.

The included bootstrap model is advisory only and is excluded from the overall
grade. For a learned model to affect ranking, use independently labeled
presentation samples and explicitly confirm that the labels are real human
assessments:

```powershell
.\.venv\Scripts\python.exe train_model.py path\to\labeled_scores.csv --production-calibrated --output models\presentation_scorer.joblib
```

The `--production-calibrated` option is the operator's declaration. The
training script cannot determine whether a dataset's labels are genuinely
human-reviewed. Facial movement and vocal energy/pitch are only observable
signals; neither can prove motivation or a person's internal emotional state.
