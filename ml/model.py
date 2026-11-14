"""Load the trained models and answer predictions.

The backend calls get_model() once at startup. If the saved models are
missing, unreadable, or older than the dataset, they are trained again
automatically, so a fresh checkout works without a separate training step.
"""
from __future__ import annotations

import json
import threading

import joblib

from .train import CATEGORY_FILE, DATA_FILE, METRICS_FILE, SEVERITY_FILE, train

SEVERITIES = ("critical", "high", "medium", "low")


class BugModel:
    def __init__(self, severity, category, metrics: dict):
        self.severity = severity
        self.category = category
        self.metrics = metrics

    @staticmethod
    def _probs(pipe, text: str) -> dict:
        proba = pipe.predict_proba([text])[0]
        return {label: float(p) for label, p in zip(pipe.classes_, proba)}

    def severity_probs(self, text: str) -> dict:
        probs = self._probs(self.severity, text)
        return {c: probs.get(c, 0.0) for c in SEVERITIES}

    @staticmethod
    def _top_terms(pipe, text: str, label: str, k: int = 4):
        """Words and word pairs that pushed the prediction toward `label`."""
        vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
        x = vec.transform([text]).tocoo()
        if x.nnz == 0:
            return [], 0
        coef = clf.coef_[list(clf.classes_).index(label)]
        names = vec.get_feature_names_out()
        contrib = sorted(((x.data[i] * coef[x.col[i]], names[x.col[i]]) for i in range(x.nnz)), reverse=True)
        return [term for score, term in contrib if score > 0][:k], int(x.nnz)

    def predict(self, text: str) -> dict:
        sev = self._probs(self.severity, text)
        sev = {c: sev.get(c, 0.0) for c in SEVERITIES}
        best = max(sev, key=sev.get)
        cat = self._probs(self.category, text)
        best_cat = max(cat, key=cat.get)
        words, known = self._top_terms(self.severity, text, best)
        return {
            "severity": best,
            "confidence": sev[best],
            "severityProbabilities": sev,
            "category": best_cat,
            "categoryConfidence": cat[best_cat],
            "categoryProbabilities": dict(sorted(cat.items(), key=lambda kv: -kv[1])),
            "topTerms": words,
            "knownTerms": known,
        }


_model: BugModel | None = None
_lock = threading.Lock()


def _saved_models_are_fresh() -> bool:
    files = (SEVERITY_FILE, CATEGORY_FILE, METRICS_FILE)
    if not all(f.exists() for f in files):
        return False
    return min(f.stat().st_mtime for f in files) >= DATA_FILE.stat().st_mtime


def get_model(force_retrain: bool = False) -> BugModel:
    global _model
    with _lock:
        if _model is not None and not force_retrain:
            return _model
        if not force_retrain and _saved_models_are_fresh():
            try:
                _model = BugModel(
                    joblib.load(SEVERITY_FILE),
                    joblib.load(CATEGORY_FILE),
                    json.loads(METRICS_FILE.read_text(encoding="utf-8")),
                )
                return _model
            except Exception:
                pass  # incompatible scikit-learn version or damaged file: retrain below
        result = train(save=True)
        _model = BugModel(result["severity"], result["category"], result["metrics"])
        return _model
