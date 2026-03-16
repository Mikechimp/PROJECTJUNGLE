"""Command-line interface for PROJECTJUNGLE.

Generate metal backing tracks from the terminal and export as MIDI files
for use in FL Studio or any DAW.
"""

import argparse
import sys

from jungle import __version__
from jungle.vibes.metal import list_vibes, get_vibe, VIBES
from jungle.generators.session import generate_session
from jungle.core.midi_export import export_midi
from jungle.core.theory import TUNINGS, SCALES, note_name


def main():
    parser = argparse.ArgumentParser(
        prog="jungle",
        description="PROJECTJUNGLE — AI Metal Jam Buddy. "
                    "Generates randomized metal backing tracks as MIDI files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  jungle                          Generate a random metal jam
  jungle --vibe thrash            Thrash metal backing track
  jungle --vibe doom --tempo 65   Slow doom at 65 BPM
  jungle --vibe djent -b 64       64 bars of djent
  jungle --list-vibes             Show all available vibes
  jungle --vibe melodeath -o jam.mid   Export to specific file
        """,
    )

    parser.add_argument("--version", action="version",
                        version=f"PROJECTJUNGLE v{__version__}")

    parser.add_argument("--vibe", "-v", default="random",
                        help="Metal sub-genre vibe (default: random). "
                             "Use --list-vibes to see options.")

    parser.add_argument("--list-vibes", action="store_true",
                        help="List all available metal vibes and exit.")

    parser.add_argument("--tempo", "-t", type=int, default=None,
                        help="Override tempo in BPM (default: auto from vibe).")

    parser.add_argument("--bars", "-b", type=int, default=32,
                        help="Number of bars to generate (default: 32).")

    parser.add_argument("--tuning", default=None,
                        choices=list(TUNINGS.keys()),
                        help="Guitar tuning (default: auto from vibe).")

    parser.add_argument("--scale", default=None,
                        choices=list(SCALES.keys()),
                        help="Scale to use (default: auto from vibe).")

    parser.add_argument("--output", "-o", default=None,
                        help="Output MIDI file path (default: jungle_jam.mid).")

    parser.add_argument("--no-drums", action="store_true",
                        help="Generate without drums (guitar + bass only).")

    parser.add_argument("--no-bass", action="store_true",
                        help="Generate without bass (guitar + drums only).")

    parser.add_argument("--no-guitar", action="store_true",
                        help="Generate without rhythm guitar (drums + bass only).")

    parser.add_argument("--info", action="store_true",
                        help="Show session info without exporting.")

    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible jams.")

    args = parser.parse_args()

    # List vibes
    if args.list_vibes:
        print("Available Metal Vibes:")
        print("=" * 60)
        for name, vibe in VIBES.items():
            print(f"  {name:15s} {vibe.description}")
            print(f"  {'':15s} Tempo: {vibe.tempo_range[0]}-{vibe.tempo_range[1]} BPM")
            print()
        return

    # Set seed
    if args.seed is not None:
        import random
        random.seed(args.seed)

    # Generate
    print(f"Generating metal jam...")
    session = generate_session(
        vibe_name=args.vibe,
        bars=args.bars,
        tempo=args.tempo,
        tuning=args.tuning,
        scale=args.scale,
    )

    # Remove tracks if requested
    if args.no_drums and "drums" in session.tracks:
        del session.tracks["drums"]
    if args.no_bass and "bass" in session.tracks:
        del session.tracks["bass"]
    if args.no_guitar and "rhythm_guitar" in session.tracks:
        del session.tracks["rhythm_guitar"]

    # Show info
    print()
    print(session.summary())
    print()

    if args.info:
        return

    # Export
    output = args.output or "jungle_jam.mid"
    export_midi(session, output)
    print(f"Exported to: {output}")
    print()
    print("Load this MIDI file into FL Studio:")
    print("  1. Drag the .mid file into the FL Studio Playlist")
    print("  2. Assign tracks to your instruments:")
    print("     - Track 1 (drums)  -> FPC / Superior Drummer / EZDrummer")
    print("     - Track 2 (bass)   -> your bass plugin")
    print("     - Track 3 (guitar) -> your rhythm guitar plugin")
    print("  3. Hit play and shred!")


if __name__ == "__main__":
    main()
