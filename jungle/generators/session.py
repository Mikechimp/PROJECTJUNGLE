"""Jam session orchestrator.

Coordinates drums, bass, and rhythm guitar generators to produce a complete
backing track. This is the main entry point for generating a jam.
"""

import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

from jungle.core.theory import get_tuning_root, random_progression, get_progression
from jungle.core.rhythm import TICKS_PER_BAR, PPQ
from jungle.vibes.metal import MetalVibe, get_vibe
from jungle.generators.drums import generate_drum_bar, PATTERNS, FILLS
from jungle.generators.riffs import generate_riff_section
from jungle.generators.bass import generate_bass_section


@dataclass
class TrackEvent:
    """A single MIDI event in the session."""
    tick: int          # absolute tick position
    channel: int       # MIDI channel (0-15)
    note: int          # MIDI note number
    velocity: int      # 0-127
    duration: int      # in ticks


@dataclass
class JamSession:
    """A complete jam session ready for MIDI export or FL Studio playback."""
    vibe_name: str
    tempo: int
    key_root: int
    scale: str
    tuning: str
    bars: int
    tracks: Dict[str, List[TrackEvent]] = field(default_factory=dict)
    # tracks: "drums", "bass", "rhythm_guitar"

    def all_events(self) -> List[TrackEvent]:
        """Return all events across all tracks, sorted by tick."""
        events = []
        for track_events in self.tracks.values():
            events.extend(track_events)
        events.sort(key=lambda e: (e.tick, e.channel))
        return events

    def duration_seconds(self) -> float:
        """Approximate duration in seconds."""
        total_ticks = self.bars * TICKS_PER_BAR
        seconds_per_tick = 60.0 / (self.tempo * PPQ)
        return total_ticks * seconds_per_tick

    def summary(self) -> str:
        """Human-readable summary of the session."""
        mins = int(self.duration_seconds() // 60)
        secs = int(self.duration_seconds() % 60)
        return (
            f"Jam Session: {self.vibe_name}\n"
            f"  Tempo: {self.tempo} BPM\n"
            f"  Key: MIDI {self.key_root} | Scale: {self.scale}\n"
            f"  Tuning: {self.tuning}\n"
            f"  Length: {self.bars} bars (~{mins}:{secs:02d})\n"
            f"  Tracks: {', '.join(self.tracks.keys())}\n"
            f"  Total events: {sum(len(v) for v in self.tracks.values())}"
        )


# MIDI channels
CH_DRUMS  = 9   # GM standard: channel 10 (0-indexed = 9)
CH_BASS   = 1
CH_GUITAR = 2


def generate_session(
    vibe_name: str = "random",
    bars: int = 32,
    tempo: Optional[int] = None,
    tuning: Optional[str] = None,
    scale: Optional[str] = None,
    key_root: Optional[int] = None,
    progression_name: str = "random",
) -> JamSession:
    """Generate a complete jam session.

    Parameters
    ----------
    vibe_name : str
        Metal sub-genre vibe ('thrash', 'doom', 'djent', etc.) or 'random'.
    bars : int
        Number of bars to generate.
    tempo : int, optional
        Override tempo (otherwise picked from vibe).
    tuning : str, optional
        Override tuning (otherwise picked from vibe).
    scale : str, optional
        Override scale (otherwise picked from vibe).
    key_root : int, optional
        Override root note MIDI number (otherwise derived from tuning).
    progression_name : str
        Chord progression name or 'random'.

    Returns
    -------
    JamSession
        Complete session with drums, bass, and rhythm guitar tracks.
    """
    vibe = get_vibe(vibe_name)

    # Resolve parameters
    _tempo = tempo or vibe.pick_tempo()
    _tuning = tuning or vibe.pick_tuning()
    _scale = scale or vibe.pick_scale()
    _root = key_root or get_tuning_root(_tuning)
    _prog_name = progression_name if progression_name != "random" \
        else vibe.pick_progression()

    session = JamSession(
        vibe_name=vibe.name,
        tempo=_tempo,
        key_root=_root,
        scale=_scale,
        tuning=_tuning,
        bars=bars,
    )

    # -- Generate drums ---------------------------------------------------- #
    drum_events = []
    structure = vibe.structure or ["riff"] * bars
    for bar_idx in range(bars):
        section = structure[bar_idx % len(structure)]
        # Pick drum pattern based on section
        if section == "breakdown":
            pattern = "breakdown"
        elif section == "solo_section":
            pattern = random.choice(["straight_eighth", "half_time"])
        else:
            pattern = vibe.pick_drum()

        add_fill = (bar_idx + 1) % 4 == 0 and random.random() < vibe.fill_frequency
        bar_events = generate_drum_bar(pattern, fill=add_fill)

        # Offset to absolute position
        bar_offset = bar_idx * TICKS_PER_BAR
        for tick, note, vel, dur in bar_events:
            drum_events.append(TrackEvent(
                tick=bar_offset + tick,
                channel=CH_DRUMS,
                note=note,
                velocity=vel,
                duration=dur,
            ))
    session.tracks["drums"] = drum_events

    # -- Generate rhythm guitar -------------------------------------------- #
    guitar_events = []
    section_bars_done = 0
    while section_bars_done < bars:
        section_len = min(4, bars - section_bars_done)
        section_idx = section_bars_done % len(structure) if structure else 0
        section = structure[section_idx] if structure else "riff"

        if section == "solo_section":
            # Leave space — no rhythm guitar during solo section
            section_bars_done += section_len
            continue

        riff_style = vibe.pick_riff()
        if section == "breakdown":
            riff_style = "breakdown"

        riff_bars = generate_riff_section(
            style=riff_style,
            root_midi=_root,
            scale_name=_scale,
            progression_name=_prog_name,
            bars=section_len,
        )
        for i, bar in enumerate(riff_bars):
            bar_offset = (section_bars_done + i) * TICKS_PER_BAR
            for tick, note, vel, dur in bar:
                guitar_events.append(TrackEvent(
                    tick=bar_offset + tick,
                    channel=CH_GUITAR,
                    note=note,
                    velocity=vel,
                    duration=dur,
                ))
        section_bars_done += section_len
    session.tracks["rhythm_guitar"] = guitar_events

    # -- Generate bass ----------------------------------------------------- #
    bass_events = []
    section_bars_done = 0
    while section_bars_done < bars:
        section_len = min(4, bars - section_bars_done)
        bass_style = vibe.pick_bass()

        bass_bars = generate_bass_section(
            style=bass_style,
            root_midi=_root,
            scale_name=_scale,
            progression_name=_prog_name,
            bars=section_len,
        )
        for i, bar in enumerate(bass_bars):
            bar_offset = (section_bars_done + i) * TICKS_PER_BAR
            for tick, note, vel, dur in bar:
                bass_events.append(TrackEvent(
                    tick=bar_offset + tick,
                    channel=CH_BASS,
                    note=note,
                    velocity=vel,
                    duration=dur,
                ))
        section_bars_done += section_len
    session.tracks["bass"] = bass_events

    return session
