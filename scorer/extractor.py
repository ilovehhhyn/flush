import re

def extract_code_blocks(text: str) -> list[dict]:
    """
    Extract all fenced code blocks from a markdown string.
    Returns list of {"language": str, "code": str}
    Handles both ``` and ~~~ fences.
    Ignores inline code (single backtick).
    """
    pattern = r'```(\w*)\n(.*?)```|~~~(\w*)\n(.*?)~~~'
    matches = re.finditer(pattern, text, re.DOTALL)
    blocks = []
    for m in matches:
        if m.group(1) is not None:
            lang = m.group(1) or "unknown"
            code = m.group(2)
        else:
            lang = m.group(3) or "unknown"
            code = m.group(4)
        blocks.append({"language": lang.lower(), "code": code})
    return blocks
