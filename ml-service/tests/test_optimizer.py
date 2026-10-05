import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import pytest
from app.services.optimization_engine import OptimizationEngine


def test_optimize_polite_prompt():
    prompt = "Can you please provide me with a detailed explanation of how JWT authentication works in a Node.js and Express.js application?"
    result = OptimizationEngine.optimize(prompt, model="gpt-4o", mode="balanced")
    assert result["optimizationStatus"] == "accepted"
    assert result["tokensSaved"] > 0
    assert result["reductionPercentage"] > 0.0
    assert result["semanticScore"] >= 0.85
    assert "JWT" in result["optimizedPrompt"]
    assert "Node" in result["optimizedPrompt"]


def test_optimize_preserves_negative_rule():
    prompt = "Create a Node.js API with PostgreSQL. Do not use MongoDB."
    result = OptimizationEngine.optimize(prompt, model="gpt-4o", mode="quality")
    assert "MongoDB" in result["optimizedPrompt"] or "not" in result["optimizedPrompt"].lower()
    assert result["optimizationStatus"] == "accepted"


def test_optimize_empty_prompt():
    result = OptimizationEngine.optimize("", model="gpt-4o")
    assert result["optimizationStatus"] == "rejected"
    assert result["originalTokens"] == 0
