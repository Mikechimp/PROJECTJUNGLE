# PROJECTJUNGLE

**AI Metal Jam Buddy for FL Studio** — generates randomized metal backing tracks (drums, bass, rhythm guitar) so you can jam, practice leads, and create. Built entirely on the Python standard library with zero external dependencies.

Pick a metal vibe, hit generate, and shred.

---

## Features

- **9 Metal Vibes** — Thrash, Doom, Progressive, Djent, Melodic Death, Death, Black, Groove, and Metalcore. Each vibe has curated tempos, scales, drum patterns, riff styles, and song structures.
- **Drum Engine** — 9 pattern types including double bass 16ths, blast beats, breakdowns, thrash skank beats, djent syncopation, doom pound, and prog odd-time feels. Fills auto-insert at phrase boundaries.
- **Riff Generator** — Power chord progressions, palm-mute chugging, tremolo picking, gallop rhythms, djent staccato, and breakdown sections. 10 metal chord progressions built in.
- **Bass Generator** — Root-lock, octave pulse, 16th-note drive, melodic walking lines, and doom sustain styles. Locks with the rhythm guitar and kick drum.
- **Music Theory Core** — Scales (phrygian, harmonic minor, locrian, diminished, etc.), power chords, drop tunings (D through 8-string), and metal-specific progressions.
- **MIDI Export** — Generates standard MIDI files (Format 1) that load directly into FL Studio, Ableton, Reaper, or any DAW.
- **FL Studio Integration** — Includes a MIDI controller script that runs inside FL Studio for real-time vibe switching and jam generation.
- **Humanized Feel** — Timing and velocity humanization on every hit so it doesn't sound robotic.
- **Zero Dependencies** — Pure Python standard library. No pip installs needed.
- **Reproducible Jams** — Set a random seed to regenerate the exact same jam.

---

## Quick Start

### GUI App (Recommended)

```bash
# Clone and install
git clone https://github.com/Mikechimp/PROJECTJUNGLE.git
cd PROJECTJUNGLE
pip install -e .

# Launch the GUI
python jungle_gui.py
# or
jungle-gui
```

The GUI gives you a visual interface with vibe selection, tempo/tuning controls, and one-click MIDI export.

### Build Standalone .exe (For Distribution)

```bash
pip install pyinstaller
python build_exe.py
```

This creates a single `PROJECTJUNGLE.exe` (or binary on Mac/Linux) in the `dist/` folder that anyone can run — no Python required.

### CLI (Command Line)

```bash
# Generate a random metal jam
jungle

# Pick a vibe
jungle --vibe thrash
jungle --vibe doom --tempo 60
jungle --vibe djent --bars 64

# See all vibes
jungle --list-vibes

# Export to a specific file
jungle --vibe melodeath -o my_jam.mid

# Reproducible jam (same seed = same output)
jungle --vibe groove --seed 42 -o groove_jam.mid
```

---

## Available Vibes

| Vibe | Style | Tempo | Think... |
|------|-------|-------|----------|
| `thrash` | Fast, aggressive, tight | 160-220 BPM | Slayer, Metallica, Megadeth |
| `doom` | Slow, crushing, massive | 50-80 BPM | Black Sabbath, Electric Wizard, Sleep |
| `progressive` | Complex, technical, dynamic | 100-180 BPM | Dream Theater, Tool, Opeth |
| `djent` | Syncopated, polyrhythmic | 110-160 BPM | Meshuggah, Periphery, Animals As Leaders |
| `melodeath` | Melodic + aggressive | 140-200 BPM | In Flames, At The Gates, Dark Tranquillity |
| `death` | Brutal, fast, guttural | 160-240 BPM | Cannibal Corpse, Death, Morbid Angel |
| `black` | Atmospheric, tremolo-heavy | 150-220 BPM | Mayhem, Burzum, Emperor |
| `groove` | Mid-tempo, heavy groove | 100-140 BPM | Pantera, Lamb of God, Machine Head |
| `metalcore` | Breakdowns + melody | 120-170 BPM | Killswitch Engage, Parkway Drive |

---

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--vibe, -v` | Metal sub-genre | `random` |
| `--tempo, -t` | BPM override | auto from vibe |
| `--bars, -b` | Number of bars | `32` |
| `--tuning` | Guitar tuning (drop_d, drop_c, etc.) | auto from vibe |
| `--scale` | Scale override | auto from vibe |
| `--output, -o` | Output .mid file path | `jungle_jam.mid` |
| `--no-drums` | Skip drum track | off |
| `--no-bass` | Skip bass track | off |
| `--no-guitar` | Skip rhythm guitar track | off |
| `--seed` | Random seed for reproducibility | none |
| `--info` | Show session info without exporting | off |
| `--list-vibes` | Show all vibes and exit | |
| `--version` | Show version | |

---

## FL Studio Integration

### Method 1: MIDI File Import (Easiest)
1. Run `jungle --vibe thrash -o jam.mid`
2. Drag `jam.mid` into FL Studio's Playlist
3. FL Studio will split it into separate tracks:
   - **Track 1 (drums)** → assign to FPC, Superior Drummer, or EZDrummer
   - **Track 2 (bass)** → assign to your bass plugin (Trilian, MODO Bass, etc.)
   - **Track 3 (guitar)** → assign to your rhythm guitar plugin (Helix Native, Archetype, etc.)
4. Hit play and solo over it

### Method 2: FL Studio Controller Script (Advanced)
1. Copy `jungle/fl_studio/jungle_controller.py` to FL Studio's Hardware folder:
   - **Windows:** `C:\Program Files\Image-Line\FL Studio\Settings\Hardware\`
   - **macOS:** `/Applications/FL Studio.app/Contents/Resources/FL/Settings/Hardware/`
2. Also copy the entire `jungle/` package to the same location (or install via pip)
3. In FL Studio: Options → MIDI Settings → Controller type → select "PROJECTJUNGLE"
4. Use MIDI CC controls to switch vibes and generate jams on-the-fly:
   - **CC 20:** Vibe select
   - **CC 21:** Tempo override
   - **CC 22:** Intensity
   - **CC 23:** Generate new jam

---

## Project Structure

```
jungle_gui.py                 # Launch the GUI app (double-click or run)
build_exe.py                  # Build standalone .exe with PyInstaller
jungle/
  __init__.py                 # Package metadata
  __main__.py                 # Module entry point
  cli.py                      # CLI argument parsing and orchestration
  gui/
    app.py                    # Desktop GUI application (tkinter)
  core/
    theory.py                 # Scales, chords, progressions, tunings
    rhythm.py                 # Timing, subdivisions, humanization
    midi_export.py            # MIDI file writer (zero dependencies)
  generators/
    drums.py                  # Metal drum pattern generator
    riffs.py                  # Rhythm guitar riff generator
    bass.py                   # Bass line generator
    session.py                # Jam session orchestrator
  vibes/
    metal.py                  # Metal sub-genre presets
  fl_studio/
    jungle_controller.py      # FL Studio MIDI controller script
```

---

## How to Make Money With This

1. **Sell backing tracks** — Generate unique jams, record yourself soloing over them, sell on BeatStars, Bandcamp, or license for sync
2. **YouTube/TikTok content** — "AI generated a random metal backing track and I soloed over it" is engaging content
3. **Practice & improve** — Better skills = better recordings = more opportunities (session work, teaching, gigs)
4. **Expand the tool** — Add more genres, build a GUI, sell it as an FL Studio plugin
5. **Collaboration** — Use it as a songwriting tool to generate ideas you'd never think of

---

## License

See [LICENSE](LICENSE) for details.
