import re
from .rules import RULES


def score_blocks(blocks: list[dict], config: dict) -> dict:
    """
    Score a list of code blocks.
    Returns:
      {
        "score": int,
        "hits": [{"id", "label", "severity", "weight", "block_index"}],
        "blocks_checked": int,
        "flush": bool
      }
    """
    disabled_rules = set(config.get("disabled_rules", []))
    threshold = config.get("threshold", 40)
    total_score = 0
    all_hits = []

    for i, block in enumerate(blocks):
        code = block["code"]
        lang = block["language"]

        for rule in RULES:
            if rule["id"] in disabled_rules:
                continue
            if rule["languages"] and lang not in rule["languages"]:
                continue

            fired = False
            if rule["pattern"]:
                try:
                    if re.search(rule["pattern"], code, re.MULTILINE | re.DOTALL):
                        fired = True
                except re.error:
                    pass

            if not fired and rule["check"]:
                try:
                    if rule["check"](code, lang):
                        fired = True
                except Exception:
                    pass

            if fired:
                total_score += rule["weight"]
                all_hits.append({
                    "id": rule["id"],
                    "label": rule["label"],
                    "severity": rule["severity"],
                    "weight": rule["weight"],
                    "block_index": i,
                })

    return {
        "score": total_score,
        "hits": all_hits,
        "blocks_checked": len(blocks),
        "flush": total_score >= threshold,
    }
