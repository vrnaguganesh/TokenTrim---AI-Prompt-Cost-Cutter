import logging
from fastapi import APIRouter, Request, HTTPException
from ..models.schemas import OptimizeRequest, OptimizeResponse
from ..services.optimization_engine import OptimizationEngine
from ..config import ENABLE_PROMPT_LOGGING

logger = logging.getLogger("tokentrim.optimize")
router = APIRouter(tags=["Optimization"])


@router.post("/optimize", response_model=OptimizeResponse)
@router.post("/internal/optimize", response_model=OptimizeResponse)
async def optimize_prompt(request: OptimizeRequest, http_request: Request):
    try:
        if ENABLE_PROMPT_LOGGING:
            logger.info(f"Processing optimization for model={request.model}, mode={request.mode}")
        else:
            logger.info("Processing prompt optimization request (prompt logging disabled)")

        result = OptimizationEngine.optimize(
            prompt=request.prompt,
            model=request.model or "gpt-4o",
            mode=request.mode or "balanced",
            custom_keywords=request.customKeywords or []
        )
        return OptimizeResponse(
            **result,
            requestId=http_request.headers.get("X-Request-ID"),
            modelVersion="tokentrim-optimizer-v1",
        )
    except Exception as e:
        logger.error(f"Error optimizing prompt: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during prompt optimization."
        )
