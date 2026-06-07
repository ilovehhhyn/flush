import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer.scorer import score_blocks

DEFAULT_CONFIG = {"threshold": 40, "disabled_rules": []}


def make_block(code, language="python"):
    return {"code": code, "language": language}


def test_clean_code_scores_zero():
    blocks = [make_block('def add(a: int, b: int) -> int:\n    """Add two numbers."""\n    return a + b\n')]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    assert result["score"] == 0
    assert result["hits"] == []
    assert result["flush"] is False


def test_todo_comment_fires():
    blocks = [make_block("# TODO fix this\nx = 1\n")]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "todo_comment" in ids
    weight = next(h["weight"] for h in result["hits"] if h["id"] == "todo_comment")
    assert weight == 30


def test_bare_except_fires():
    blocks = [make_block("try:\n    pass\nexcept:\n    pass\n")]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "bare_except" in ids
    weight = next(h["weight"] for h in result["hits"] if h["id"] == "bare_except")
    assert weight == 35


def test_too_many_params_fires():
    blocks = [make_block("def calc(a, b, c, d, e, f):\n    return a\n")]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "too_many_params" in ids


def test_hardcoded_credentials_fires_with_weight_50():
    blocks = [make_block('password = "hunter2"\n')]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "hardcoded_credentials" in ids
    weight = next(h["weight"] for h in result["hits"] if h["id"] == "hardcoded_credentials")
    assert weight == 50
    assert result["flush"] is True  # 50 >= 40


def test_disabled_rule_does_not_fire():
    config = {"threshold": 40, "disabled_rules": ["todo_comment"]}
    blocks = [make_block("# TODO fix\nx = 1\n")]
    result = score_blocks(blocks, config)
    ids = [h["id"] for h in result["hits"]]
    assert "todo_comment" not in ids


def test_language_scoped_rule_skips_wrong_language():
    blocks = [make_block("def foo():\n    pass\n", language="javascript")]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "no_type_hints" not in ids
    assert "no_docstring" not in ids


def test_language_scoped_rule_fires_on_correct_language():
    blocks = [make_block("def foo():\n    pass\n", language="python")]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "no_type_hints" in ids


def test_score_accumulates_across_multiple_blocks():
    blocks = [
        make_block("# TODO fix\nx = 1\n"),
        make_block('password = "secret123"\n'),
    ]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    assert result["blocks_checked"] == 2
    assert result["score"] >= 80  # 30 (todo) + 50 (credentials)


def test_threshold_is_gte_not_gt():
    # score exactly at threshold should flush
    config = {"threshold": 30, "disabled_rules": []}
    blocks = [make_block("# TODO fix\nx = 1\n")]
    result = score_blocks(blocks, config)
    assert result["score"] == 30
    assert result["flush"] is True


def test_score_below_threshold_no_flush():
    config = {"threshold": 100, "disabled_rules": []}
    blocks = [make_block("# TODO fix\nx = 1\n")]
    result = score_blocks(blocks, config)
    assert result["flush"] is False


def test_mutable_default_arg_fires():
    blocks = [make_block("def foo(data=[]):\n    return data\n")]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "mutable_default_arg" in ids


def test_star_import_fires():
    blocks = [make_block("from os import *\n")]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "star_import" in ids


def test_global_variable_fires():
    blocks = [make_block("def foo():\n    global result\n    result = 1\n")]
    result = score_blocks(blocks, DEFAULT_CONFIG)
    ids = [h["id"] for h in result["hits"]]
    assert "global_variable" in ids
