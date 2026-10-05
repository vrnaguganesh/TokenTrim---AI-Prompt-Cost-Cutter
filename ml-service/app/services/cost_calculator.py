from typing import Dict, Any
from ..config import load_models_config


class CostCalculator:
    """Calculates estimated LLM input costs and monetary savings from token compression."""

    @classmethod
    def get_model_pricing(cls, model_id: str) -> Dict[str, Any]:
        cfg = load_models_config()
        models_dict = cfg.get("models", {})
        
        model_key = model_id.lower() if model_id else "gpt-4o"
        if model_key in models_dict:
            return models_dict[model_key]
        
        for k, v in models_dict.items():
            if k in model_key or model_key in k:
                return v

        default_key = cfg.get("defaultModel", "gpt-4o")
        return models_dict.get(default_key, {"inputPricePerMillionTokens": 2.50, "name": "Default Model"})

    @classmethod
    def calculate_cost(
        cls,
        original_tokens: int,
        optimized_tokens: int,
        model_id: str = "gpt-4o"
    ) -> Dict[str, Any]:
        pricing = cls.get_model_pricing(model_id)
        input_price_per_million = float(pricing.get("inputPricePerMillionTokens", 2.50))

        estimated_original_cost = (original_tokens / 1_000_000.0) * input_price_per_million
        estimated_optimized_cost = (optimized_tokens / 1_000_000.0) * input_price_per_million
        
        estimated_cost_saved = max(0.0, estimated_original_cost - estimated_optimized_cost)

        if estimated_original_cost > 0:
            cost_reduction_pct = round((estimated_cost_saved / estimated_original_cost) * 100.0, 2)
        else:
            cost_reduction_pct = 0.0

        return {
            "model": model_id,
            "modelName": pricing.get("name", model_id),
            "inputPricePerMillionTokens": input_price_per_million,
            "estimatedOriginalCost": round(estimated_original_cost, 6),
            "estimatedOptimizedCost": round(estimated_optimized_cost, 6),
            "estimatedCostSaved": round(estimated_cost_saved, 6),
            "costReductionPercentage": cost_reduction_pct,
            "isEstimate": True
        }
