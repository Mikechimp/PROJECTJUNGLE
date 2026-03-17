"""Real-time MIDI playback engine for PROJECTJUNGLE.

Converts tick-based JamSession events into real-time MIDI output,
with looping, track muting, live tempo changes, and transport controls.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from jungle.core.rhythm import PPQ, TICKS_PER_BAR


# --------------------------------------------------------------------------- #
#  MIDI output backends — try multiple, use what's available
# --------------------------------------------------------------------------- #

class MidiOutputBase:
    """Abstract MIDI output."""
    def open(self): ...
    def close(self): ...
    def note_on(self, channel: int, note: int, velocity: int): ...
    def note_off(self, channel: int, note: int): ...
    def all_notes_off(self):
        """Panic — silence everything."""
        for ch in range(16):
            for note in range(128):
                self.note_off(ch, note)


class PygameMidiOutput(MidiOutputBase):
    """Output via pygame.midi (pip install pygame)."""

    def __init__(self, device_id=None):
        self._device_id = device_id
        self._output = None

    def open(self):
        import pygame.midi
        pygame.midi.init()
        if self._device_id is None:
            self._device_id = pygame.midi.get_default_output_id()
        self._output = pygame.midi.Output(self._device_id)

    def close(self):
        if self._output:
            self.all_notes_off()
            self._output.close()
            self._output = None
        import pygame.midi
        pygame.midi.quit()

    def note_on(self, channel, note, velocity):
        if self._output:
            self._output.note_on(note, velocity, channel)

    def note_off(self, channel, note):
        if self._output:
            self._output.note_off(note, 0, channel)


class RtmidiOutput(MidiOutputBase):
    """Output via mido + python-rtmidi (pip install mido python-rtmidi)."""

    def __init__(self, port_name=None):
        self._port_name = port_name
        self._port = None

    def open(self):
        import mido
        if self._port_name:
            self._port = mido.open_output(self._port_name)
        else:
            self._port = mido.open_output()

    def close(self):
        if self._port:
            self.all_notes_off()
            self._port.close()
            self._port = None

    def note_on(self, channel, note, velocity):
        if self._port:
            import mido
            self._port.send(mido.Message('note_on', channel=channel,
                                          note=note, velocity=velocity))

    def note_off(self, channel, note):
        if self._port:
            import mido
            self._port.send(mido.Message('note_off', channel=channel,
                                          note=note, velocity=0))


class WindowsMidiOutput(MidiOutputBase):
    """Output via Windows Multimedia API (zero dependencies, Windows only)."""

    def __init__(self, device_id=0):
        self._device_id = device_id
        self._handle = None

    def open(self):
        import ctypes
        from ctypes import wintypes
        self._winmm = ctypes.windll.winmm
        handle = wintypes.HANDLE()
        result = self._winmm.midiOutOpen(
            ctypes.byref(handle), self._device_id, 0, 0, 0)
        if result != 0:
            raise RuntimeError(f"midiOutOpen failed: error {result}")
        self._handle = handle

    def close(self):
        if self._handle:
            self.all_notes_off()
            self._winmm.midiOutClose(self._handle)
            self._handle = None

    def _send_short(self, status, data1, data2):
        if self._handle:
            msg = status | (data1 << 8) | (data2 << 16)
            self._winmm.midiOutShortMsg(self._handle, msg)

    def note_on(self, channel, note, velocity):
        self._send_short(0x90 | (channel & 0xF), note & 0x7F, velocity & 0x7F)

    def note_off(self, channel, note):
        self._send_short(0x80 | (channel & 0xF), note & 0x7F, 0)

    def all_notes_off(self):
        # Send CC 123 (All Notes Off) on all channels
        if self._handle:
            for ch in range(16):
                self._send_short(0xB0 | ch, 123, 0)


def auto_detect_output() -> MidiOutputBase:
    """Try backends in order and return the first that works."""
    # 1. Try pygame.midi
    try:
        import pygame.midi
        return PygameMidiOutput()
    except ImportError:
        pass

    # 2. Try mido + rtmidi
    try:
        import mido
        import rtmidi  # noqa: F401
        return RtmidiOutput()
    except ImportError:
        pass

    # 3. Try Windows API
    try:
        import ctypes
        ctypes.windll.winmm  # only exists on Windows
        return WindowsMidiOutput()
    except (AttributeError, OSError):
        pass

    raise RuntimeError(
        "No MIDI output available.\n"
        "Install one of:\n"
        "  pip install pygame        (recommended)\n"
        "  pip install mido python-rtmidi\n"
        "Or run on Windows (built-in MIDI support)."
    )


def list_midi_ports() -> List[str]:
    """List available MIDI output ports."""
    ports = []
    try:
        import pygame.midi
        pygame.midi.init()
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            if info[3] == 1:  # is output
                ports.append(f"[pygame:{i}] {info[1].decode()}")
        pygame.midi.quit()
    except ImportError:
        pass
    try:
        import mido
        ports.extend(f"[mido] {p}" for p in mido.get_output_names())
    except ImportError:
        pass
    return ports


# --------------------------------------------------------------------------- #
#  Scheduled MIDI event (for the playback queue)
# --------------------------------------------------------------------------- #

@dataclass
class ScheduledEvent:
    """A MIDI event scheduled at a specific tick."""
    tick: int
    event_type: str       # 'on' or 'off'
    channel: int
    note: int
    velocity: int
    track_name: str       # 'drums', 'bass', 'rhythm_guitar'


# --------------------------------------------------------------------------- #
#  Live Playback Engine
# --------------------------------------------------------------------------- #

class LiveEngine:
    """Real-time MIDI playback engine with looping and live controls.

    Usage:
        engine = LiveEngine()
        engine.load_session(jam_session)
        engine.play()       # starts looping playback
        engine.set_tempo(180)
        engine.mute_track("drums")
        engine.stop()
    """

    def __init__(self, midi_output: Optional[MidiOutputBase] = None):
        self._output = midi_output
        self._events: List[ScheduledEvent] = []
        self._total_ticks = 0
        self._tempo = 120               # BPM
        self._playing = False
        self._looping = True
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Live controls
        self._muted_tracks: Dict[str, bool] = {}
        self._track_velocity_scale: Dict[str, float] = {}  # 0.0 - 1.0

        # Callbacks for UI updates
        self.on_bar_change: Optional[Callable[[int, int], None]] = None
        self.on_beat_change: Optional[Callable[[int], None]] = None
        self.on_loop_restart: Optional[Callable[[], None]] = None
        self.on_playback_stop: Optional[Callable[[], None]] = None
        self.on_note_played: Optional[Callable[[str, int, int], None]] = None

        # Current position
        self._current_bar = 0
        self._current_beat = 0
        self._total_bars = 0

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def tempo(self) -> int:
        return self._tempo

    @property
    def current_bar(self) -> int:
        return self._current_bar

    @property
    def total_bars(self) -> int:
        return self._total_bars

    @property
    def looping(self) -> bool:
        return self._looping

    def load_session(self, session):
        """Load a JamSession into the engine."""
        was_playing = self._playing
        if was_playing:
            self.stop()

        with self._lock:
            self._tempo = session.tempo
            self._total_bars = session.bars
            self._total_ticks = session.bars * TICKS_PER_BAR
            self._events = []

            for track_name, events in session.tracks.items():
                self._muted_tracks.setdefault(track_name, False)
                self._track_velocity_scale.setdefault(track_name, 1.0)

                for ev in events:
                    # Note on
                    self._events.append(ScheduledEvent(
                        tick=ev.tick,
                        event_type='on',
                        channel=ev.channel,
                        note=ev.note,
                        velocity=ev.velocity,
                        track_name=track_name,
                    ))
                    # Note off
                    off_tick = ev.tick + ev.duration
                    # Wrap note-off within session bounds
                    if off_tick > self._total_ticks:
                        off_tick = self._total_ticks
                    self._events.append(ScheduledEvent(
                        tick=off_tick,
                        event_type='off',
                        channel=ev.channel,
                        note=ev.note,
                        velocity=0,
                        track_name=track_name,
                    ))

            # Sort by tick, note-offs before note-ons at same tick
            self._events.sort(key=lambda e: (e.tick, 0 if e.event_type == 'off' else 1))

        if was_playing:
            self.play()

    def open_output(self):
        """Open the MIDI output device."""
        if self._output is None:
            self._output = auto_detect_output()
        self._output.open()

    def close_output(self):
        """Close the MIDI output device."""
        if self._output:
            self._output.close()

    def play(self):
        """Start playback (from beginning)."""
        if self._playing:
            self.stop()
        if not self._output:
            self.open_output()
        self._playing = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop playback and silence all notes."""
        self._playing = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._output:
            self._output.all_notes_off()
        self._current_bar = 0
        self._current_beat = 0
        if self.on_playback_stop:
            self.on_playback_stop()

    def pause(self):
        """Pause playback (keeps position, just stops sending)."""
        self._playing = False
        self._stop_event.set()
        if self._output:
            self._output.all_notes_off()

    def set_tempo(self, bpm: int):
        """Change tempo live (takes effect immediately)."""
        with self._lock:
            self._tempo = max(40, min(300, bpm))

    def set_looping(self, loop: bool):
        """Enable/disable looping."""
        self._looping = loop

    def mute_track(self, track_name: str):
        """Mute a track."""
        self._muted_tracks[track_name] = True

    def unmute_track(self, track_name: str):
        """Unmute a track."""
        self._muted_tracks[track_name] = False

    def toggle_mute(self, track_name: str) -> bool:
        """Toggle mute, returns new muted state."""
        current = self._muted_tracks.get(track_name, False)
        self._muted_tracks[track_name] = not current
        return not current

    def is_muted(self, track_name: str) -> bool:
        return self._muted_tracks.get(track_name, False)

    def set_track_volume(self, track_name: str, volume: float):
        """Set track velocity scale (0.0 = silent, 1.0 = full)."""
        self._track_velocity_scale[track_name] = max(0.0, min(1.0, volume))

    # ------------------------------------------------------------------ #
    #  Playback loop (runs in thread)
    # ------------------------------------------------------------------ #

    def _ticks_to_seconds(self, ticks: int) -> float:
        """Convert ticks to seconds at current tempo."""
        return (ticks / PPQ) * (60.0 / self._tempo)

    def _playback_loop(self):
        """Main playback thread."""
        while not self._stop_event.is_set():
            self._play_once()
            if self._stop_event.is_set():
                break
            if self._looping:
                if self._output:
                    self._output.all_notes_off()
                if self.on_loop_restart:
                    self.on_loop_restart()
            else:
                break

        self._playing = False
        if self.on_playback_stop:
            self.on_playback_stop()

    def _play_once(self):
        """Play through the event list once."""
        if not self._events:
            return

        start_time = time.perf_counter()
        event_idx = 0
        last_bar = -1

        while event_idx < len(self._events) and not self._stop_event.is_set():
            with self._lock:
                tempo = self._tempo

            ev = self._events[event_idx]

            # Calculate when this event should fire
            target_seconds = (ev.tick / PPQ) * (60.0 / tempo)
            elapsed = time.perf_counter() - start_time

            # Wait until it's time
            wait = target_seconds - elapsed
            if wait > 0:
                # Sleep in small increments so we can respond to stop quickly
                # and pick up tempo changes
                while wait > 0 and not self._stop_event.is_set():
                    chunk = min(wait, 0.005)  # 5ms chunks
                    time.sleep(chunk)
                    # Recalculate with potentially new tempo
                    with self._lock:
                        tempo = self._tempo
                    target_seconds = (ev.tick / PPQ) * (60.0 / tempo)
                    elapsed = time.perf_counter() - start_time
                    wait = target_seconds - elapsed

            if self._stop_event.is_set():
                break

            # Update position
            current_bar = ev.tick // TICKS_PER_BAR
            current_beat = (ev.tick % TICKS_PER_BAR) // PPQ
            if current_bar != last_bar:
                self._current_bar = current_bar
                self._current_beat = current_beat
                last_bar = current_bar
                if self.on_bar_change:
                    self.on_bar_change(current_bar, self._total_bars)

            # Send the event (respecting mute)
            if ev.event_type == 'on':
                if not self._muted_tracks.get(ev.track_name, False):
                    vel = int(ev.velocity * self._track_velocity_scale.get(
                        ev.track_name, 1.0))
                    vel = max(1, min(127, vel))
                    self._output.note_on(ev.channel, ev.note, vel)
                    if self.on_note_played:
                        self.on_note_played(ev.track_name, ev.note, vel)
            else:
                # Always send note-off (even for muted tracks, in case
                # they were muted mid-note)
                self._output.note_off(ev.channel, ev.note)

            event_idx += 1
