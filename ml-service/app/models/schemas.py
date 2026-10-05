from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class OptimizeRequest(BaseModel):
    prompt: str = Field(..., description="Original prompt text to optimize")
    model: Optional[str] = Field("gpt-4o", description="Target LLM model ID for tokenizer and cost calculation")
    mode: Optional[str] = Field("balanced", description="Optimization mode: 'aggressive', 'balanced', or 'quality'")
    customKeywords: Optional[List[str]] = Field(default=[], description="User-specified keywords to strictly protect")


class SegmentDetail(BaseModel):
    index: int
    text: str
    type: str
    is_protected: bool
    label: str
    processed_text: str


class OptimizeResponse(BaseModel):
    requestId: Optional[str] = None
    originalPrompt: str
    optimizedPrompt: str
    originalTokens: int
    optimizedTokens: int
    tokensSaved: int
    reductionPercentage: float
    semanticScore: float
    estimatedOriginalCost: float
    estimatedOptimizedCost: float
    estimatedCostSaved: float
    costReductionPercentage: float
    optimizationStatus: str
    modelVersion: str = "tokentrim-optimizer-v1"
    rejectionReason: Optional[str] = None
    mode: Optional[str] = "balanced"
    model: Optional[str] = "gpt-4o"
    segments: Optional[List[SegmentDetail]] = None
    safetyAudit: Optional[Dict[str, Any]] = None


class EvaluateRequest(BaseModel):
    originalPrompt: str
    optimizedPrompt: str
    model: Optional[str] = "gpt-4o"
    mode: Optional[str] = "balanced"


class EvaluateResponse(BaseModel):
    originalTokens: int
    optimizedTokens: int
    tokensSaved: int
    reductionPercentage: float
    semanticScore: float
    isSafe: bool
    safetyReason: Optional[str] = None
    estimatedOriginalCost: float
    estimatedOptimizedCost: float
    estimatedCostSaved: float
    auditDetails: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str = "1.0.0"
    environment: str = "production"


class ModelInfoResponse(BaseModel):
    version: str
    modelLoaded: bool
    algorithm: str
    trainingDataset: str
    supportedModes: List[str]
    supportedModels: List[str]
    metrics: Dict[str, Any]
