import os
import json
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(BASE_DIR / "models")))
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
CONFIG_PATH = Path(os.getenv("CONFIG_PATH", str(ROOT_DIR / "config" / "models.json")))

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
ENABLE_PROMPT_LOGGING = os.getenv("ENABLE_PROMPT_LOGGING", "false").lower() in ("true", "1", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ML_INTERNAL_TOKEN = os.getenv("ML_INTERNAL_TOKEN", "")

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "balanced")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")


def load_models_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "defaultModel": "gpt-4o",
        "models": {
            "gpt-4o": {"name": "GPT-4o", "inputPricePerMillionTokens": 2.50, "tokenizer": "o200k_base"},
            "gpt-4o-mini": {"name": "GPT-4o Mini", "inputPricePerMillionTokens": 0.15, "tokenizer": "o200k_base"},
            "claude-3-5-sonnet": {"name": "Claude 3.5 Sonnet", "inputPricePerMillionTokens": 3.00, "tokenizer": "cl100k_base"},
            "gemini-1.5-pro": {"name": "Gemini 1.5 Pro", "inputPricePerMillionTokens": 1.25, "tokenizer": "cl100k_base"},
            "model-a": {"name": "Model Tier A", "inputPricePerMillionTokens": 1.00, "tokenizer": "cl100k_base"},
            "model-b": {"name": "Model Tier B", "inputPricePerMillionTokens": 0.50, "tokenizer": "cl100k_base"}
        },
        "modes": {
            "aggressive": {"minSemanticScore": 0.88, "targetTokenReductionMin": 30.0, "targetTokenReductionMax": 50.0},
            "balanced": {"minSemanticScore": 0.92, "targetTokenReductionMin": 20.0, "targetTokenReductionMax": 35.0},
            "quality": {"minSemanticScore": 0.96, "targetTokenReductionMin": 10.0, "targetTokenReductionMax": 20.0}
        }
    }
