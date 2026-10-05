from typing import Dict, Any, Optional, List
from ..config import load_models_config, DEFAULT_MODEL, DEFAULT_MODE
from ..preprocessing.cleaner import TextCleaner
from ..preprocessing.normalizer import PromptNormalizer
from .segmenter import PromptSegmenter, PromptSegment
from .classifier_service import ClassifierService
from .safety_guard import SafetyGuard
from .semantic_service import SemanticService
from .tokenizer import count_tokens, calculate_token_savings
from .cost_calculator import CostCalculator


class OptimizationEngine:
    """End-to-End Prompt Optimization Engine coordinating ML classification, safety validation, and token accounting."""

    @classmethod
    def optimize(
        cls,
        prompt: str,
        model: str = DEFAULT_MODEL,
        mode: str = DEFAULT_MODE,
        custom_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        raw_prompt = prompt or ""
        cleaned_original = TextCleaner.clean_text(raw_prompt)

        if not cleaned_original or len(cleaned_original.strip()) == 0:
            return {
                "modelVersion": "tokentrim-optimizer-v1",
                "originalPrompt": raw_prompt,
                "optimizedPrompt": raw_prompt,
                "originalTokens": 0,
                "optimizedTokens": 0,
                "tokensSaved": 0,
                "reductionPercentage": 0.0,
                "semanticScore": 1.0,
                "estimatedOriginalCost": 0.0,
                "estimatedOptimizedCost": 0.0,
                "estimatedCostSaved": 0.0,
                "costReductionPercentage": 0.0,
                "optimizationStatus": "rejected",
                "rejectionReason": "Empty prompt provided",
                "segments": []
            }

        # Step 1: Segment prompt
        segments: List[PromptSegment] = PromptSegmenter.segment(cleaned_original)
        
        # Step 2: Classify segments
        unprotected_indices = [i for i, s in enumerate(segments) if not s.is_protected]
        unprotected_texts = [segments[i].text for i in unprotected_indices]

        if unprotected_texts:
            classifications = ClassifierService.classify_segments(unprotected_texts)
            for idx, res in zip(unprotected_indices, classifications):
                segments[idx].label = res["label"]

        # Step 3, 4, 5: Keep, Remove, Compress
        reconstructed_parts: List[str] = []
        for s in segments:
            if s.is_protected:
                s.label = "KEEP"
                s.processed_text = s.text
                reconstructed_parts.append(s.text)
                continue

            if s.label == "REMOVE":
                tech_terms = SafetyGuard.extract_tech_terms(s.text)
                negatives = SafetyGuard.extract_negative_clauses(s.text)
                
                if tech_terms or negatives:
                    compressed = PromptNormalizer.normalize_clause(s.text, mode=mode)
                    s.label = "COMPRESS"
                    s.processed_text = compressed
                    if compressed:
                        reconstructed_parts.append(compressed)
                else:
                    s.processed_text = ""
            elif s.label == "COMPRESS":
                compressed = PromptNormalizer.normalize_clause(s.text, mode=mode)
                s.processed_text = compressed
                if compressed:
                    reconstructed_parts.append(compressed)
            else:  # KEEP
                if mode == "aggressive":
                    light_cleaned = PromptNormalizer.apply_filler_stripping(s.text)
                    s.processed_text = light_cleaned or s.text
                else:
                    s.processed_text = s.text
                reconstructed_parts.append(s.processed_text)

        # Step 6: Prompt Reconstruction
        optimized_candidate = TextCleaner.normalize_whitespace("\n".join(reconstructed_parts))
        if not optimized_candidate:
            optimized_candidate = cleaned_original

        # Step 7: Calculate Semantic Similarity
        semantic_score = SemanticService.calculate_similarity(cleaned_original, optimized_candidate)

        # Step 8: Compare token count
        original_tokens = count_tokens(cleaned_original, model=model)
        optimized_tokens = count_tokens(optimized_candidate, model=model)
        token_metrics = calculate_token_savings(original_tokens, optimized_tokens)

        # Step 9: Validate required entities & safety constraints
        is_safe, safety_reason, audit_details = SafetyGuard.validate_preservation(
            cleaned_original,
            optimized_candidate,
            mode=mode
        )

        config_data = load_models_config()
        mode_config = config_data.get("modes", {}).get(mode, {
            "minSemanticScore": 0.92,
            "targetTokenReductionMin": 20.0
        })
        min_semantic_threshold = float(mode_config.get("minSemanticScore", 0.92))

        # Step 10: Optimization Decision
        accepted = True
        rejection_reason = None

        if not is_safe:
            accepted = False
            rejection_reason = safety_reason
        elif semantic_score < min_semantic_threshold:
            accepted = False
            rejection_reason = f"Semantic similarity score ({semantic_score}) fell below threshold ({min_semantic_threshold}) for mode '{mode}'"
        elif optimized_tokens > original_tokens:
            accepted = False
            rejection_reason = "Optimization resulted in token expansion"

        final_optimized_text = optimized_candidate if accepted else cleaned_original
        final_optimized_tokens = optimized_tokens if accepted else original_tokens
        
        cost_metrics = CostCalculator.calculate_cost(
            original_tokens=original_tokens,
            optimized_tokens=final_optimized_tokens,
            model_id=model
        )

        final_token_metrics = calculate_token_savings(original_tokens, final_optimized_tokens)

        return {
            "originalPrompt": raw_prompt,
            "optimizedPrompt": final_optimized_text,
            "originalTokens": original_tokens,
            "optimizedTokens": final_optimized_tokens,
            "tokensSaved": final_token_metrics["tokensSaved"],
            "reductionPercentage": final_token_metrics["reductionPercentage"],
            "semanticScore": semantic_score,
            "estimatedOriginalCost": cost_metrics["estimatedOriginalCost"],
            "estimatedOptimizedCost": cost_metrics["estimatedOptimizedCost"],
            "estimatedCostSaved": cost_metrics["estimatedCostSaved"],
            "costReductionPercentage": cost_metrics["costReductionPercentage"],
            "optimizationStatus": "accepted" if accepted else "rejected",
            "rejectionReason": rejection_reason,
            "mode": mode,
            "model": model,
            "segments": [s.to_dict() for s in segments],
            "safetyAudit": audit_details
        }
