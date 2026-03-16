"""MIDI file writer — zero dependencies.

Writes standard MIDI files (Format 1) that can be loaded into FL Studio,
any DAW, or played back with any MIDI player. Uses only the struct module
from the standard library.
"""

import struct
from typing import List, BinaryIO

from jungle.core.rhythm import PPQ


def _var_len(value: int) -> bytes:
    """Encode an integer as a MIDI variable-length quantity."""
    result = []
    result.append(value & 0x7F)
    value >>= 7
    while value:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.reverse()
    return bytes(result)


def _tempo_event(bpm: int) -> bytes:
    """Create a MIDI tempo meta-event."""
    microseconds = int(60_000_000 / bpm)
    return (
        b'\x00'                           # delta time = 0
        b'\xFF\x51\x03'                   # meta event: set tempo
        + struct.pack('>I', microseconds)[1:]  # 3 bytes, big-endian
    )


def _track_name_event(name: str) -> bytes:
    """Create a MIDI track name meta-event."""
    name_bytes = name.encode('ascii', errors='replace')
    return (
        b'\x00'
        b'\xFF\x03'
        + _var_len(len(name_bytes))
        + name_bytes
    )


def _end_of_track() -> bytes:
    """Create an end-of-track meta-event."""
    return b'\x00\xFF\x2F\x00'


def _note_on(delta: int, channel: int, note: int, velocity: int) -> bytes:
    """Create a note-on event."""
    return (
        _var_len(delta)
        + bytes([0x90 | (channel & 0x0F), note & 0x7F, velocity & 0x7F])
    )


def _note_off(delta: int, channel: int, note: int) -> bytes:
    """Create a note-off event."""
    return (
        _var_len(delta)
        + bytes([0x80 | (channel & 0x0F), note & 0x7F, 0])
    )


def _write_chunk(f: BinaryIO, chunk_type: bytes, data: bytes):
    """Write a MIDI chunk (header or track)."""
    f.write(chunk_type)
    f.write(struct.pack('>I', len(data)))
    f.write(data)


def export_midi(session, filepath: str):
    """Export a JamSession to a standard MIDI file.

    Parameters
    ----------
    session : JamSession
        The generated jam session.
    filepath : str
        Output .mid file path.
    """
    from jungle.generators.session import TrackEvent

    track_names = list(session.tracks.keys())
    num_tracks = len(track_names) + 1  # +1 for tempo track

    with open(filepath, 'wb') as f:
        # --- Header chunk ---
        header_data = struct.pack('>HHH', 1, num_tracks, PPQ)
        _write_chunk(f, b'MThd', header_data)

        # --- Tempo track ---
        tempo_data = bytearray()
        tempo_data += _track_name_event("Tempo")
        tempo_data += _tempo_event(session.tempo)
        tempo_data += _end_of_track()
        _write_chunk(f, b'MTrk', bytes(tempo_data))

        # --- Instrument tracks ---
        for track_name in track_names:
            events = session.tracks[track_name]
            track_data = bytearray()
            track_data += _track_name_event(track_name)

            # Sort events by tick, then build note-on / note-off pairs
            sorted_events = sorted(events, key=lambda e: e.tick)

            # Build a timeline of on/off messages
            messages = []
            for ev in sorted_events:
                messages.append((ev.tick, 'on', ev.channel, ev.note, ev.velocity))
                off_tick = ev.tick + ev.duration
                messages.append((off_tick, 'off', ev.channel, ev.note, 0))

            messages.sort(key=lambda m: (m[0], 0 if m[1] == 'off' else 1))

            prev_tick = 0
            for msg in messages:
                tick, msg_type, ch, note, vel = msg
                delta = max(0, tick - prev_tick)
                if msg_type == 'on':
                    track_data += _note_on(delta, ch, note, vel)
                else:
                    track_data += _note_off(delta, ch, note)
                prev_tick = tick

            track_data += _end_of_track()
            _write_chunk(f, b'MTrk', bytes(track_data))
