import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import pytest
from app.services.segmenter import PromptSegmenter


def test_segment_code_blocks():
    text = "Here is the plan:\n```python\ndef hello():\n    return 'world'\n```\nPlease run it."
    segments = PromptSegmenter.segment(text)
    assert len(segments) >= 2
    code_segs = [s for s in segments if s.segment_type == "code_block"]
    assert len(code_segs) == 1
    assert code_segs[0].is_protected is True
    assert "def hello()" in code_segs[0].text


def test_segment_lists_and_sentences():
    text = "Tasks to execute:\n* Build the auth module.\n* Test the endpoints.\n* Deploy to cloud."
    segments = PromptSegmenter.segment(text)
    list_items = [s for s in segments if s.segment_type == "list_item"]
    assert len(list_items) == 3


def test_segment_empty():
    assert PromptSegmenter.segment("") == []
    assert PromptSegmenter.segment("   ") == []
