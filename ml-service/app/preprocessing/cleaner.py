import re
import unicodedata
from typing import Tuple, Dict, List

# Common filler and conversational noise phrases that carry low semantic value
FILLER_PATTERNS = [
    (r"\b(can\s+you\s+please|could\s+you\s+please|please\s+kindly|kindly|would\s+you\s+kindly)\b", ""),
    (r"\b(can\s+you\s+help\s+me\s+to|could\s+you\s+help\s+me\s+to|help\s+me\s+to)\b", ""),
    (r"\b(i\s+would\s+like\s+you\s+to|i\s+want\s+you\s+to|i\s+need\s+you\s+to|i\s+am\s+asking\s+you\s+to|i\s+am\s+looking\s+for\s+you\s+to)\b", ""),
    (r"\b(i\s+would\s+appreciate\s+it\s+if\s+you\s+could|i\s+would\s+be\s+grateful\s+if\s+you\s+could)\b", ""),
    (r"\b(please\s+make\s+sure\s+that\s+you|make\s+sure\s+that\s+you|make\s+sure\s+you|please\s+ensure\s+that\s+you)\b", "Ensure you"),
    (r"\b(in\s+a\s+very\s+detailed\s+manner|in\s+great\s+detail|as\s+detailed\s+as\s+possible|with\s+a\s+lot\s+of\s+detail)\b", "in detail"),
    (r"\b(if\s+possible|if\s+you\s+can|if\s+applicable|as\s+much\s+as\s+possible)\b", ""),
    (r"\b(it\s+is\s+worth\s+noting\s+that|it\s+is\s+important\s+to\s+note\s+that|please\s+note\s+that|it\s+is\s+worth\s+mentioning\s+that)\b", "Note:"),
    (r"\b(first\s+and\s+foremost|needless\s+to\s+say|as\s+a\s+matter\s+of\s+fact|at\s+this\s+point\s+in\s+time|for\s+what\s+it's\s+worth)\b", ""),
    (r"\b(for\s+the\s+purpose\s+of)\b", "for"),
    (r"\b(in\s+order\s+to)\b", "to"),
    (r"\b(due\s+to\s+the\s+fact\s+that|owing\s+to\s+the\s+fact\s+that)\b", "because"),
    (r"\b(with\s+regard\s+to|with\s+respect\s+to|with\s+reference\s+to|in\s+terms\s+of)\b", "regarding"),
    (r"\b(thank\s+you\s+in\s+advance|thanks\s+in\s+advance|thank\s+you\s+so\s+much|thanks\s+a\s+lot|thanks!|thank\s+you!)\b", ""),
    (r"^(hey|hello|hi|dear\s+ai|greetings|good\s+morning|good\s+evening)[\s,!:]+", ""),
]

# Common compression rewrites: verbose phrasing -> concise phrasing
COMPRESSION_RULES = [
    (r"\bprovide\s+me\s+with\s+a\s+detailed\s+explanation\s+of\s+how\b", "Explain how"),
    (r"\bprovide\s+me\s+with\s+a\s+detailed\s+explanation\s+of\b", "Explain"),
    (r"\bprovide\s+a\s+detailed\s+explanation\s+of\b", "Explain"),
    (r"\bprovide\s+a\s+step\s+by\s+step\s+guide\s+on\s+how\s+to\b", "Provide step-by-step guide to"),
    (r"\bgive\s+me\s+an\s+overview\s+of\b", "Overview"),
    (r"\bwrite\s+a\s+comprehensive\s+tutorial\s+about\b", "Write a tutorial on"),
    (r"\bi\s+am\s+trying\s+to\s+figure\s+out\s+how\s+to\b", "How to"),
    (r"\bhow\s+can\s+one\s+implement\b", "How to implement"),
    (r"\bwhat\s+are\s+the\s+differences\s+between\b", "Compare"),
    (r"\bwhat\s+is\s+the\s+difference\s+between\b", "Compare"),
    (r"\bwhat\s+is\s+the\s+best\s+way\s+to\b", "Best way to"),
    (r"\bcould\s+you\s+please\s+give\s+me\s+examples\s+of\b", "Give examples of"),
    (r"\bplease\s+write\s+code\s+to\b", "Write code to"),
    (r"\bi\s+would\s+like\s+to\s+request\s+that\s+you\b", ""),
    (r"\bprovide\s+a\s+complete\s+list\s+of\b", "List"),
    (r"\bcan\s+you\s+tell\s+me\s+about\b", "Describe"),
]


class TextCleaner:
    """Preprocesses raw prompt texts, protects technical artifacts, and cleans noise."""

    @staticmethod
    def normalize_unicode(text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"[\u200B-\u200D\uFEFF\u00A0]", " ", text)
        return text

    @staticmethod
    def protect_artifacts(text: str) -> Tuple[str, Dict[str, str]]:
        placeholders: Dict[str, str] = {}
        counter = 0

        # 1. Multi-line code blocks ``` ... ```
        def replace_code_block(match):
            nonlocal counter
            key = f"__TOKENTRIM_CODE_BLOCK_{counter}__"
            counter += 1
            placeholders[key] = match.group(0)
            return key

        text = re.sub(r"```[\s\S]*?```", replace_code_block, text)

        # 2. Inline code ` ... `
        def replace_inline_code(match):
            nonlocal counter
            key = f"__TOKENTRIM_INLINE_CODE_{counter}__"
            counter += 1
            placeholders[key] = match.group(0)
            return key

        text = re.sub(r"`[^`\n]+`", replace_inline_code, text)

        # 3. URLs
        def replace_url(match):
            nonlocal counter
            key = f"__TOKENTRIM_URL_{counter}__"
            counter += 1
            placeholders[key] = match.group(0)
            return key

        text = re.sub(r"https?://[^\s<>\"')]+", replace_url, text)

        # 4. Email addresses
        def replace_email(match):
            nonlocal counter
            key = f"__TOKENTRIM_EMAIL_{counter}__"
            counter += 1
            placeholders[key] = match.group(0)
            return key

        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", replace_email, text)

        return text, placeholders

    @staticmethod
    def restore_artifacts(text: str, placeholders: Dict[str, str]) -> str:
        if not placeholders:
            return text
        for key, original in placeholders.items():
            text = text.replace(key, original)
        return text

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @classmethod
    def clean_text(cls, text: str) -> str:
        if not text:
            return ""
        text = cls.normalize_unicode(text)
        text = cls.normalize_whitespace(text)
        return text
