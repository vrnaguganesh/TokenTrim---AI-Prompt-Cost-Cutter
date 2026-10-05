"""Routes package"""
from .health import router as health_router
from .optimize import router as optimize_router
from .evaluate import router as evaluate_router
from .model_info import router as model_info_router

__all__ = ["health_router", "optimize_router", "evaluate_router", "model_info_router"]
