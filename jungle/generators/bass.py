"""Metal bass line generator.

Generates MIDI events for bass guitar that lock in with the rhythm guitar
and drums. Styles range from root-note following to melodic fills.
"""

import random
from typing import List, Tuple

from jungle.core.theory import get_scale_notes, get_progression, random_progression
from jungle.core.rhythm import (
    TICKS_PER_BAR, QUARTER, EIGHTH, SIXTEENTH, humanize,
)

BassEvent = Tuple[int, int, int, int]  # (tick, note, velocity, duration)


def root_lock(root_midi: int, progression: List[int],
              bars: int = 4) -> List[List[BassEvent]]:
    """Bass follows the root of each chord — 8th-note pulse.

    This is the most common metal bass approach: lock with the kick drum
    on the root notes of whatever the guitar is playing.
    """
    all_bars = []
    for bar_idx in range(bars):
        offset = progression[bar_idx % len(progression)]
        note = root_midi + offset
        events = []
        for i in range(8):
            t = i * EIGHTH
            vel = 100 if i % 2 == 0 else 85
            t_h, vel = humanize(t, vel, timing_ms=5, vel_range=6)
            events.append((t_h, note, vel, EIGHTH - 20))
        all_bars.append(events)
    return all_bars


def octave_pulse(root_midi: int, progression: List[int],
                 bars: int = 4) -> List[List[BassEvent]]:
    """Alternates between root and octave on 8th notes."""
    all_bars = []
    for bar_idx in range(bars):
        offset = progression[bar_idx % len(progression)]
        root = root_midi + offset
        octave = root + 12
        events = []
        for i in range(8):
            t = i * EIGHTH
            note = root if i % 2 == 0 else octave
            vel = 105 if i % 2 == 0 else 90
            t_h, vel = humanize(t, vel)
            events.append((t_h, note, vel, EIGHTH - 20))
        all_bars.append(events)
    return all_bars


def sixteenth_drive(root_midi: int, progression: List[int],
                    bars: int = 4) -> List[List[BassEvent]]:
    """Aggressive 16th-note bass drive — matches double bass drums."""
    all_bars = []
    for bar_idx in range(bars):
        offset = progression[bar_idx % len(progression)]
        note = root_midi + offset
        events = []
        for i in range(16):
            t = i * SIXTEENTH
            vel = 95 + (15 if i % 4 == 0 else 0)
            t_h, vel = humanize(t, vel, timing_ms=3, vel_range=4)
            events.append((t_h, note, vel, SIXTEENTH - 25))
        all_bars.append(events)
    return all_bars


def melodic_walk(root_midi: int, scale_name: str,
                 progression: List[int],
                 bars: int = 4) -> List[List[BassEvent]]:
    """Walking bass line using scale tones — more prog/melodeath feel."""
    all_bars = []
    for bar_idx in range(bars):
        offset = progression[bar_idx % len(progression)]
        bar_root = root_midi + offset
        scale = get_scale_notes(bar_root, scale_name, octaves=1)
        events = []
        # Walk through 4-5 scale tones per bar in quarter/8th mix
        walk = random.sample(scale[:7], min(4, len(scale)))
        walk.sort()
        if random.random() > 0.5:
            walk.reverse()
        for i, note in enumerate(walk):
            t = i * QUARTER
            vel = random.randint(90, 110)
            t_h, vel = humanize(t, vel)
            events.append((t_h, note, vel, QUARTER - 30))
        all_bars.append(events)
    return all_bars


def doom_sustain(root_midi: int, progression: List[int],
                 bars: int = 4) -> List[List[BassEvent]]:
    """Long sustained notes — doom/sludge style. One note per bar."""
    all_bars = []
    for bar_idx in range(bars):
        offset = progression[bar_idx % len(progression)]
        note = root_midi + offset
        vel = random.randint(100, 120)
        t_h, vel = humanize(0, vel, timing_ms=8)
        events = [(t_h, note, vel, TICKS_PER_BAR - 60)]
        all_bars.append(events)
    return all_bars


# --------------------------------------------------------------------------- #
#  Registry
# --------------------------------------------------------------------------- #

BASS_STYLES = {
    "root_lock":     root_lock,
    "octave_pulse":  octave_pulse,
    "sixteenth":     sixteenth_drive,
    "melodic_walk":  melodic_walk,
    "doom_sustain":  doom_sustain,
}


def generate_bass_section(style: str = "random",
                          root_midi: int = 38,
                          scale_name: str = "natural_minor",
                          progression_name: str = "random",
                          bars: int = 4) -> List[List[BassEvent]]:
    """Generate bass for a section. Returns list of bars."""
    if style == "random":
        style = random.choice(list(BASS_STYLES.keys()))

    _, prog = random_progression() if progression_name == "random" \
        else (progression_name, get_progression(progression_name))

    fn = BASS_STYLES.get(style, root_lock)

    if style == "melodic_walk":
        return fn(root_midi, scale_name, prog, bars)
    else:
        return fn(root_midi, prog, bars)
