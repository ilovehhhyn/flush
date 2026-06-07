import json
import os

DEFAULT_CONFIG = {
    "threshold": 40,
    "mode": "manual",
    "disabled_rules": [],
    "redo_prompt_template": (
        "🚽 flush triggered — smell score {score} (threshold: {threshold}).\n\n"
        "Violations: {hits}.\n\n"
        "Please rewrite the code above fixing all of these issues. "
        "Do not repeat any of the flagged patterns."
    ),
}

def load_config() -> dict:
    config_path = os.path.expanduser("~/.claude/flush/config/rules.json")
    if not os.path.exists(config_path):
        return DEFAULT_CONFIG
    with open(config_path) as f:
        user_config = json.load(f)
    merged = {**DEFAULT_CONFIG, **user_config}
    return merged
