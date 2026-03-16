"""Music theory foundations for metal jam generation.

Handles scales, intervals, chord construction, and MIDI note mapping.
Everything is in MIDI note numbers (0-127) where middle C = 60.
"""

import random
from typing import List, Tuple, Optional

# --------------------------------------------------------------------------- #
#  MIDI helpers
# --------------------------------------------------------------------------- #

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def note_name(midi_note: int) -> str:
    """Return the note name + octave for a MIDI note number."""
    octave = (midi_note // 12) - 1
    return f"{NOTE_NAMES[midi_note % 12]}{octave}"

def name_to_midi(name: str, octave: int = 2) -> int:
    """Convert a note name like 'C' or 'D#' + octave to MIDI number."""
    idx = NOTE_NAMES.index(name.upper())
    return (octave + 1) * 12 + idx

# --------------------------------------------------------------------------- #
#  Scales (as semitone intervals from the root)
# --------------------------------------------------------------------------- #

SCALES = {
    # Core metal scales
    "natural_minor":     [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor":    [0, 2, 3, 5, 7, 8, 11],
    "phrygian":          [0, 1, 3, 5, 7, 8, 10],
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],
    "locrian":           [0, 1, 3, 5, 6, 8, 10],
    "diminished":        [0, 2, 3, 5, 6, 8, 9, 11],
    "chromatic":         list(range(12)),
    "minor_pentatonic":  [0, 3, 5, 7, 10],
    "blues":             [0, 3, 5, 6, 7, 10],
    "whole_tone":        [0, 2, 4, 6, 8, 10],
    # Drop-tuning: just shifts the root, handled elsewhere
}

def get_scale_notes(root_midi: int, scale_name: str, octaves: int = 2) -> List[int]:
    """Return a list of MIDI notes for a scale across *octaves* octaves."""
    intervals = SCALES.get(scale_name, SCALES["natural_minor"])
    notes = []
    for octave in range(octaves):
        for iv in intervals:
            n = root_midi + octave * 12 + iv
            if 0 <= n <= 127:
                notes.append(n)
    return notes

# --------------------------------------------------------------------------- #
#  Chord types (intervals from root)
# --------------------------------------------------------------------------- #

CHORD_TYPES = {
    "power":         [0, 7],         # 1-5 — the metal staple
    "power_oct":     [0, 7, 12],     # 1-5-8
    "minor":         [0, 3, 7],
    "major":         [0, 4, 7],
    "dim":           [0, 3, 6],
    "aug":           [0, 4, 8],
    "minor7":        [0, 3, 7, 10],
    "dom7":          [0, 4, 7, 10],
    "dim7":          [0, 3, 6, 9],
    "sus2":          [0, 2, 7],
    "sus4":          [0, 5, 7],
    "add9":          [0, 4, 7, 14],
}

def build_chord(root_midi: int, chord_type: str = "power") -> List[int]:
    """Return MIDI notes for a chord rooted at *root_midi*."""
    intervals = CHORD_TYPES.get(chord_type, CHORD_TYPES["power"])
    return [root_midi + iv for iv in intervals if 0 <= root_midi + iv <= 127]

# --------------------------------------------------------------------------- #
#  Common metal progressions (as semitone offsets from the key root)
# --------------------------------------------------------------------------- #

METAL_PROGRESSIONS = {
    "classic_metal":     [0, 3, 5, 7],       # i - bIII - iv - v
    "thrash_chug":       [0, 1, 0, 5],       # i - bII - i - iv
    "doom_crawl":        [0, 5, 3, 0],       # i - iv - bIII - i
    "phrygian_evil":     [0, 1, 3, 1],       # i - bII - bIII - bII
    "djent_riff":        [0, 0, 10, 8],      # i - i - bVII - bVI (rhythmic)
    "prog_odyssey":      [0, 7, 5, 8, 3],    # i - v - iv - bVI - bIII
    "melodeath_gallop":  [0, 5, 7, 3, 8],    # i - iv - v - bIII - bVI
    "breakdown":         [0, 0, 0, 1],       # chug on root, half-step tension
    "harmonic_minor_run":[0, 7, 8, 11],      # i - v - bVI - vii (harmonic minor)
    "chromatic_descent":  [0, 11, 10, 9],    # descending chromatically
}

def get_progression(name: str) -> List[int]:
    """Return a progression by name, or a random one."""
    if name == "random":
        name = random.choice(list(METAL_PROGRESSIONS.keys()))
    return METAL_PROGRESSIONS.get(name, METAL_PROGRESSIONS["classic_metal"])

def random_progression() -> Tuple[str, List[int]]:
    """Return a random progression name and its intervals."""
    name = random.choice(list(METAL_PROGRESSIONS.keys()))
    return name, METAL_PROGRESSIONS[name]

# --------------------------------------------------------------------------- #
#  Tunings (lowest string MIDI note)
# --------------------------------------------------------------------------- #

TUNINGS = {
    "standard_e":  40,  # E2
    "drop_d":      38,  # D2
    "drop_c":      36,  # C2
    "drop_b":      35,  # B1
    "drop_a":      33,  # A1
    "seven_string": 35, # B1 (7-string standard)
    "eight_string": 28, # E1 (8-string, F#1 is 30 but some go lower)
}

def get_tuning_root(tuning: str = "drop_d") -> int:
    """Return the MIDI note number for the lowest string in a tuning."""
    return TUNINGS.get(tuning, TUNINGS["drop_d"])
