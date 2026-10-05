from fastapi import APIRouter
from ..models.schemas import ModelInfoResponse
from ..services.classifier_service import ClassifierService
from ..config import load_models_config

router = APIRouter(tags=["Model Info"])


@router.get("/model/info", response_model=ModelInfoResponse)
@router.get("/model-info", response_model=ModelInfoResponse)
async def get_model_info():
    config_data = load_models_config()
    is_loaded = ClassifierService.is_model_loaded()
    metadata = ClassifierService.get_metadata()

    modes = list(config_data.get("modes", {}).keys())
    models = list(config_data.get("models", {}).keys())

    return ModelInfoResponse(
        version="1.0.0",
        modelLoaded=is_loaded,
        algorithm=metadata.get("algorithm", "TF-IDF + Calibrated Classifier"),
        trainingDataset=metadata.get("dataset", "zai-org/BPO + TokenTrim Technical Corpus"),
        supportedModes=modes,
        supportedModels=models,
        metrics=metadata.get("metrics", {})
    )
