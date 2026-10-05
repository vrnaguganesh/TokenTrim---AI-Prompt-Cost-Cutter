from fastapi import APIRouter
from ..models.schemas import EvaluateRequest, EvaluateResponse
from ..services.semantic_service import SemanticService
from ..services.safety_guard import SafetyGuard
from ..services.tokenizer import count_tokens, calculate_token_savings
from ..services.cost_calculator import CostCalculator

router = APIRouter(tags=["Evaluation"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_pair(request: EvaluateRequest):
    orig_tokens = count_tokens(request.originalPrompt, model=request.model or "gpt-4o")
    opt_tokens = count_tokens(request.optimizedPrompt, model=request.model or "gpt-4o")
    token_metrics = calculate_token_savings(orig_tokens, opt_tokens)

    semantic_score = SemanticService.calculate_similarity(request.originalPrompt, request.optimizedPrompt)
    
    is_safe, reason, audit_details = SafetyGuard.validate_preservation(
        original_prompt=request.originalPrompt,
        optimized_prompt=request.optimizedPrompt,
        mode=request.mode or "balanced"
    )

    cost_metrics = CostCalculator.calculate_cost(
        original_tokens=orig_tokens,
        optimized_tokens=opt_tokens,
        model_id=request.model or "gpt-4o"
    )

    return EvaluateResponse(
        originalTokens=orig_tokens,
        optimizedTokens=opt_tokens,
        tokensSaved=token_metrics["tokensSaved"],
        reductionPercentage=token_metrics["reductionPercentage"],
        semanticScore=semantic_score,
        isSafe=is_safe,
        safetyReason=reason,
        estimatedOriginalCost=cost_metrics["estimatedOriginalCost"],
        estimatedOptimizedCost=cost_metrics["estimatedOptimizedCost"],
        estimatedCostSaved=cost_metrics["estimatedCostSaved"],
        auditDetails=audit_details
    )
