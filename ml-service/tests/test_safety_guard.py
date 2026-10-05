import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import pytest
from app.services.safety_guard import SafetyGuard


def test_safety_guard_preserves_tech_terms():
    original = "Create a Node.js + Express REST API using PostgreSQL with JWT authentication."
    bad_opt = "Create a REST API."
    is_safe, reason, audit = SafetyGuard.validate_preservation(original, bad_opt)
    assert is_safe is False
    assert "Important technical constraints were removed" in reason


def test_safety_guard_preserves_negative_constraints():
    original = "Build a user login system. Do not use MongoDB."
    bad_opt = "Build a user login system."
    is_safe, reason, audit = SafetyGuard.validate_preservation(original, bad_opt)
    assert is_safe is False
    assert "negative constraint" in reason.lower()


def test_safety_guard_preserves_required_format():
    original = "List top 5 ML frameworks. Return response formatted as JSON."
    bad_opt = "List top 5 ML frameworks."
    is_safe, reason, audit = SafetyGuard.validate_preservation(original, bad_opt)
    assert is_safe is False
    assert "format specification was removed" in reason.lower()


def test_safety_guard_valid_preservation():
    original = "Explain JWT authentication in a Node.js and Express.js application."
    good_opt = "Explain JWT authentication in Node.js + Express.js."
    is_safe, reason, audit = SafetyGuard.validate_preservation(original, good_opt)
    assert is_safe is True
    assert reason is None
