# flush

A Claude Code hook that scores every code response for "smelliness" and plays a pixelated toilet flush animation in your terminal when the code is bad enough then optionally auto-prompts Claude to rewrite it.

```
 flush

      .-----------.        score: 85
      |___________|
    ._____________.        [!] bare except or empty catch     +35
    |             |        [!] >5 function parameters         +25
    |             |        [~] Python function missing hints  +15
    |_____________|        [~] undocumented function          +10
        |     |
    .-----------.           f/ENTER  flush it
   /             \          s        skip
  |               |
  |               |
   \             /
    '___________'
    |___________|
```

---

## how it works

After every Claude turn, a `Stop` hook intercepts the response, extracts all fenced code blocks, and scores them against 15 configurable smell rules. If the total score meets the threshold:

- **manual mode** (default): the terminal UI plays the flush animation and shows the score + violations. You decide whether to send the redo prompt.
- **auto mode**: Claude Code immediately sends a follow-up prompt asking Claude to fix the violations. No UI interaction needed.

The hook always exits cleanly — it never crashes Claude Code.

**[Watch the demo](https://youtu.be/G3HWnpxAXGw)**

---

## rules

| id | label | severity | weight | languages |
|---|---|---|---|---|
| `hardcoded_credentials` | hardcoded password / secret / token | error | 50 | all |
| `bare_except` | bare `except:` or empty catch | error | 35 | all |
| `todo_comment` | TODO / FIXME / HACK comment | error | 30 | all |
| `mutable_default_arg` | mutable default argument (`=[]`, `={}`) | error | 25 | python |
| `too_many_params` | function with >5 parameters | error | 25 | all |
| `nested_loops` | nested `for` loops (O(n²) smell) | warn | 20 | all |
| `no_error_handling` | file/network op without try/except | warn | 20 | python |
| `global_variable` | `global` statement | warn | 15 | all |
| `magic_numbers` | unexplained numeric literals | warn | 15 | all |
| `no_type_hints` | Python function missing type hints | warn | 15 | python |
| `star_import` | `from x import *` | warn | 15 | python |
| `single_char_vars` | single-character variable names | warn | 10 | all |
| `debug_output` | `print()` or `console.log()` | warn | 10 | all |
| `no_docstring` | Python function without docstring | warn | 10 | python |
| `long_lines` | lines over 100 characters | warn | 10 | all |

**Notable thresholds:** a single hardcoded credential (50 pts) always flushes. A bare except + TODO comment (65 pts) always flushes. The default threshold is 40.

### adding a rule

1. Add an entry to `RULES` in `scorer/rules.py` — see existing rules for the schema
2. Add a test in `tests/test_scorer.py`
3. Run `./install.sh` to deploy

---

## requirements

- macOS or Linux
- Python 3.9+
- Claude Code CLI (`claude`)

---

## install

```bash
git clone https://github.com/yourname/flush
cd flush
chmod +x install.sh
./install.sh
```

`install.sh` does four things:

1. Copies `hooks/post_response.py` → `~/.claude/hooks/flush_post_response.py`
2. Copies the scorer package and config → `~/.claude/flush/`
3. Registers the hook in `~/.claude/settings.json` under the `Stop` event
4. Makes hook and UI scripts executable

### verify the install

```bash
# hook is registered
cat ~/.claude/settings.json

# scorer package is in place
ls ~/.claude/flush/scorer/

# hook file exists
ls ~/.claude/hooks/flush_post_response.py
```

`settings.json` should contain exactly one `Stop` hook entry:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/flush_post_response.py"
          }
        ]
      }
    ]
  }
}
```

---

## usage

Open **two terminal tabs**.

**Tab 1 — start the UI:**
```bash
python3 ~/.claude/flush/ui/terminal_ui.py
```

Leave this running. It polls for new flushes every 2 seconds.

**Tab 2 — use Claude Code normally:**
```bash
claude
```

When Claude writes smelly code, the hook fires automatically. Within 2 seconds, Tab 1 plays the animation. After it finishes:

| key | action |
|---|---|
| `f` or `Enter` | copy redo prompt to clipboard — paste into Claude Code |
| `s` | skip this flush |
| `q` | quit the UI |

`s` works at any point — during the animation or at the prompt.

---

## smoke test

Use `printf` (not `echo` — zsh's echo expands `\n` and produces invalid JSON):

```bash
# score 115 — should flush
printf '{"assistant_message":"```python\\ndef calc(x,y,z,a,b,c):\\n    # TODO fix\\n    try:\\n        pass\\n    except:\\n        pass\\n```"}' \
  | python3 ~/.claude/hooks/flush_post_response.py

# check what was written
cat ~/.claude/flush/flush_state.json
```

```bash
# score 35 — below threshold, no flush
printf '{"assistant_message":"```python\\ndef greet(name):\\n    print(name)\\n    return name\\n```"}' \
  | python3 ~/.claude/hooks/flush_post_response.py
```

Expected output in both cases: `{"action": "none"}` — this is correct. In manual mode the hook always returns `none`; the animation is driven by the state file, not the hook's stdout.

---

## config

Edit `~/.claude/flush/config/rules.json` — the hook reads it fresh every run, no restart needed.

```json
{
  "threshold": 40,
  "mode": "manual",
  "disabled_rules": [],
  "redo_prompt_template": "🚽 flush triggered — smell score {score} (threshold: {threshold}).\n\nViolations: {hits}.\n\nPlease rewrite the code fixing all of these."
}
```

### fields

| field | type | default | description |
|---|---|---|---|
| `threshold` | int | `40` | minimum score to trigger flush. lower = more sensitive. range: 20–80 |
| `mode` | `"manual"` or `"auto"` | `"manual"` | manual: you decide. auto: Claude immediately rewrites |
| `disabled_rules` | list of strings | `[]` | rule IDs to ignore |
| `redo_prompt_template` | string | see above | supports `{score}`, `{threshold}`, `{hits}` |

### example configs

**Strict — auto-rewrite, catch almost everything:**
```json
{
  "threshold": 20,
  "mode": "auto",
  "disabled_rules": []
}
```

**Relaxed — for scripts and exploratory code:**
```json
{
  "threshold": 60,
  "mode": "manual",
  "disabled_rules": ["no_docstring", "no_type_hints", "debug_output", "single_char_vars"]
}
```

---

## auto mode

With `"mode": "auto"`, the hook injects the redo prompt directly into Claude Code as the next user turn — Claude rewrites immediately with no UI interaction.

```
Claude writes smelly code
        ↓
hook scores it (score ≥ threshold)
        ↓
hook returns {"action": "prompt", "message": "🚽 flush triggered..."}
        ↓
Claude Code sends that message as the next turn
        ↓
Claude rewrites the code
```

In auto mode the terminal UI is optional — it will still animate if running, but you don't need it.

---

## state file

After every hook run (when code blocks are found), the hook writes `~/.claude/flush/flush_state.json`:

```json
{
  "score": 85,
  "hits": [
    {"id": "bare_except", "label": "bare except or empty catch", "severity": "error", "weight": 35, "block_index": 0},
    {"id": "too_many_params", "label": ">5 function parameters", "severity": "error", "weight": 25, "block_index": 0}
  ],
  "blocks_checked": 1,
  "flush": true
}
```

The terminal UI polls this file every 2 seconds. When `flush` is `true`, it animates and then sets `flush` back to `false` after you act (press `f` or `s`).

---

## tests

```bash
cd flush
python3 -m pytest tests/ -v
```

23 tests covering the extractor and scorer. All should pass.

---

## troubleshooting

**Hook not firing at all**

Check `~/.claude/settings.json` has exactly one `Stop` entry. If you ran `install.sh` multiple times the hook may be registered twice — edit the file manually to deduplicate.

**score always 0 / no flush**

- Check `disabled_rules` in `config/rules.json` — you may have disabled too much
- Language-scoped rules (`no_type_hints`, `no_docstring`, etc.) only fire when the code block has a language tag. If Claude outputs a code block without ` ```python `, those rules won't fire
- Run the smoke test to confirm the scorer works independently

**animation plays but `f` does nothing**

Press `f` only after the animation finishes and the `f/s` prompt appears. During the animation the key does nothing.

**animation stuck on "flushing..."**

Press `s` to escape it, restart the UI. This was a bug (now fixed) where particles spawned indefinitely.

**clipboard empty after pressing `f`**

Requires `pbcopy` (macOS) or `xclip` (Linux). Both should be available by default. If neither is found, the redo prompt is not copied — you can read it from `flush_state.json` hits and construct it manually.

**UI shows old score repeatedly**

The UI only polls for new flushes when in "watching" state. Always dismiss the current animation (`s`) before running new code, otherwise the new flush is acked along with the old one and never shown.

---

## uninstall

```bash
rm ~/.claude/hooks/flush_post_response.py
rm -rf ~/.claude/flush/
```

Then remove the `hooks` block from `~/.claude/settings.json`.

---

## repo structure

```
flush/
├── hooks/
│   └── post_response.py       main hook — reads Claude response, scores, writes state
├── scorer/
│   ├── extractor.py           extracts fenced code blocks from markdown
│   ├── rules.py               15 smell rule definitions
│   ├── scorer.py              applies rules, accumulates score
│   └── config_loader.py       loads config/rules.json with defaults
├── config/
│   └── rules.json             user-editable thresholds and toggles
├── ui/
│   └── terminal_ui.py         curses-based toilet animation UI
├── server/
│   └── state_server.py        optional HTTP server exposing state (unused by default)
├── tests/
│   ├── test_extractor.py
│   ├── test_scorer.py
│   └── fixtures/
├── install_helpers/
│   └── merge_settings.py      merges hook registration into settings.json
├── install.sh
└── settings.patch.json        hook registration snippet
```
