"""Metal riff and rhythm guitar generator.

Creates MIDI events for rhythm guitar parts: chugging patterns, power chord
progressions, tremolo picking, and palm-muted sections.

All events are (tick, note, velocity, duration) tuples.
"""

import random
from typing import List, Tuple

from jungle.core.theory import (
    build_chord, get_scale_notes, get_progression, random_progression,
    get_tuning_root, METAL_PROGRESSIONS,
)
from jungle.core.rhythm import (
    TICKS_PER_BAR, QUARTER, EIGHTH, SIXTEENTH, TRIPLET_8,
    humanize,
)

RiffEvent = Tuple[int, int, int, int]  # (tick, note, velocity, duration)


# --------------------------------------------------------------------------- #
#  Riff patterns
# --------------------------------------------------------------------------- #

def power_chord_progression(root_midi: int,
                            progression: List[int],
                            bars: int = 4) -> List[List[RiffEvent]]:
    """Generate bars of power chords following a progression.

    Each chord gets one bar of steady 8th-note chugging.
    Returns a list of bars, each bar is a list of events.
    """
    all_bars = []
    for bar_idx in range(bars):
        chord_offset = progression[bar_idx % len(progression)]
        chord_root = root_midi + chord_offset
        chord_notes = build_chord(chord_root, "power_oct")
        events: List[RiffEvent] = []
        eighths = [i * EIGHTH for i in range(8)]
        for t in eighths:
            vel = random.randint(95, 115)
            t_h, vel = humanize(t, vel)
            for note in chord_notes:
                events.append((t_h, note, vel, EIGHTH - 20))
        all_bars.append(events)
    return all_bars


def palm_mute_chug(root_midi: int, bars: int = 2) -> List[List[RiffEvent]]:
    """Tight palm-muted 16th note chugging on the root.

    Low velocity + short duration = palm mute feel in most guitar VSTs.
    """
    all_bars = []
    for _ in range(bars):
        events = []
        sixteenths = [i * SIXTEENTH for i in range(16)]
        for i, t in enumerate(sixteenths):
            vel = 75 + (15 if i % 4 == 0 else 0)  # accent downbeats
            t_h, vel = humanize(t, vel, timing_ms=5, vel_range=5)
            events.append((t_h, root_midi, vel, SIXTEENTH - 30))
        all_bars.append(events)
    return all_bars


def tremolo_riff(root_midi: int, scale_name: str = "natural_minor",
                 bars: int = 2) -> List[List[RiffEvent]]:
    """Tremolo-picked melodic riff using scale tones.

    Picks a short motif from the scale and repeats with variation.
    """
    scale = get_scale_notes(root_midi, scale_name, octaves=2)
    # Pick a 4-note motif
    start_idx = random.randint(0, max(0, len(scale) - 5))
    motif = scale[start_idx:start_idx + 4]
    if len(motif) < 4:
        motif = scale[:4]

    all_bars = []
    for bar_idx in range(bars):
        events = []
        sixteenths = [i * SIXTEENTH for i in range(16)]
        for i, t in enumerate(sixteenths):
            note = motif[i % len(motif)]
            # Vary the motif slightly on the second bar
            if bar_idx % 2 == 1 and i >= 12:
                note = motif[0]  # resolve to root
            vel = random.randint(90, 110)
            t_h, vel = humanize(t, vel, timing_ms=3)
            events.append((t_h, note, vel, SIXTEENTH - 10))
        all_bars.append(events)
    return all_bars


def gallop_pattern(root_midi: int,
                   progression: List[int],
                   bars: int = 4) -> List[List[RiffEvent]]:
    """Galloping rhythm (8th + two 16ths) — iron maiden / melodeath style."""
    all_bars = []
    for bar_idx in range(bars):
        chord_offset = progression[bar_idx % len(progression)]
        chord_root = root_midi + chord_offset
        notes = build_chord(chord_root, "power")
        events = []
        # 4 gallop groups per bar (one per beat)
        for beat in range(4):
            base = beat * QUARTER
            # 8th note
            vel = random.randint(100, 115)
            t, v = humanize(base, vel)
            for n in notes:
                events.append((t, n, v, EIGHTH - 20))
            # Two 16ths
            for sub in range(2):
                st = base + EIGHTH + sub * SIXTEENTH
                vel = random.randint(85, 100)
                t, v = humanize(st, vel)
                for n in notes:
                    events.append((t, n, v, SIXTEENTH - 20))
        all_bars.append(events)
    return all_bars


def djent_staccato(root_midi: int, bars: int = 2) -> List[List[RiffEvent]]:
    """Djent-style staccato chugging with syncopated accents and rests."""
    all_bars = []
    # A djent rhythm pattern: 1 = hit, 0 = rest (16th note grid)
    patterns = [
        [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],
        [1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0],
        [1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    ]
    for bar_idx in range(bars):
        pattern = random.choice(patterns)
        events = []
        for i, hit in enumerate(pattern):
            if hit:
                t = i * SIXTEENTH
                vel = 120 if i % 4 == 0 else 100
                t_h, vel = humanize(t, vel, timing_ms=3, vel_range=4)
                notes = build_chord(root_midi, "power_oct")
                for n in notes:
                    events.append((t_h, n, vel, SIXTEENTH - 40))
        all_bars.append(events)
    return all_bars


def breakdown_riff(root_midi: int, bars: int = 4) -> List[List[RiffEvent]]:
    """Breakdown section — slow, heavy, half-step dissonance."""
    all_bars = []
    for bar_idx in range(bars):
        events = []
        eighths = [i * EIGHTH for i in range(8)]
        # Alternate between root and half-step up for tension
        for i, t in enumerate(eighths):
            if i < 6:
                note = root_midi
            else:
                note = root_midi + 1  # half-step tension
            vel = 120 if i % 2 == 0 else 95
            notes = build_chord(note, "power_oct")
            t_h, vel = humanize(t, vel, timing_ms=5)
            for n in notes:
                events.append((t_h, n, vel, EIGHTH - 15))
        all_bars.append(events)
    return all_bars


# --------------------------------------------------------------------------- #
#  Registry
# --------------------------------------------------------------------------- #

RIFF_STYLES = {
    "power_chords":  "power_chord_progression",
    "palm_mute":     "palm_mute_chug",
    "tremolo":       "tremolo_riff",
    "gallop":        "gallop_pattern",
    "djent":         "djent_staccato",
    "breakdown":     "breakdown_riff",
}


def generate_riff_section(style: str = "random",
                          root_midi: int = 38,
                          scale_name: str = "natural_minor",
                          progression_name: str = "random",
                          bars: int = 4) -> List[List[RiffEvent]]:
    """High-level riff generator. Returns a list of bars.

    *style*: riff style name or 'random'.
    *root_midi*: root note MIDI number (default D2 = drop D).
    """
    if style == "random":
        style = random.choice(list(RIFF_STYLES.keys()))

    prog_name, prog = random_progression() if progression_name == "random" \
        else (progression_name, get_progression(progression_name))

    if style == "power_chords":
        return power_chord_progression(root_midi, prog, bars)
    elif style == "palm_mute":
        return palm_mute_chug(root_midi, bars)
    elif style == "tremolo":
        return tremolo_riff(root_midi, scale_name, bars)
    elif style == "gallop":
        return gallop_pattern(root_midi, prog, bars)
    elif style == "djent":
        return djent_staccato(root_midi, bars)
    elif style == "breakdown":
        return breakdown_riff(root_midi, bars)
    else:
        return power_chord_progression(root_midi, prog, bars)
