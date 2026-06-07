import re

RULES = [
    {
        "id": "todo_comment",
        "label": "TODO / FIXME comment",
        "severity": "error",
        "weight": 30,
        "languages": None,
        "pattern": r"(//|#)\s*(TODO|FIXME|HACK|XXX)\b",
        "check": None,
    },
    {
        "id": "bare_except",
        "label": "bare except or empty catch",
        "severity": "error",
        "weight": 35,
        "languages": None,
        "pattern": r"except:\s*\n\s*pass|catch\s*\(\s*\w*\s*\)\s*\{\s*\}|except\s+Exception\s*:\s*\n\s*pass",
        "check": None,
    },
    {
        "id": "too_many_params",
        "label": ">5 function parameters",
        "severity": "error",
        "weight": 25,
        "languages": None,
        "pattern": None,
        "check": lambda code, lang: _check_too_many_params(code, lang),
    },
    {
        "id": "no_type_hints",
        "label": "Python function missing type hints",
        "severity": "warn",
        "weight": 15,
        "languages": ["python", "py"],
        "pattern": r"def\s+\w+\s*\([^)]*\)\s*:",
        "check": lambda code, lang: bool(re.search(r"def\s+\w+\s*\([^)]*\)\s*:", code))
                                    and "->" not in code,
    },
    {
        "id": "magic_numbers",
        "label": "magic numbers (unexplained literals)",
        "severity": "warn",
        "weight": 15,
        "languages": None,
        "pattern": r"(?<![a-zA-Z_\"'])(?!0\b|1\b)\d{2,}(?![a-zA-Z_\"'])",
        "check": None,
    },
    {
        "id": "single_char_vars",
        "label": "single-character variable names",
        "severity": "warn",
        "weight": 10,
        "languages": None,
        "pattern": r"\b(?!i\b|j\b|k\b|n\b|x\b|y\b|z\b)[a-wA-W]\s*=\s*[^=]",
        "check": None,
    },
    {
        "id": "debug_output",
        "label": "debug output (print / console.log)",
        "severity": "warn",
        "weight": 10,
        "languages": None,
        "pattern": r"console\.log\(|print\(",
        "check": None,
    },
    {
        "id": "no_docstring",
        "label": "undocumented function (no docstring)",
        "severity": "warn",
        "weight": 10,
        "languages": ["python", "py"],
        "pattern": None,
        "check": lambda code, lang: bool(re.search(r"def\s+\w+", code))
                                    and '"""' not in code
                                    and "'''" not in code,
    },
    {
        "id": "long_lines",
        "label": "lines exceeding 100 characters",
        "severity": "warn",
        "weight": 10,
        "languages": None,
        "pattern": None,
        "check": lambda code, lang: any(len(line) > 100 for line in code.split("\n")),
    },
    {
        "id": "nested_loops",
        "label": "nested for loops (O(n²) smell)",
        "severity": "warn",
        "weight": 20,
        "languages": None,
        "pattern": r"for\s+.+:\s*\n[\s]+for\s+.+:",
        "check": None,
    },
    {
        "id": "mutable_default_arg",
        "label": "mutable default argument",
        "severity": "error",
        "weight": 25,
        "languages": ["python", "py"],
        "pattern": r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|\(\))[^)]*\)",
        "check": None,
    },
    {
        "id": "global_variable",
        "label": "global variable usage",
        "severity": "warn",
        "weight": 15,
        "languages": None,
        "pattern": r"^\s*global\s+\w+",
        "check": None,
    },
    {
        "id": "hardcoded_credentials",
        "label": "hardcoded credentials or secrets",
        "severity": "error",
        "weight": 50,
        "languages": None,
        "pattern": r"(password|secret|api_key|token|passwd)\s*=\s*[\"'][^\"']{3,}[\"']",
        "check": None,
    },
    {
        "id": "star_import",
        "label": "wildcard import (from x import *)",
        "severity": "warn",
        "weight": 15,
        "languages": ["python", "py"],
        "pattern": r"from\s+\S+\s+import\s+\*",
        "check": None,
    },
    {
        "id": "no_error_handling",
        "label": "file/network op with no try/except",
        "severity": "warn",
        "weight": 20,
        "languages": ["python", "py"],
        "pattern": None,
        "check": lambda code, lang: _check_no_error_handling(code),
    },
]


def _check_too_many_params(code: str, lang: str) -> bool:
    patterns = [
        r"def\s+\w+\s*\(([^)]+)\)",         # Python
        r"function\s+\w+\s*\(([^)]+)\)",    # JS named
        r"\w+\s*=\s*function\s*\(([^)]+)\)",  # JS assigned
        r"\w+\s*=\s*\(([^)]+)\)\s*=>",       # JS arrow
    ]
    for p in patterns:
        for match in re.finditer(p, code):
            params = [x.strip() for x in match.group(1).split(",") if x.strip()]
            if len(params) > 5:
                return True
    return False


def _check_no_error_handling(code: str) -> bool:
    risky_ops = re.search(
        r"open\(|requests\.(get|post|put|delete)|urllib|http\.client|socket\.", code
    )
    has_try = "try:" in code
    return bool(risky_ops) and not has_try
