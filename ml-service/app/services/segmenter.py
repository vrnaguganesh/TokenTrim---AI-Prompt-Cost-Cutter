import re
from typing import List, Dict, Any


class PromptSegment:
    def __init__(self, index: int, text: str, segment_type: str, is_protected: bool = False):
        self.index = index
        self.text = text
        self.segment_type = segment_type
        self.is_protected = is_protected
        self.label: str = "KEEP"
        self.processed_text: str = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "text": self.text,
            "type": self.segment_type,
            "is_protected": self.is_protected,
            "label": self.label,
            "processed_text": self.processed_text
        }


class PromptSegmenter:
    """Segments prompt into atomic units: code blocks, headings, bullet points, and clauses."""

    @classmethod
    def segment(cls, text: str) -> List[PromptSegment]:
        if not text or not text.strip():
            return []

        segments: List[PromptSegment] = []
        seg_idx = 0

        code_block_pattern = re.compile(r"(```[\s\S]*?```)")
        parts = code_block_pattern.split(text)

        for part in parts:
            if not part:
                continue

            if part.startswith("```") and part.endswith("```"):
                segments.append(PromptSegment(
                    index=seg_idx,
                    text=part,
                    segment_type="code_block",
                    is_protected=True
                ))
                seg_idx += 1
                continue

            lines = part.split("\n")
            for line in lines:
                trimmed_line = line.strip()
                if not trimmed_line:
                    continue

                if re.match(r"^#{1,6}\s+", trimmed_line):
                    segments.append(PromptSegment(
                        index=seg_idx,
                        text=trimmed_line,
                        segment_type="heading",
                        is_protected=True
                    ))
                    seg_idx += 1
                    continue

                if re.match(r"^(\*|-|\+|\d+\.)\s+", trimmed_line):
                    segments.append(PromptSegment(
                        index=seg_idx,
                        text=trimmed_line,
                        segment_type="list_item",
                        is_protected=False
                    ))
                    seg_idx += 1
                    continue

                sentence_splits = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'`])", trimmed_line)
                
                for s in sentence_splits:
                    s_clean = s.strip()
                    if not s_clean:
                        continue

                    segments.append(PromptSegment(
                        index=seg_idx,
                        text=s_clean,
                        segment_type="sentence",
                        is_protected=False
                    ))
                    seg_idx += 1

        return segments
