import re
from typing import List, Dict, Set, Tuple, Any
from ..preprocessing.cleaner import TextCleaner, FILLER_PATTERNS
from .segmenter import PromptSegmenter, PromptSegment


class BaselineOptimizer:
    """
    Stage 1 Baseline Optimizer:
    Uses rule-based redundancy detection, TF-IDF / term frequency heuristics,
    and duplicate n-gram / Jaccard similarity suppression.
    """

    @classmethod
    def compute_jaccard(cls, tokens_a: Set[str], tokens_b: Set[str]) -> float:
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))
        return intersection / union if union > 0 else 0.0

    @classmethod
    def tokenize_words(cls, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b\w+\b", text)]

    @classmethod
    def optimize(cls, text: str, mode: str = "balanced") -> Tuple[str, List[Dict[str, Any]]]:
        if not text:
            return "", []

        segments = PromptSegmenter.segment(text)
        retained_segments: List[str] = []
        seen_token_sets: List[Set[str]] = []
        segment_decisions: List[Dict[str, Any]] = []

        jaccard_threshold = 0.65 if mode == "aggressive" else (0.75 if mode == "balanced" else 0.85)

        for seg in segments:
            if seg.is_protected:
                retained_segments.append(seg.text)
                decision = seg.to_dict()
                decision["label"] = "KEEP"
                segment_decisions.append(decision)
                continue

            cleaned_seg = seg.text
            for pattern, rep in FILLER_PATTERNS:
                cleaned_seg = re.sub(pattern, rep, cleaned_seg, flags=re.IGNORECASE).strip()

            tokens = set(cls.tokenize_words(cleaned_seg))
            
            is_duplicate = False
            for prev_tokens in seen_token_sets:
                if cls.compute_jaccard(tokens, prev_tokens) >= jaccard_threshold and len(tokens) > 3:
                    is_duplicate = True
                    break

            if is_duplicate or not cleaned_seg:
                decision = seg.to_dict()
                decision["label"] = "REMOVE"
                decision["processed_text"] = ""
                segment_decisions.append(decision)
            else:
                seen_token_sets.append(tokens)
                retained_segments.append(cleaned_seg)
                decision = seg.to_dict()
                decision["label"] = "KEEP" if cleaned_seg == seg.text else "COMPRESS"
                decision["processed_text"] = cleaned_seg
                segment_decisions.append(decision)

        optimized_text = TextCleaner.normalize_whitespace("\n".join(retained_segments))
        return optimized_text, segment_decisions
