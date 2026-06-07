#!/usr/bin/env python3
"""
flush — terminal toilet UI

  ENTER / f   tell claude to retry (at the prompt)
  s           skip  (any time)
  q           quit  (any time)
"""

import curses
import json
import os
import time
import random
import subprocess

STATE_PATH   = os.path.expanduser("~/.claude/flush/flush_state.json")
PENDING_PATH = os.path.expanduser("~/.claude/flush/pending_prompt.txt")
POLL_SECS    = 2.0
FPS          = 12

# ── Sprite (21 chars wide) ────────────────────────────────────────────────

LID_FRAMES = [
    ["     .-----------.   ",
     "     |___________|   "],   # 0: closed
    ["    .-----------.    ",
     "   ( ----------- )   "],   # 1: cracking
    ["   .-----------.     ",
     "  (               )  "],   # 2: half open
    ["   _______________   ",
     "  |_______________|  "],   # 3: fully open
]

BODY = [
    "   ._____________.   ",
    "   |             |   ",
    "   |             |   ",
    "   |_____________|   ",
    "       |     |       ",
    "    .-----------.    ",
    "   /             \\   ",
    "  |               |  ",
    "  |               |  ",
    "   \\             /   ",
    "    '___________'    ",
    "    |___________|    ",
]

# Poop drawn via colored chars — fits inside the bowl inner area (15 chars wide)
# Row 7 of BODY: red !  centered
# Row 8 of BODY: yellow block pile
POOP_EXCLAIM = "        !        "   # 17 chars, centered at col+3
POOP_TOP     = "     ▄▄▄▄▄     "    # 15 chars
POOP_BASE    = "   █████████   "     # 15 chars

SPLASH_CHARS = "~≋◦·•∘*~≋◦·"

# ── Color pairs ───────────────────────────────────────────────────────────

_BODY  = 1;  _LID   = 2;  _TITLE = 3
_ERR   = 4;  _WARN  = 5;  _SCORE = 6
_DIM   = 7;  _WATER = 8;  _RETRY = 9
_OK    = 10


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    bg = -1
    curses.init_pair(_BODY,  curses.COLOR_WHITE,  bg)
    curses.init_pair(_LID,   curses.COLOR_CYAN,   bg)
    curses.init_pair(_TITLE, curses.COLOR_CYAN,   bg)
    curses.init_pair(_ERR,   curses.COLOR_RED,    bg)
    curses.init_pair(_WARN,  curses.COLOR_YELLOW, bg)
    curses.init_pair(_SCORE, curses.COLOR_CYAN,   bg)
    curses.init_pair(_DIM,   curses.COLOR_WHITE,  bg)
    curses.init_pair(_WATER, curses.COLOR_CYAN,   bg)
    curses.init_pair(_RETRY, curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(_OK,    curses.COLOR_GREEN,  bg)


# ── Drawing ───────────────────────────────────────────────────────────────

def safeadd(win, row, col, text, attr=0):
    mr, mc = win.getmaxyx()
    if row < 0 or row >= mr or col >= mc:
        return
    try:
        win.addstr(row, col, text[:max(0, mc - col)], attr)
    except curses.error:
        pass


def draw_toilet(win, t_row, t_col, lid_frame, particles, smelly=False):
    lid = LID_FRAMES[min(lid_frame, 3)]
    for i, line in enumerate(lid):
        safeadd(win, t_row + i, t_col, line,
                curses.color_pair(_LID) | curses.A_BOLD)
    for i, line in enumerate(BODY):
        safeadd(win, t_row + 2 + i, t_col, line, curses.color_pair(_BODY))

    if smelly:
        inner = t_col + 3           # start of inner bowl area
        # Red ! above the poop
        safeadd(win, t_row + 2 + 6, inner, POOP_EXCLAIM,
                curses.color_pair(_ERR) | curses.A_BOLD)
        # Brown block pile (yellow = closest to brown in standard curses)
        safeadd(win, t_row + 2 + 7, inner, POOP_TOP,
                curses.color_pair(_WARN) | curses.A_BOLD)
        safeadd(win, t_row + 2 + 8, inner, POOP_BASE,
                curses.color_pair(_WARN) | curses.A_BOLD)

    for p in particles:
        safeadd(win, p['row'], p['col'], p['ch'],
                curses.color_pair(_WATER) | curses.A_BOLD)


def draw_score(win, row, col, state):
    mr, mc = win.getmaxyx()
    score = (state or {}).get('score', 0)
    hits  = (state or {}).get('hits',  [])
    safeadd(win, row, col, f"score: {score}",
            curses.color_pair(_SCORE) | curses.A_BOLD)
    for i, h in enumerate(hits[:10]):
        pair = curses.color_pair(_ERR if h['severity'] == 'error' else _WARN)
        tag  = "[!]" if h['severity'] == 'error' else "[~]"
        safeadd(win, row + 2 + i, col,
                f"{tag} {h['label']} +{h['weight']}"[:mc - col - 1], pair)


# ── Particles ─────────────────────────────────────────────────────────────

def big_splash(bowl_row, t_col, n=32):
    cx = t_col + 10
    return [
        {
            'frow': float(bowl_row),
            'fcol': float(cx + random.randint(-7, 7)),
            'row':  bowl_row,
            'col':  cx + random.randint(-7, 7),
            'vy':   -random.uniform(0.7, 2.5),
            'vx':   random.uniform(-0.6, 0.6),
            'ch':   random.choice(SPLASH_CHARS),
            'life': random.randint(10, 26),
        }
        for _ in range(n)
    ]


def tick_particles(particles):
    out = []
    for p in particles:
        p['frow'] += p['vy']
        p['fcol'] += p['vx']
        p['row']   = int(p['frow'])
        p['col']   = int(p['fcol'])
        p['life'] -= 1
        if p['life'] > 0:
            out.append(p)
    return out


# ── State file ────────────────────────────────────────────────────────────

def read_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def ack():
    s = read_state() or {}
    s['flush'] = False
    try:
        with open(STATE_PATH, 'w') as f:
            json.dump(s, f)
    except OSError:
        pass


def build_prompt(state):
    score  = (state or {}).get('score', '?')
    hits   = (state or {}).get('hits',  [])
    labels = ', '.join(h['label'] for h in hits)
    return (
        f"🚽 flush triggered — smell score {score}.\n\n"
        f"Violations: {labels}.\n\n"
        "Please rewrite the code above addressing each violation. "
        "Do not include any of the flagged patterns."
    )


def do_flush(state):
    text = build_prompt(state)
    try:
        with open(PENDING_PATH, 'w') as f:
            f.write(text)
    except OSError:
        pass
    for cmd in (['pbcopy'], ['xclip', '-selection', 'clipboard']):
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            p.communicate(text.encode())
            break
        except FileNotFoundError:
            continue


# ── Main loop ─────────────────────────────────────────────────────────────

def run(stdscr):
    setup_colors()
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(int(1000 / FPS))

    # Phase flow:
    #  watching → detected → (f) → opening → splashing → flushed → watching
    #                       ↘ (s) → watching
    phase     = 'watching'
    state     = None
    lid_frame = 0
    anim_tick = 0
    particles = []
    last_poll = 0.0
    sprite_h  = 2 + len(BODY)   # 14 rows

    while True:
        mr, mc = stdscr.getmaxyx()
        t_row     = max(3, (mr - sprite_h - 6) // 2)
        t_col     = 2
        panel_col = t_col + 21 + 3
        bowl_row  = t_row + 2 + 8   # bowl content row (BODY index 8)

        # ── Poll ─────────────────────────────────────────────────────────
        now = time.time()
        if phase == 'watching' and now - last_poll >= POLL_SECS:
            last_poll = now
            s = read_state()
            if s and s.get('flush'):
                state     = s
                phase     = 'detected'
                lid_frame = 0
                anim_tick = 0
                particles = []

        # ── Input ─────────────────────────────────────────────────────────
        ch = stdscr.getch()

        if ch == ord('q'):
            break

        if ch in (ord('s'), ord('S')) and phase != 'watching':
            ack()
            phase = 'watching'
            state = None
            lid_frame = 0
            particles = []
            anim_tick = 0

        if phase == 'detected' and ch in (ord('f'), ord('F'), 10, 13):
            do_flush(state)
            ack()
            phase     = 'opening'
            lid_frame = 0
            anim_tick = 0

        if phase == 'flushed' and anim_tick > FPS * 4:
            phase = 'watching'
            state = None

        # ── Animation ────────────────────────────────────────────────────
        anim_tick += 1

        if phase == 'opening':
            lid_frame = min(anim_tick // 3, 3)
            if lid_frame >= 3:
                particles = big_splash(bowl_row, t_col)
                phase     = 'splashing'
                anim_tick = 0

        elif phase == 'splashing':
            particles = tick_particles(particles)
            if not particles:
                phase     = 'flushed'
                anim_tick = 0
                lid_frame = 0

        # ── Draw ──────────────────────────────────────────────────────────
        stdscr.erase()

        # Title
        title = " flush "
        safeadd(stdscr, 0, (mc - len(title)) // 2,
                title, curses.color_pair(_TITLE) | curses.A_BOLD | curses.A_REVERSE)

        # Red alert above toilet when smelly code detected
        if phase == 'detected':
            alert = "  !! smelly code detected !!  "
            safeadd(stdscr, t_row - 1, t_col,
                    alert, curses.color_pair(_ERR) | curses.A_BOLD)

        # Toilet sprite
        smelly = (phase == 'detected')
        if phase in ('watching', 'detected', 'flushed'):
            lf = 0
        elif phase == 'opening':
            lf = lid_frame
        else:   # splashing
            lf = 3

        draw_toilet(stdscr, t_row, t_col, lf, particles, smelly=smelly)

        # Score panel (right side)
        if state and phase in ('detected', 'opening', 'splashing', 'flushed'):
            draw_score(stdscr, t_row, panel_col, state)

        # Below-toilet area
        btn_row = t_row + sprite_h + 1
        if phase == 'watching':
            safeadd(stdscr, btn_row, t_col,
                    "watching for code smell...", curses.color_pair(_DIM))

        elif phase == 'detected':
            safeadd(stdscr, btn_row, t_col,
                    "  tell claude to retry  ",
                    curses.color_pair(_RETRY) | curses.A_BOLD)
            safeadd(stdscr, btn_row, t_col + 26,
                    "press ENTER or f", curses.color_pair(_DIM))
            safeadd(stdscr, btn_row + 1, t_col,
                    "  skip  ",
                    curses.color_pair(_DIM))
            safeadd(stdscr, btn_row + 1, t_col + 26,
                    "press s", curses.color_pair(_DIM))

        elif phase == 'flushed':
            safeadd(stdscr, btn_row, t_col,
                    "retry instructions copied to clipboard",
                    curses.color_pair(_OK) | curses.A_BOLD)

        # Status bar
        statuses = {
            'watching':  "q quit",
            'detected':  "ENTER / f = tell claude to retry   s = skip   q = quit",
            'opening':   "flushing...   s = skip   q = quit",
            'splashing': "flushing...   s = skip   q = quit",
            'flushed':   "paste into Claude Code, then send any message to trigger rewrite",
        }
        safeadd(stdscr, mr - 1, 0,
                statuses.get(phase, '')[:mc - 1],
                curses.color_pair(_DIM) | curses.A_DIM)

        stdscr.refresh()


def main():
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
