import os
import joblib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..config import MODEL_DIR
from ..preprocessing.cleaner import FILLER_PATTERNS, COMPRESSION_RULES

_CLASSIFIER = None
_VECTORIZER = None
_MODEL_METADATA = {}


class ClassifierService:
    """Stage 2 ML Segment Classifier (KEEP / REMOVE / COMPRESS)."""

    @classmethod
    def load_model(cls, model_dir: Optional[Path] = None) -> bool:
        global _CLASSIFIER, _VECTORIZER, _MODEL_METADATA
        target_dir = model_dir or MODEL_DIR
        classifier_path = target_dir / "prompt_classifier.joblib"
        vectorizer_path = target_dir / "tfidf_vectorizer.joblib"
        
        if classifier_path.exists() and vectorizer_path.exists():
            try:
                _CLASSIFIER = joblib.load(classifier_path)
                _VECTORIZER = joblib.load(vectorizer_path)
                
                metrics_path = target_dir / "classifier_metrics.json"
                if metrics_path.exists():
                    import json
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        _MODEL_METADATA = json.load(f)
                else:
                    _MODEL_METADATA = {"algorithm": type(_CLASSIFIER).__name__, "status": "loaded"}
                return True
            except Exception as e:
                print(f"Warning: Failed to load trained classifier from {target_dir}: {e}")
                return False
        return False

    @classmethod
    def is_model_loaded(cls) -> bool:
        global _CLASSIFIER, _VECTORIZER
        return _CLASSIFIER is not None and _VECTORIZER is not None

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        global _MODEL_METADATA
        return _MODEL_METADATA

    @classmethod
    def fallback_classify(cls, text: str) -> Tuple[str, float]:
        lower = text.lower().strip()
        
        for pat, _ in FILLER_PATTERNS:
            import re
            if re.search(pat, lower) and len(lower.split()) < 12:
                words = re.sub(pat, "", lower).strip().split()
                if len(words) <= 2:
                    return "REMOVE", 0.95

        for pat, _ in COMPRESSION_RULES:
            import re
            if re.search(pat, lower):
                return "COMPRESS", 0.90

        return "KEEP", 0.85

    @classmethod
    def classify_segments(cls, segment_texts: List[str]) -> List[Dict[str, Any]]:
        global _CLASSIFIER, _VECTORIZER
        if not segment_texts:
            return []

        results: List[Dict[str, Any]] = []

        if cls.is_model_loaded():
            try:
                X = _VECTORIZER.transform(segment_texts)
                predictions = _CLASSIFIER.predict(X)
                
                if hasattr(_CLASSIFIER, "predict_proba"):
                    probas = _CLASSIFIER.predict_proba(X)
                    for i, text in enumerate(segment_texts):
                        pred_label = str(predictions[i])
                        prob = float(max(probas[i]))
                        results.append({"label": pred_label, "confidence": round(prob, 4)})
                else:
                    for i, text in enumerate(segment_texts):
                        results.append({"label": str(predictions[i]), "confidence": 0.88})
                return results
            except Exception as e:
                print(f"Warning: ML classification inference error: {e}")

        for text in segment_texts:
            label, conf = cls.fallback_classify(text)
            results.append({"label": label, "confidence": conf})

        return results
