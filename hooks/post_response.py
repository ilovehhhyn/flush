#!/usr/bin/env python3

import sys
import json
import os

sys.path.insert(0, os.path.expanduser("~/.claude/flush"))

from scorer.extractor import extract_code_blocks
from scorer.scorer import score_blocks
from scorer.config_loader import load_config


PENDING_PATH = os.path.expanduser("~/.claude/flush/pending_prompt.txt")


def main():
    # If the user pressed 'f' in the UI, fire the queued redo prompt first.
    if os.path.exists(PENDING_PATH):
        try:
            with open(PENDING_PATH) as f:
                prompt = f.read().strip()
            os.remove(PENDING_PATH)
            if prompt:
                print(json.dumps({"action": "prompt", "message": prompt}))
                sys.exit(0)
        except OSError:
            pass

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"action": "none"}))
        sys.exit(0)

    config = load_config()

    # Claude Code Stop hook sends last_assistant_message (str or content-block list).
    # Fall back to transcript_path file, then assistant_message for smoke tests.
    message = ""
    lam = data.get("last_assistant_message", "")
    if isinstance(lam, str):
        message = lam
    elif isinstance(lam, list):
        message = "\n".join(
            b.get("text", "") for b in lam
            if isinstance(b, dict) and b.get("type") == "text"
        )

    if not message:
        tp = data.get("transcript_path", "")
        if tp and os.path.exists(tp):
            try:
                with open(tp) as f:
                    lines = f.readlines()
                for line in reversed(lines):
                    try:
                        entry = json.loads(line)
                        if entry.get("role") == "assistant":
                            content = entry.get("content", "")
                            if isinstance(content, str):
                                message = content
                            elif isinstance(content, list):
                                message = "\n".join(
                                    b.get("text", "") for b in content
                                    if isinstance(b, dict) and b.get("type") == "text"
                                )
                            break
                    except json.JSONDecodeError:
                        continue
            except OSError:
                pass

    if not message:
        message = data.get("assistant_message", "")

    blocks = extract_code_blocks(message)
    if not blocks:
        print(json.dumps({"action": "none"}))
        sys.exit(0)

    result = score_blocks(blocks, config)

    state_path = os.path.expanduser("~/.claude/flush/flush_state.json")
    with open(state_path, "w") as f:
        json.dump(result, f)

    threshold = config.get("threshold", 40)
    mode = config.get("mode", "manual")

    if result["score"] >= threshold:
        hits = result["hits"]
        hit_labels = ", ".join(h["label"] for h in hits)

        if mode == "auto":
            redo_prompt = (
                f"🚽 flush triggered — smell score {result['score']} (threshold: {threshold}).\n\n"
                f"Violations detected: {hit_labels}.\n\n"
                f"Please rewrite the code above addressing each of these issues. "
                f"Do not include any of the flagged patterns in the new version."
            )
            print(json.dumps({"action": "prompt", "message": redo_prompt}))
        else:
            print(json.dumps({"action": "none"}))
    else:
        print(json.dumps({"action": "none"}))

    sys.exit(0)


if __name__ == "__main__":
    main()
