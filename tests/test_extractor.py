import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer.extractor import extract_code_blocks


def test_single_block():
    text = "```python\nprint('hello')\n```"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "python"
    assert "print" in blocks[0]["code"]


def test_multiple_blocks():
    text = "```python\nx = 1\n```\n\n```js\nconsole.log(1)\n```"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 2
    assert blocks[0]["language"] == "python"
    assert blocks[1]["language"] == "js"


def test_no_blocks():
    text = "Just plain text with no code blocks."
    blocks = extract_code_blocks(text)
    assert blocks == []


def test_no_language_tag():
    text = "```\nsome code\n```"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "unknown"


def test_tilde_fence():
    text = "~~~python\nprint('hi')\n~~~"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "python"


def test_inline_code_ignored():
    text = "Use `x = 1` inline but no fenced block."
    blocks = extract_code_blocks(text)
    assert blocks == []


def test_empty_block():
    text = "```python\n```"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["code"] == ""


def test_block_with_trailing_whitespace():
    text = "```python\ndef foo():   \n    pass   \n```"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 1
    assert "def foo" in blocks[0]["code"]


def test_language_tag_uppercased_normalized():
    text = "```Python\npass\n```"
    blocks = extract_code_blocks(text)
    assert blocks[0]["language"] == "python"
