"""PROJECTJUNGLE — FL Studio MIDI Controller Script.

This script runs inside FL Studio as a MIDI controller script.
It generates metal backing tracks on-the-fly and sends MIDI events
to FL Studio's channels.

INSTALLATION:
1. Copy this file to your FL Studio MIDI scripts folder:
   - Windows: C:\\Program Files\\Image-Line\\FL Studio\\Settings\\Hardware\\
   - macOS: /Applications/FL Studio.app/Contents/Resources/FL/Settings/Hardware/
2. In FL Studio, go to Options > MIDI Settings
3. Under "Controller type", select "PROJECTJUNGLE" from the dropdown
4. Assign it to an input port

FL Studio MIDI Scripting API Reference:
- midi: MIDI message constants and helpers
- channels: Control FL channels (instruments)
- mixer: Control the mixer
- transport: Transport controls (play, stop, tempo)
- ui: UI interaction
- device: Device info and MIDI output

CONTROLS (mapped to MIDI CCs):
- CC 20: Vibe select (0-127 maps to available vibes)
- CC 21: Tempo override (0=auto, 1-127 maps to 60-240 BPM)
- CC 22: Intensity (0=chill, 127=brutal)
- CC 23: Generate new jam (any value triggers generation)
- CC 24: Section type (0=riff, 32=verse, 64=breakdown, 96=solo)
"""

# NOTE: This script uses FL Studio's built-in Python modules.
# When running outside FL Studio, these imports will fail — that's expected.
# The script is designed to be placed in FL Studio's Hardware folder.

try:
    import midi
    import channels
    import mixer
    import transport
    import ui
    import device
    FL_STUDIO = True
except ImportError:
    FL_STUDIO = False

import sys
import os
import random

# Add the project root to path so we can import jungle modules
# When installed via pip, this isn't needed. When running from source:
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from jungle.vibes.metal import get_vibe, list_vibes, VIBES
from jungle.generators.session import generate_session, CH_DRUMS, CH_BASS, CH_GUITAR
from jungle.core.rhythm import PPQ, TICKS_PER_BAR


# --------------------------------------------------------------------------- #
#  State
# --------------------------------------------------------------------------- #

class JungleState:
    """Holds the current jam session state."""
    def __init__(self):
        self.current_vibe = "thrash"
        self.tempo_override = None
        self.intensity = 64          # 0-127
        self.session = None
        self.playing = False
        self.current_bar = 0
        self.bar_events = {}         # bar_idx -> list of events
        self.vibe_list = list_vibes()

    def generate(self):
        """Generate a new jam session based on current settings."""
        bars = 32
        self.session = generate_session(
            vibe_name=self.current_vibe,
            bars=bars,
            tempo=self.tempo_override,
        )
        # Index events by bar for efficient playback
        self.bar_events = {}
        for track_name, events in self.session.tracks.items():
            for ev in events:
                bar_idx = ev.tick // TICKS_PER_BAR
                if bar_idx not in self.bar_events:
                    self.bar_events[bar_idx] = []
                self.bar_events[bar_idx].append(ev)
        self.current_bar = 0

    def set_vibe(self, cc_value: int):
        """Map a CC value (0-127) to a vibe."""
        idx = int(cc_value / 128 * len(self.vibe_list))
        idx = min(idx, len(self.vibe_list) - 1)
        self.current_vibe = self.vibe_list[idx]


STATE = JungleState()


# --------------------------------------------------------------------------- #
#  FL Studio callback functions
# --------------------------------------------------------------------------- #

def OnInit():
    """Called when the script is loaded."""
    if FL_STUDIO:
        device.setHasMeters()
        print("PROJECTJUNGLE Metal Jam Buddy loaded!")
        print(f"Available vibes: {', '.join(list_vibes())}")
        print("Send CC 23 to generate a new jam.")
    STATE.generate()


def OnDeInit():
    """Called when the script is unloaded."""
    STATE.playing = False
    if FL_STUDIO:
        print("PROJECTJUNGLE unloaded.")


def OnMidiMsg(event):
    """Handle incoming MIDI messages.

    This is where we intercept CC messages to control the jam buddy.
    """
    if not FL_STUDIO:
        return

    # Check if it's a CC message
    status = event.status & 0xF0
    if status != 0xB0:  # Not a CC
        return

    cc_num = event.data1
    cc_val = event.data2

    if cc_num == 20:
        # Vibe select
        STATE.set_vibe(cc_val)
        ui.setHintMsg(f"JUNGLE Vibe: {STATE.current_vibe}")
        event.handled = True

    elif cc_num == 21:
        # Tempo override
        if cc_val == 0:
            STATE.tempo_override = None
            ui.setHintMsg("JUNGLE Tempo: Auto")
        else:
            STATE.tempo_override = 60 + int(cc_val / 127 * 180)
            ui.setHintMsg(f"JUNGLE Tempo: {STATE.tempo_override} BPM")
        event.handled = True

    elif cc_num == 22:
        # Intensity
        STATE.intensity = cc_val
        ui.setHintMsg(f"JUNGLE Intensity: {cc_val}")
        event.handled = True

    elif cc_num == 23:
        # Generate new jam
        STATE.generate()
        ui.setHintMsg(f"JUNGLE: New {STATE.current_vibe} jam generated!")
        event.handled = True

    elif cc_num == 24:
        # Section type (for future use)
        event.handled = True


def OnIdle():
    """Called frequently — use for timed playback.

    NOTE: OnIdle timing is not precise enough for tight MIDI playback.
    For production use, export MIDI files and load them into the playlist.
    This provides a basic preview / trigger mechanism.
    """
    pass


# --------------------------------------------------------------------------- #
#  Utility: Send events for a bar to FL Studio channels
# --------------------------------------------------------------------------- #

def send_bar_to_channels(bar_idx: int):
    """Send all MIDI events for a given bar to FL Studio channels.

    This maps:
    - Drum events -> Channel 0 (assign to FPC or drum plugin)
    - Bass events -> Channel 1 (assign to bass plugin)
    - Guitar events -> Channel 2 (assign to guitar plugin)
    """
    if not FL_STUDIO or not STATE.session:
        return

    events = STATE.bar_events.get(bar_idx, [])
    for ev in events:
        # Map our channels to FL Studio channel indices
        if ev.channel == CH_DRUMS:
            fl_channel = 0
        elif ev.channel == CH_BASS:
            fl_channel = 1
        elif ev.channel == CH_GUITAR:
            fl_channel = 2
        else:
            fl_channel = ev.channel

        # Send note to FL channel
        channels.midiNoteOn(fl_channel, ev.note, ev.velocity)


# --------------------------------------------------------------------------- #
#  Standalone test
# --------------------------------------------------------------------------- #

if __name__ == "__main__" and not FL_STUDIO:
    print("PROJECTJUNGLE — FL Studio Controller Script")
    print("=" * 50)
    print()
    print("This script is designed to run inside FL Studio.")
    print("Running standalone test...\n")

    STATE.generate()
    if STATE.session:
        print(STATE.session.summary())
        print(f"\nBars with events: {len(STATE.bar_events)}")
        total = sum(len(v) for v in STATE.bar_events.values())
        print(f"Total events: {total}")
        print("\nTo use in FL Studio:")
        print("1. Copy this file to FL Studio's Hardware folder")
        print("2. Select 'PROJECTJUNGLE' as your MIDI controller")
        print("3. Use CC 20-24 to control the jam buddy")
