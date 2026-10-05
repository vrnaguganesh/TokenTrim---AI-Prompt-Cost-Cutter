from fastapi import APIRouter
from ..models.schemas import HealthResponse
from ..services.classifier_service import ClassifierService
from ..config import ENVIRONMENT

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    is_loaded = ClassifierService.is_model_loaded()
    return HealthResponse(
        status="healthy",
        model_loaded=is_loaded,
        version="1.0.0",
        environment=ENVIRONMENT
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check():
    is_loaded = ClassifierService.is_model_loaded()
    return HealthResponse(
        status="ready" if is_loaded else "not_ready",
        model_loaded=is_loaded,
        version="1.0.0",
        environment=ENVIRONMENT,
    )
