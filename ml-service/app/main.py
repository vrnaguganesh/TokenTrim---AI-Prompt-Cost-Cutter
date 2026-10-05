import uuid
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import PORT, HOST, LOG_LEVEL, ENVIRONMENT, MODEL_DIR, ML_INTERNAL_TOKEN
from .services.classifier_service import ClassifierService
from .services.semantic_service import get_semantic_model
from .routes.health import router as health_router
from .routes.optimize import router as optimize_router
from .routes.evaluate import router as evaluate_router
from .routes.model_info import router as model_info_router

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] [ReqID: %(request_id)s] %(message)s"
)
logger = logging.getLogger("tokentrim.ml_service")


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


for handler in logging.root.handlers:
    handler.addFilter(RequestIdFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TokenTrim ML Service...")
    
    model_loaded = ClassifierService.load_model(MODEL_DIR)
    if model_loaded:
        logger.info("Successfully loaded ML prompt classifier from models directory.")
    else:
        logger.info("ML prompt classifier model artifacts not found. Heuristic rules will be active until trained.")

    try:
        logger.info("Warming up semantic sentence-transformer model...")
        get_semantic_model()
        logger.info("Semantic sentence-transformer model ready.")
    except Exception as e:
        logger.warning(f"Semantic transformer warmup error: {e}")

    yield

    logger.info("Shutting down TokenTrim ML Service gracefully...")


app = FastAPI(
    title="TokenTrim ML Prompt Optimization Engine",
    description="Production-ready ML Service for semantic prompt compression and LLM cost optimization.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id_and_timing_middleware(request: Request, call_next):
    if request.url.path == "/internal/optimize" and ML_INTERNAL_TOKEN:
        if request.headers.get("X-Internal-Token") != ML_INTERNAL_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "Invalid internal service token"})
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.time()
    
    response: Response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000.0
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-Ms"] = f"{process_time:.2f}"
    
    logger.info(
        f"{request.method} {request.url.path} completed with status {response.status_code} in {process_time:.2f}ms",
        extra={"request_id": req_id}
    )
    return response


app.include_router(health_router)
app.include_router(optimize_router)
app.include_router(evaluate_router)
app.include_router(model_info_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
