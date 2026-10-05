import tiktoken
from typing import Dict, Any, Optional

# Cache encoders
_ENCODER_CACHE: Dict[str, tiktoken.Encoding] = {}


def get_encoder_for_model(model: str = "gpt-4o") -> tiktoken.Encoding:
    """Returns or caches the tiktoken encoding appropriate for the specified model."""
    model_lower = (model or "").lower()
    
    # Map model identifier to tokenizer encoding
    if "4o" in model_lower:
        encoding_name = "o200k_base"
    elif any(k in model_lower for k in ("gpt-4", "gpt-3.5", "claude", "gemini", "model-a", "model-b")):
        encoding_name = "cl100k_base"
    else:
        try:
            return tiktoken.encoding_for_model(model_lower)
        except Exception:
            encoding_name = "cl100k_base"

    if encoding_name not in _ENCODER_CACHE:
        try:
            _ENCODER_CACHE[encoding_name] = tiktoken.get_encoding(encoding_name)
        except Exception:
            # Fallback to cl100k_base or first available
            _ENCODER_CACHE[encoding_name] = tiktoken.get_encoding("cl100k_base")
            
    return _ENCODER_CACHE[encoding_name]


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Calculates exact token count for text using the model's tokenizer."""
    if not text:
        return 0
    try:
        encoder = get_encoder_for_model(model)
        return len(encoder.encode(text))
    except Exception:
        # Heuristic fallback: ~4 characters per token
        return max(1, len(text.strip().split()))


def get_token_count_details(text: str, model: str = "gpt-4o") -> Dict[str, int]:
    """Returns token count wrapped in standard dictionary response."""
    return {"tokens": count_tokens(text, model)}


def calculate_token_savings(original_tokens: int, optimized_tokens: int) -> Dict[str, Any]:
    """
    Computes token reduction metrics.
    Ensures tokens_saved and reduction_percentage are never falsely reported as positive when compression expanded tokens.
    """
    tokens_saved = original_tokens - optimized_tokens
    
    if original_tokens <= 0:
        return {
            "tokensSaved": 0,
            "reductionPercentage": 0.0
        }

    # Only report non-negative savings
    safe_tokens_saved = max(0, tokens_saved)
    reduction_pct = (tokens_saved / original_tokens) * 100.0
    safe_reduction_pct = max(0.0, round(reduction_pct, 2))

    return {
        "tokensSaved": safe_tokens_saved,
        "reductionPercentage": safe_reduction_pct
    }
