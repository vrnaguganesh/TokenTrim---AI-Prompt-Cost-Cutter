import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import pytest
from app.services.tokenizer import count_tokens, calculate_token_savings, get_token_count_details


def test_count_tokens():
    text = "Hello world, this is a test prompt."
    tokens = count_tokens(text, model="gpt-4o")
    assert tokens > 0
    assert isinstance(tokens, int)


def test_get_token_count_details():
    res = get_token_count_details("Testing token count response", model="gpt-4o")
    assert "tokens" in res
    assert res["tokens"] > 0


def test_calculate_token_savings_positive():
    res = calculate_token_savings(100, 70)
    assert res["tokensSaved"] == 30
    assert res["reductionPercentage"] == 30.0


def test_calculate_token_savings_never_negative():
    res = calculate_token_savings(50, 60)
    assert res["tokensSaved"] == 0
    assert res["reductionPercentage"] == 0.0


def test_calculate_token_savings_zero_tokens():
    res = calculate_token_savings(0, 0)
    assert res["tokensSaved"] == 0
    assert res["reductionPercentage"] == 0.0
