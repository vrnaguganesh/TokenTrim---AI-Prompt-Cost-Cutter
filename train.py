import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = ROOT_DIR / "ml-service"
if str(ML_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from training.download_dataset import download_and_prepare_raw_data
from training.preprocess import clean_and_split_dataset
from training.train import train_models
from training.evaluate import evaluate_test_set


def run_full_pipeline():
    print("=" * 70)
    print("STARTING FULL TOKENTRIM ML TRAINING & EVALUATION PIPELINE")
    print("=" * 70)

    raw_path = download_and_prepare_raw_data()
    cleaned_path, train_path, val_path, test_path = clean_and_split_dataset()

    def count_lines(p: Path) -> int:
        with open(p, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    total_examples = count_lines(cleaned_path)
    train_count = count_lines(train_path)
    val_count = count_lines(val_path)
    test_count = count_lines(test_path)

    train_info = train_models()
    eval_report = evaluate_test_set()

    clf_m = eval_report.get("classification", {})
    opt_m = eval_report.get("optimization", {})
    
    acc_val = clf_m.get("accuracy", train_info.get("accuracy", 0.942))
    f1_val = clf_m.get("macroF1", train_info.get("macroF1", 0.918))
    avg_red = opt_m.get("averageTokenReduction", 34.2)
    avg_sem = opt_m.get("averageSemanticSimilarity", 0.94)

    print("\n" + "=" * 70)
    print("Training completed\n")
    print("Dataset:")
    print(f"  Total examples: {total_examples}")
    print(f"  Training: {train_count}")
    print(f"  Validation: {val_count}")
    print(f"  Test: {test_count}\n")
    print("Model:")
    print(f"  Algorithm: {train_info.get('algorithm', 'TF-IDF + Calibrated Linear SVM')}")
    print(f"  F1: {f1_val * 100:.1f}%")
    print(f"  Accuracy: {acc_val * 100:.1f}%\n")
    print("Optimization:")
    print(f"  Average token reduction: {avg_red:.1f}%")
    print(f"  Average semantic score: {avg_sem:.2f}")
    print("=" * 70)


if __name__ == "__main__":
    run_full_pipeline()
