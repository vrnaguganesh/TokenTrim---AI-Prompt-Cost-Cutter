"""Evaluate the trained segment classifier and compression quality on test data."""

import json
import logging
import sys
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

SCRIPT_DIR = Path(__file__).resolve().parent
SERVICE_DIR = SCRIPT_DIR.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from training.train import build_segment_training_data

MODEL_DIR = SERVICE_DIR / "models"
SPLITS_DIR = SERVICE_DIR / "data" / "splits"
REPORT_DIR = SERVICE_DIR / "reports"
LOGGER = logging.getLogger(__name__)


def evaluate() -> Dict[str, Any]:
    test_path = SPLITS_DIR / "test.csv"
    if not test_path.exists():
        raise FileNotFoundError(f"Test split not found: {test_path}. Run preprocess.py first.")
    classifier = joblib.load(MODEL_DIR / "prompt_classifier.joblib")
    vectorizer = joblib.load(MODEL_DIR / "tfidf_vectorizer.joblib")
    data = pd.read_csv(test_path)
    texts, labels = build_segment_training_data(test_path)
    predictions = classifier.predict(vectorizer.transform(texts)) if texts else []
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="macro", zero_division=0
    ) if texts else (0.0, 0.0, 0.0, None)
    reductions = data["reduction_percentage"].astype(float).tolist()
    scores = data["semantic_score"].astype(float).tolist()
    accepted = [
        score >= 0.92 and reduction > 0
        for score, reduction in zip(scores, reductions)
    ]
    positive_reductions = [value for value in reductions if value > 0]
    report: Dict[str, Any] = {
        "accuracy": float(accuracy_score(labels, predictions)) if texts else 0.0,
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "average_token_reduction": mean(reductions) if reductions else 0.0,
        "average_positive_token_reduction": (
            mean(positive_reductions) if positive_reductions else 0.0
        ),
        "median_token_reduction": median(reductions) if reductions else 0.0,
        "compression_rate": (
            len(positive_reductions) / len(reductions) if reductions else 0.0
        ),
        "expansion_rate": (
            sum(value < 0 for value in reductions) / len(reductions)
            if reductions else 0.0
        ),
        "average_semantic_score": mean(scores) if scores else 0.0,
        "optimization_acceptance_rate": mean(accepted) if accepted else 0.0,
        "test_records": len(data),
        "dataset": "zai-org/BPO + Sudhendra/semantic-compression-sft",
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with (REPORT_DIR / "model_evaluation.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    with (REPORT_DIR / "model_evaluation.txt").open("w", encoding="utf-8") as handle:
        for key, value in report.items():
            handle.write(f"{key}: {value}\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    evaluate()
