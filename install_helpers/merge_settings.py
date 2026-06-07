#!/usr/bin/env python3
"""Merge settings.patch.json into ~/.claude/settings.json.

Usage: python3 merge_settings.py <settings_path> <patch_path>

For the hooks key, appends to existing arrays rather than overwriting.
All other keys are merged shallowly (patch wins on conflict).
"""

import sys
import json
import os


def merge(base: dict, patch: dict) -> dict:
    result = dict(base)
    for key, val in patch.items():
        if key == "hooks" and isinstance(val, dict) and isinstance(base.get(key), dict):
            merged_hooks = dict(base[key])
            for hook_name, hook_list in val.items():
                if hook_name in merged_hooks:
                    existing = merged_hooks[hook_name]
                    if isinstance(existing, list) and isinstance(hook_list, list):
                        merged_hooks[hook_name] = existing + hook_list
                    else:
                        merged_hooks[hook_name] = hook_list
                else:
                    merged_hooks[hook_name] = hook_list
            result[key] = merged_hooks
        else:
            result[key] = val
    return result


def main():
    if len(sys.argv) != 3:
        print("Usage: merge_settings.py <settings.json> <patch.json>")
        sys.exit(1)

    settings_path = sys.argv[1]
    patch_path = sys.argv[2]

    base = {}
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            try:
                base = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {settings_path} is not valid JSON — treating as empty")

    with open(patch_path) as f:
        patch = json.load(f)

    merged = merge(base, patch)

    with open(settings_path, "w") as f:
        json.dump(merged, f, indent=2)
        f.write("\n")

    print(f"Merged {patch_path} into {settings_path}")


if __name__ == "__main__":
    main()
