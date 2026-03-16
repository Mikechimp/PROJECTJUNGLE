"""Rhythm and timing utilities for jam generation.

All timing is in "ticks" where 1 beat = 480 ticks (standard MIDI PPQ).
A bar of 4/4 = 1920 ticks.
"""

PPQ = 480               # Pulses (ticks) per quarter note
TICKS_PER_BAR = PPQ * 4  # 4/4 time

# Subdivision helpers
WHOLE     = PPQ * 4    # 1920
HALF      = PPQ * 2    # 960
QUARTER   = PPQ        # 480
EIGHTH    = PPQ // 2   # 240
SIXTEENTH = PPQ // 4   # 120
TRIPLET_8 = PPQ // 3   # 160  (eighth-note triplet)
TRIPLET_16 = PPQ // 6  # 80   (sixteenth-note triplet)


def swing(tick: int, amount: float = 0.1) -> int:
    """Apply a swing offset to off-beat eighth notes.

    *amount* ranges from 0.0 (straight) to 0.5 (hard swing).
    """
    import random
    # Only swing off-beat eighths
    position_in_beat = tick % QUARTER
    if position_in_beat == EIGHTH:
        offset = int(EIGHTH * amount)
        return tick + random.randint(0, offset)
    return tick


def humanize(tick: int, velocity: int, timing_ms: int = 10,
             vel_range: int = 8) -> tuple:
    """Add slight random timing and velocity variation for human feel."""
    import random
    # Convert ms to ticks (rough: at 120 BPM, 1 tick ≈ 1.04 ms)
    timing_ticks = max(1, timing_ms)
    t = tick + random.randint(-timing_ticks, timing_ticks)
    v = max(1, min(127, velocity + random.randint(-vel_range, vel_range)))
    return max(0, t), v
