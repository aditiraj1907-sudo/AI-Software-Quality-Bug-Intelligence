"""Train the two text models used by the platform.

* severity model: bug report text -> critical / high / medium / low
* category model: bug report text -> Security / Logic / Error handling / ...

Both are TF-IDF + logistic regression pipelines (scikit-learn). Quality is
measured with stratified k-fold cross-validation, so every number in
metrics.json comes from reports the model did not train on.

Run from the project root:

    python -m ml.train
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "data" / "bug_reports.csv"
MODEL_DIR = HERE / "models"
SEVERITY_FILE = MODEL_DIR / "severity.joblib"
CATEGORY_FILE = MODEL_DIR / "category.joblib"
METRICS_FILE = MODEL_DIR / "metrics.json"


def load_data(path: Path = DATA_FILE):
    texts, categories, severities = [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts.append(row["text"].strip())
            categories.append(row["category"].strip())
            severities.append(row["severity"].strip())
    return texts, categories, severities


def make_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")),
            ("clf", LogisticRegression(C=8.0, max_iter=2000, class_weight="balanced")),
        ]
    )


def evaluate(texts, labels, seed: int = 42) -> dict:
    """Cross-validated accuracy, macro F1 and per-class scores."""
    folds = max(2, min(5, min(Counter(labels).values())))
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    predicted = cross_val_predict(make_pipeline(), texts, labels, cv=cv)
    report = classification_report(labels, predicted, output_dict=True, zero_division=0)
    per_class = {
        name: {
            "precision": round(vals["precision"], 3),
            "recall": round(vals["recall"], 3),
            "f1": round(vals["f1-score"], 3),
            "support": int(vals["support"]),
        }
        for name, vals in report.items()
        if name in set(labels)
    }
    return {
        "accuracy": round(accuracy_score(labels, predicted), 3),
        "macro_f1": round(f1_score(labels, predicted, average="macro", zero_division=0), 3),
        "folds": folds,
        "per_class": per_class,
    }


def train(save: bool = True) -> dict:
    texts, categories, severities = load_data()
    metrics = {
        "algorithm": "TF-IDF (1-2 grams) + logistic regression",
        "samples": len(texts),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "severity": {"classes": dict(Counter(severities)), **evaluate(texts, severities)},
        "category": {"classes": dict(Counter(categories)), **evaluate(texts, categories)},
    }
    severity_model = make_pipeline().fit(texts, severities)
    category_model = make_pipeline().fit(texts, categories)
    if save:
        try:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            joblib.dump(severity_model, SEVERITY_FILE)
            joblib.dump(category_model, CATEGORY_FILE)
            METRICS_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        except OSError:
            pass  # read-only folder: the models still work for this run
    return {"severity": severity_model, "category": category_model, "metrics": metrics}


if __name__ == "__main__":
    result = train(save=True)
    m = result["metrics"]
    print(f"Trained on {m['samples']} labelled bug reports")
    for name in ("severity", "category"):
        print(f"  {name:9s} accuracy {m[name]['accuracy']:.3f}   macro-F1 {m[name]['macro_f1']:.3f}   ({m[name]['folds']}-fold cross-validation)")
    print(f"Saved to {MODEL_DIR}")
