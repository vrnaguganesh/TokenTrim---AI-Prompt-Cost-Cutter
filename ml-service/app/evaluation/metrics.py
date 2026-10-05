import numpy as np
from typing import Dict, List, Any
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix


class MetricsCalculator:
    """Calculates classification, optimization, cost, and safety quality metrics."""

    @staticmethod
    def calculate_classification_metrics(y_true: List[str], y_pred: List[str], labels: List[str] = ["KEEP", "REMOVE", "COMPRESS"]) -> Dict[str, Any]:
        acc = float(accuracy_score(y_true, y_pred))
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=labels, zero_division=0, average="macro"
        )
        p_class, r_class, f1_class, supp_class = precision_recall_fscore_support(
            y_true, y_pred, labels=labels, zero_division=0, average=None
        )
        cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()

        per_class = {}
        for i, lbl in enumerate(labels):
            per_class[lbl] = {
                "precision": round(float(p_class[i]), 4),
                "recall": round(float(r_class[i]), 4),
                "f1": round(float(f1_class[i]), 4),
                "support": int(supp_class[i])
            }

        return {
            "accuracy": round(acc, 4),
            "macroPrecision": round(float(precision), 4),
            "macroRecall": round(float(recall), 4),
            "macroF1": round(float(f1), 4),
            "confusionMatrix": cm,
            "classes": labels,
            "perClass": per_class
        }

    @staticmethod
    def calculate_optimization_metrics(optimization_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not optimization_results:
            return {}

        token_reductions = [r["reductionPercentage"] for r in optimization_results]
        semantic_scores = [r["semanticScore"] for r in optimization_results]
        tokens_saved_list = [r["tokensSaved"] for r in optimization_results]
        cost_saved_list = [r["estimatedCostSaved"] for r in optimization_results]
        accepted_list = [1 if r["optimizationStatus"] == "accepted" else 0 for r in optimization_results]

        avg_reduction = float(np.mean(token_reductions))
        median_reduction = float(np.median(token_reductions))
        avg_semantic = float(np.mean(semantic_scores))
        min_semantic = float(np.min(semantic_scores))
        acceptance_rate = float(np.mean(accepted_list)) * 100.0
        total_tokens_saved = int(np.sum(tokens_saved_list))
        total_cost_saved = float(np.sum(cost_saved_list))

        return {
            "averageTokenReduction": round(avg_reduction, 2),
            "medianTokenReduction": round(median_reduction, 2),
            "averageSemanticSimilarity": round(avg_semantic, 4),
            "minimumSemanticSimilarity": round(min_semantic, 4),
            "optimizationAcceptanceRate": round(acceptance_rate, 2),
            "totalTokensSaved": total_tokens_saved,
            "totalEstimatedCostSaved": round(total_cost_saved, 6),
            "totalEvaluatedPrompts": len(optimization_results)
        }
