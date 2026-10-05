import re
from typing import List, Dict, Tuple, Set
from .cleaner import TextCleaner, FILLER_PATTERNS, COMPRESSION_RULES


class PromptNormalizer:
    """Normalizes prompt clauses, applies safe compression rewrites, and strips low-information fluff."""

    @classmethod
    def apply_filler_stripping(cls, text: str) -> str:
        working = text
        for pattern, replacement in FILLER_PATTERNS:
            working = re.sub(pattern, replacement, working, flags=re.IGNORECASE)
        return TextCleaner.normalize_whitespace(working)

    @classmethod
    def apply_compression_rules(cls, text: str) -> str:
        working = text
        for pattern, replacement in COMPRESSION_RULES:
            working = re.sub(pattern, replacement, working, flags=re.IGNORECASE)
        return TextCleaner.normalize_whitespace(working)

    @classmethod
    def normalize_clause(cls, clause: str, mode: str = "balanced") -> str:
        if not clause or not clause.strip():
            return ""

        text, placeholders = TextCleaner.protect_artifacts(clause)
        
        # Step 1: Strip polite/filler noise
        text = cls.apply_filler_stripping(text)

        # Step 2: Apply concise compression substitutions if aggressive or balanced
        if mode in ("aggressive", "balanced"):
            text = cls.apply_compression_rules(text)

        # Step 3: Normalize whitespace
        text = TextCleaner.normalize_whitespace(text)

        # Step 4: Restore protected artifacts
        text = TextCleaner.restore_artifacts(text, placeholders)
        return text.strip()
