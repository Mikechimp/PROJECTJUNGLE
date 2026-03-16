"""Metal drum pattern generator.

Generates MIDI drum events for various metal sub-genres. Uses General MIDI
drum mapping so it works with any GM-compatible drum plugin in FL Studio
(FPC, FL Keys, or third-party like Superior Drummer / EZDrummer).

Each pattern is a list of (tick, note, velocity, duration) tuples for one bar.
"""

import random
from typing import List, Tuple, Dict, Optional

from jungle.core.rhythm import (
    TICKS_PER_BAR, QUARTER, EIGHTH, SIXTEENTH, TRIPLET_8, TRIPLET_16,
    humanize,
)

# --------------------------------------------------------------------------- #
#  General MIDI Drum Map (key selections for metal)
# --------------------------------------------------------------------------- #

KICK      = 36   # Bass Drum 1
SNARE     = 38   # Acoustic Snare
SNARE_RIM = 37   # Side Stick
HIHAT_CL  = 42   # Closed Hi-Hat
HIHAT_OP  = 46   # Open Hi-Hat
HIHAT_PD  = 44   # Pedal Hi-Hat
RIDE      = 51   # Ride Cymbal 1
RIDE_BELL = 53   # Ride Bell
CRASH_1   = 49   # Crash Cymbal 1
CRASH_2   = 57   # Crash Cymbal 2
CHINA     = 52   # Chinese Cymbal
SPLASH    = 55   # Splash Cymbal
TOM_HIGH  = 48   # Hi-Mid Tom
TOM_MID   = 47   # Low-Mid Tom
TOM_LOW   = 45   # Low Tom
TOM_FLOOR = 43   # High Floor Tom

# Event type alias
DrumEvent = Tuple[int, int, int, int]  # (tick, note, velocity, duration)


# --------------------------------------------------------------------------- #
#  Pattern building helpers
# --------------------------------------------------------------------------- #

def _grid(subdivisions: int, bar_count: int = 1) -> List[int]:
    """Return evenly spaced tick positions for *subdivisions* per bar."""
    step = TICKS_PER_BAR // subdivisions
    return [i * step for i in range(subdivisions * bar_count)]


def _place(ticks: List[int], note: int, velocity: int = 100,
           duration: int = SIXTEENTH, human: bool = True) -> List[DrumEvent]:
    """Place a drum hit at each tick."""
    events = []
    for t in ticks:
        if human:
            t, velocity = humanize(t, velocity)
        events.append((t, note, velocity, duration))
    return events


# --------------------------------------------------------------------------- #
#  Core metal patterns (1 bar each, 4/4 time)
# --------------------------------------------------------------------------- #

def straight_eighth_beat() -> List[DrumEvent]:
    """Standard 8th-note metal beat — kick on 1 & 3, snare on 2 & 4."""
    events = []
    eighths = _grid(8)
    # Hi-hat on all eighths
    events += _place(eighths, HIHAT_CL, velocity=90)
    # Kick on beats 1 and 3
    events += _place([eighths[0], eighths[4]], KICK, velocity=110)
    # Snare on beats 2 and 4
    events += _place([eighths[2], eighths[6]], SNARE, velocity=105)
    return events


def double_bass_16th() -> List[DrumEvent]:
    """Double bass drum 16th notes — the metal standard."""
    events = []
    sixteenths = _grid(16)
    # Kick on every 16th
    events += _place(sixteenths, KICK, velocity=105)
    # Snare on beats 2 and 4
    events += _place([sixteenths[4], sixteenths[12]], SNARE, velocity=110)
    # Ride on 8ths for cut
    events += _place(_grid(8), RIDE, velocity=85)
    return events


def blast_beat() -> List[DrumEvent]:
    """Blast beat — alternating kick/snare on 16ths with ride."""
    events = []
    sixteenths = _grid(16)
    for i, t in enumerate(sixteenths):
        if i % 2 == 0:
            events += _place([t], KICK, velocity=115)
            events += _place([t], RIDE, velocity=90)
        else:
            events += _place([t], SNARE, velocity=110)
            events += _place([t], RIDE, velocity=85)
    return events


def half_time_groove() -> List[DrumEvent]:
    """Half-time feel — snare on beat 3, kick pattern varies."""
    events = []
    sixteenths = _grid(16)
    # Snare on beat 3 only
    events += _place([sixteenths[8]], SNARE, velocity=115)
    # Kick on 1, and-of-2, 4
    events += _place([sixteenths[0], sixteenths[6], sixteenths[12]], KICK, velocity=110)
    # Hi-hat 8ths
    events += _place(_grid(8), HIHAT_CL, velocity=80)
    return events


def breakdown_chug() -> List[DrumEvent]:
    """Breakdown pattern — slow, heavy, china cymbal hits."""
    events = []
    eighths = _grid(8)
    # Kick on every downbeat eighth
    events += _place([eighths[0], eighths[2], eighths[4], eighths[6]], KICK, velocity=120)
    # Snare on beat 3
    events += _place([eighths[4]], SNARE, velocity=120)
    # China on beat 1
    events += _place([eighths[0]], CHINA, velocity=100)
    # Open hi-hat accents
    events += _place([eighths[1], eighths[5]], HIHAT_OP, velocity=75)
    return events


def thrash_skank_beat() -> List[DrumEvent]:
    """Thrash skank/D-beat — punk-influenced fast metal beat."""
    events = []
    eighths = _grid(8)
    # Kick on off-beats
    events += _place([eighths[1], eighths[3], eighths[5], eighths[7]], KICK, velocity=105)
    # Snare on all 8ths for that thrash feel
    events += _place(eighths, SNARE, velocity=95)
    # Ride driving
    events += _place(_grid(16), RIDE, velocity=80)
    return events


def doom_slow_pound() -> List[DrumEvent]:
    """Doom metal — sparse, heavy hits with lots of space."""
    events = []
    quarters = _grid(4)
    # Kick on 1
    events += _place([quarters[0]], KICK, velocity=120)
    # Snare on 3
    events += _place([quarters[2]], SNARE, velocity=115)
    # Crash on 1
    events += _place([quarters[0]], CRASH_1, velocity=95)
    # Sparse hi-hat
    events += _place([quarters[1], quarters[3]], HIHAT_CL, velocity=60)
    return events


def djent_syncopated() -> List[DrumEvent]:
    """Djent-style syncopated groove with ghost notes."""
    events = []
    sixteenths = _grid(16)
    # Syncopated kick pattern
    kick_hits = [0, 3, 6, 10, 13]
    events += _place([sixteenths[i] for i in kick_hits], KICK, velocity=115)
    # Snare on 4 and 12 (beats 2 and 4 shifted)
    events += _place([sixteenths[4], sixteenths[12]], SNARE, velocity=110)
    # Ghost snare notes
    ghost_hits = [2, 7, 9, 14]
    events += _place([sixteenths[i] for i in ghost_hits], SNARE, velocity=40)
    # Hi-hat
    events += _place(_grid(8), HIHAT_CL, velocity=75)
    return events


def prog_odd_time(beats: int = 7) -> List[DrumEvent]:
    """Progressive metal odd-time signature feel (still in 4/4 grid).

    Creates a polyrhythmic feel by accenting every *beats* 16th notes.
    """
    events = []
    sixteenths = _grid(16)
    # Accent pattern based on odd grouping
    for i, t in enumerate(sixteenths):
        if i % beats == 0:
            events += _place([t], KICK, velocity=115)
            events += _place([t], CHINA, velocity=90)
        elif i % beats == (beats // 2):
            events += _place([t], SNARE, velocity=105)
    # Ride on 8ths
    events += _place(_grid(8), RIDE, velocity=80)
    return events


# --------------------------------------------------------------------------- #
#  Fills
# --------------------------------------------------------------------------- #

def tom_fill_descending() -> List[DrumEvent]:
    """Classic descending tom fill for the last beat of a bar."""
    events = []
    # Fill occupies the last quarter note (4 sixteenths)
    start = TICKS_PER_BAR - (SIXTEENTH * 4)
    toms = [TOM_HIGH, TOM_MID, TOM_LOW, TOM_FLOOR]
    for i, tom in enumerate(toms):
        t = start + i * SIXTEENTH
        events += _place([t], tom, velocity=105)
    # Crash on the downbeat of the next bar (tick 0 of next bar)
    events += _place([TICKS_PER_BAR], CRASH_1, velocity=110)
    return events


def double_bass_fill() -> List[DrumEvent]:
    """Double bass run fill for the last 2 beats."""
    events = []
    start = TICKS_PER_BAR - (SIXTEENTH * 8)
    for i in range(8):
        t = start + i * SIXTEENTH
        events += _place([t], KICK, velocity=110)
        if i % 2 == 0:
            events += _place([t], SNARE, velocity=100)
    events += _place([TICKS_PER_BAR], CRASH_2, velocity=115)
    return events


def blast_fill() -> List[DrumEvent]:
    """Short blast beat fill for the last beat."""
    events = []
    start = TICKS_PER_BAR - (SIXTEENTH * 4)
    for i in range(4):
        t = start + i * SIXTEENTH
        events += _place([t], KICK, velocity=120)
        events += _place([t], SNARE, velocity=115)
    events += _place([TICKS_PER_BAR], CHINA, velocity=120)
    return events


# --------------------------------------------------------------------------- #
#  Pattern registry
# --------------------------------------------------------------------------- #

PATTERNS: Dict[str, callable] = {
    "straight_eighth":   straight_eighth_beat,
    "double_bass":       double_bass_16th,
    "blast_beat":        blast_beat,
    "half_time":         half_time_groove,
    "breakdown":         breakdown_chug,
    "thrash_skank":      thrash_skank_beat,
    "doom_pound":        doom_slow_pound,
    "djent_syncopated":  djent_syncopated,
    "prog_odd":          prog_odd_time,
}

FILLS: Dict[str, callable] = {
    "tom_descend":  tom_fill_descending,
    "double_bass":  double_bass_fill,
    "blast":        blast_fill,
}


def generate_drum_bar(pattern_name: str = "random",
                      fill: bool = False) -> List[DrumEvent]:
    """Generate one bar of drums.

    If *pattern_name* is 'random', picks a random pattern.
    If *fill* is True, appends a random fill to the pattern.
    """
    if pattern_name == "random":
        pattern_name = random.choice(list(PATTERNS.keys()))

    fn = PATTERNS.get(pattern_name, straight_eighth_beat)
    events = fn()

    if fill:
        fill_fn = random.choice(list(FILLS.values()))
        events += fill_fn()

    return events
