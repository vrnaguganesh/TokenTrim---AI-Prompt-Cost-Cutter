import json
import sys
import joblib
import re
import csv
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

SCRIPT_DIR = Path(__file__).resolve().parent
SERVICE_DIR = SCRIPT_DIR.parent
ROOT_DIR = SERVICE_DIR.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.preprocessing.cleaner import FILLER_PATTERNS, COMPRESSION_RULES
from app.services.segmenter import PromptSegmenter

MODEL_DIR = SERVICE_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
SPLITS_DIR = SERVICE_DIR / "data" / "splits"


def build_segment_training_data(dataset_path: Path) -> Tuple[List[str], List[str]]:
    """Builds labeled segment samples (KEEP, REMOVE, COMPRESS) from prompt pairs."""
    texts: List[str] = []
    labels: List[str] = []

    if not dataset_path.exists():
        return texts, labels

    with open(dataset_path, "r", encoding="utf-8") as f:
        if dataset_path.suffix.lower() == ".csv":
            items = csv.DictReader(f)
        else:
            items = (json.loads(line) for line in f if line.strip())
        for item in items:
            orig = item.get("original_prompt", "")
            opt = item.get("optimized_prompt", "")

            segments = PromptSegmenter.segment(orig)
            opt_lower = opt.lower()

            for s in segments:
                if s.is_protected:
                    texts.append(s.text)
                    labels.append("KEEP")
                    continue

                s_text = s.text.strip()
                s_lower = s_text.lower()
                
                # Check if segment matches filler phrases
                is_filler = False
                for pat, _ in FILLER_PATTERNS:
                    if re.search(pat, s_lower) and len(s_lower.split()) < 12:
                        words = re.sub(pat, "", s_lower).strip().split()
                        if len(words) <= 2:
                            is_filler = True
                            break

                if is_filler:
                    texts.append(s_text)
                    labels.append("REMOVE")
                    continue

                # Check if segment matches compression rules
                is_compressible = False
                for pat, _ in COMPRESSION_RULES:
                    if re.search(pat, s_lower):
                        is_compressible = True
                        break

                if is_compressible:
                    texts.append(s_text)
                    labels.append("COMPRESS")
                    continue

                # Alignment heuristic against optimized prompt
                words = [w for w in re.findall(r"\b\w+\b", s_lower) if len(w) > 2]
                overlap = sum(1 for w in words if w in opt_lower)
                ratio = overlap / len(words) if words else 1.0

                if ratio >= 0.70:
                    texts.append(s_text)
                    labels.append("KEEP")
                elif ratio <= 0.25:
                    texts.append(s_text)
                    labels.append("REMOVE")
                else:
                    texts.append(s_text)
                    labels.append("COMPRESS")

    # Add synthetic canonical segment examples to reinforce key class boundaries
    synthetic_segments = [
        # REMOVE
        ("Can you please", "REMOVE"),
        ("Could you kindly", "REMOVE"),
        ("I would like you to", "REMOVE"),
        ("Please make sure that you", "REMOVE"),
        ("in a very detailed manner", "REMOVE"),
        ("if possible", "REMOVE"),
        ("Thank you in advance!", "REMOVE"),
        ("Thanks a lot!", "REMOVE"),
        ("Hello! Hope you are doing well.", "REMOVE"),
        ("Hey there,", "REMOVE"),
        ("Dear AI,", "REMOVE"),
        ("I am looking for your assistance with", "REMOVE"),
        ("Needless to say", "REMOVE"),
        ("First and foremost", "REMOVE"),
        ("As a matter of fact", "REMOVE"),

        # COMPRESS
        ("Can you please provide me with a detailed explanation of how", "COMPRESS"),
        ("Provide a step by step guide on how to", "COMPRESS"),
        ("Give me an overview of", "COMPRESS"),
        ("Write a comprehensive tutorial about", "COMPRESS"),
        ("I am trying to figure out how to", "COMPRESS"),
        ("What are the differences between", "COMPRESS"),
        ("What is the best way to", "COMPRESS"),
        ("Could you please give me examples of", "COMPRESS"),
        ("Please write code to", "COMPRESS"),

        # KEEP
        ("Do not use MongoDB", "KEEP"),
        ("Use PostgreSQL 15 with connection pooling", "KEEP"),
        ("Return response formatted as strict JSON", "KEEP"),
        ("Limit output to 500 words", "KEEP"),
        ("Use Node.js 22 and Express.js", "KEEP"),
        ("Ensure all passwords are hashed with bcrypt", "KEEP"),
        ("Include unit tests with 90% code coverage", "KEEP"),
        ("Do not expose API secret keys", "KEEP"),
        ("Target latency must be under 100ms", "KEEP"),
        ("```typescript\ninterface User { id: string; }\n```", "KEEP")
    ]

    for text, lbl in synthetic_segments:
        texts.append(text)
        labels.append(lbl)

    return texts, labels


def train_models() -> Dict[str, Any]:
    print("=" * 60)
    print("STEP 3: Training ML Prompt Segment Classifier")
    print("=" * 60)

    train_path = SPLITS_DIR / "train.csv"
    val_path = SPLITS_DIR / "validation.csv"

    X_train_raw, y_train = build_segment_training_data(train_path)
    X_val_raw, y_val = build_segment_training_data(val_path)

    print(f"Segment Training Samples:   {len(X_train_raw)}")
    print(f"Segment Validation Samples: {len(X_val_raw)}")

    label_counts = {lbl: y_train.count(lbl) for lbl in set(y_train)}
    print(f"Class Distribution: {label_counts}")

    # TF-IDF Feature Extraction
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=15000,
        sublinear_tf=True,
        strip_accents="unicode"
    )

    if not X_train_raw or not X_val_raw:
        raise ValueError("Training and validation splits must contain valid prompt pairs.")
    X_train_vec = vectorizer.fit_transform(X_train_raw)
    X_val_vec = vectorizer.transform(X_val_raw)

    # Model 1: Logistic Regression
    print("\nTraining Model 1: TF-IDF + Logistic Regression...")
    clf_lr = LogisticRegression(
        C=2.5,
        max_iter=1500,
        class_weight="balanced",
        random_state=42
    )
    clf_lr.fit(X_train_vec, y_train)
    y_pred_lr = clf_lr.predict(X_val_vec)
    
    acc_lr = accuracy_score(y_val, y_pred_lr)
    p_lr, r_lr, f1_lr, _ = precision_recall_fscore_support(y_val, y_pred_lr, average="macro", zero_division=0)
    print(f"  -> Logistic Regression Validation: Accuracy={acc_lr * 100:.2f}%, Macro F1={f1_lr * 100:.2f}%")

    # Model 2: Linear SVM with Probability Calibration
    print("\nTraining Model 2: TF-IDF + Calibrated Linear SVM...")
    base_svm = LinearSVC(C=1.5, max_iter=3000, class_weight="balanced", random_state=42)
    clf_svm = CalibratedClassifierCV(estimator=base_svm, cv=3)
    clf_svm.fit(X_train_vec, y_train)
    y_pred_svm = clf_svm.predict(X_val_vec)

    acc_svm = accuracy_score(y_val, y_pred_svm)
    p_svm, r_svm, f1_svm, _ = precision_recall_fscore_support(y_val, y_pred_svm, average="macro", zero_division=0)
    print(f"  -> Linear SVM Validation: Accuracy={acc_svm * 100:.2f}%, Macro F1={f1_svm * 100:.2f}%")

    # Select Champion Model
    if f1_svm >= f1_lr:
        best_clf = clf_svm
        best_name = "TF-IDF + Calibrated Linear SVM"
        best_acc = acc_svm
        best_f1 = f1_svm
    else:
        best_clf = clf_lr
        best_name = "TF-IDF + Logistic Regression"
        best_acc = acc_lr
        best_f1 = f1_lr

    print(f"\nSelected Champion Model: {best_name} (Macro F1={best_f1 * 100:.2f}%)")

    # Export models
    classifier_path = MODEL_DIR / "prompt_classifier.joblib"
    vectorizer_path = MODEL_DIR / "tfidf_vectorizer.joblib"
    joblib.dump(best_clf, classifier_path)
    joblib.dump(vectorizer, vectorizer_path)

    metrics_info = {
        "algorithm": best_name,
        "accuracy": round(float(best_acc), 4),
        "macroF1": round(float(best_f1), 4),
        "models_compared": {
            "logistic_regression": {"accuracy": round(float(acc_lr), 4), "macroF1": round(float(f1_lr), 4)},
            "linear_svm": {"accuracy": round(float(acc_svm), 4), "macroF1": round(float(f1_svm), 4)}
        },
        "dataset": "zai-org/BPO + Sudhendra/semantic-compression-sft",
        "training_split": str(train_path),
        "validation_split": str(val_path),
    }

    metrics_path = MODEL_DIR / "classifier_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_info, f, indent=2)
    with open(MODEL_DIR / "model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metrics_info, f, indent=2)

    print(f"Artifacts saved to {MODEL_DIR}")
    return metrics_info


if __name__ == "__main__":
    train_models()
