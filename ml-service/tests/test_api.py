import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_loaded" in data


def test_optimize_endpoint():
    payload = {
        "prompt": "Can you please provide a detailed explanation of Redis caching in Node.js?",
        "model": "gpt-4o",
        "mode": "balanced"
    }
    response = client.post("/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "originalPrompt" in data
    assert "optimizedPrompt" in data
    assert "originalTokens" in data
    assert "optimizedTokens" in data
    assert "tokensSaved" in data
    assert "reductionPercentage" in data
    assert "semanticScore" in data
    assert "estimatedOriginalCost" in data
    assert "estimatedOptimizedCost" in data
    assert "estimatedCostSaved" in data
    assert "costReductionPercentage" in data
    assert "optimizationStatus" in data


def test_evaluate_endpoint():
    payload = {
        "originalPrompt": "Can you please explain how Docker containers work?",
        "optimizedPrompt": "Explain Docker containers.",
        "model": "gpt-4o",
        "mode": "balanced"
    }
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "originalTokens" in data
    assert "tokensSaved" in data
    assert "semanticScore" in data
    assert "isSafe" in data


def test_model_info_endpoint():
    response = client.get("/model/info")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "supportedModes" in data
    assert "supportedModels" in data
    assert "metrics" in data
