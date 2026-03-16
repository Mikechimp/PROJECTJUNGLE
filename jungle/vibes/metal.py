"""Metal sub-genre vibe presets.

Each vibe defines the typical parameters for a metal sub-genre:
tempo range, preferred scales, drum patterns, riff styles, bass styles,
and song structure templates.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import random


@dataclass
class MetalVibe:
    """Defines the musical personality of a metal sub-genre."""
    name: str
    description: str
    tempo_range: Tuple[int, int]           # BPM min/max
    scales: List[str]                       # preferred scales
    tunings: List[str]                      # preferred tunings
    drum_patterns: List[str]                # preferred drum patterns
    riff_styles: List[str]                  # preferred riff styles
    bass_styles: List[str]                  # preferred bass styles
    progressions: List[str]                 # preferred chord progressions
    structure: List[str] = field(default_factory=list)  # song section order
    fill_frequency: float = 0.25           # chance of a fill each bar

    def pick_tempo(self) -> int:
        return random.randint(*self.tempo_range)

    def pick_scale(self) -> str:
        return random.choice(self.scales)

    def pick_tuning(self) -> str:
        return random.choice(self.tunings)

    def pick_drum(self) -> str:
        return random.choice(self.drum_patterns)

    def pick_riff(self) -> str:
        return random.choice(self.riff_styles)

    def pick_bass(self) -> str:
        return random.choice(self.bass_styles)

    def pick_progression(self) -> str:
        return random.choice(self.progressions)


# --------------------------------------------------------------------------- #
#  Vibe presets
# --------------------------------------------------------------------------- #

VIBES: Dict[str, MetalVibe] = {
    "thrash": MetalVibe(
        name="Thrash Metal",
        description="Fast, aggressive, tight riffing. Slayer, Metallica, Megadeth.",
        tempo_range=(160, 220),
        scales=["natural_minor", "phrygian", "minor_pentatonic", "blues"],
        tunings=["standard_e", "drop_d"],
        drum_patterns=["thrash_skank", "double_bass", "straight_eighth"],
        riff_styles=["palm_mute", "gallop", "power_chords", "tremolo"],
        bass_styles=["root_lock", "sixteenth"],
        progressions=["thrash_chug", "classic_metal", "phrygian_evil"],
        structure=["riff", "riff", "verse", "verse", "riff", "riff",
                   "breakdown", "solo_section", "riff", "riff"],
        fill_frequency=0.2,
    ),

    "doom": MetalVibe(
        name="Doom Metal",
        description="Slow, crushing, massive tone. Black Sabbath, Electric Wizard, Sleep.",
        tempo_range=(50, 80),
        scales=["natural_minor", "blues", "minor_pentatonic", "phrygian"],
        tunings=["drop_c", "drop_b", "drop_d"],
        drum_patterns=["doom_pound", "half_time"],
        riff_styles=["power_chords", "tremolo"],
        bass_styles=["doom_sustain", "root_lock"],
        progressions=["doom_crawl", "classic_metal"],
        structure=["riff", "riff", "riff", "riff", "solo_section",
                   "riff", "riff", "riff", "riff"],
        fill_frequency=0.1,
    ),

    "progressive": MetalVibe(
        name="Progressive Metal",
        description="Complex, technical, dynamic. Dream Theater, Tool, Opeth.",
        tempo_range=(100, 180),
        scales=["natural_minor", "harmonic_minor", "phrygian_dominant",
                "diminished", "whole_tone"],
        tunings=["standard_e", "drop_d", "seven_string"],
        drum_patterns=["prog_odd", "double_bass", "half_time", "djent_syncopated"],
        riff_styles=["power_chords", "tremolo", "gallop", "djent"],
        bass_styles=["melodic_walk", "octave_pulse", "root_lock"],
        progressions=["prog_odyssey", "harmonic_minor_run", "classic_metal"],
        structure=["riff", "verse", "riff", "verse", "breakdown",
                   "solo_section", "riff", "verse", "riff"],
        fill_frequency=0.3,
    ),

    "djent": MetalVibe(
        name="Djent",
        description="Syncopated, polyrhythmic, tight. Meshuggah, Periphery, Animals As Leaders.",
        tempo_range=(110, 160),
        scales=["natural_minor", "phrygian", "diminished", "harmonic_minor"],
        tunings=["drop_b", "drop_a", "seven_string", "eight_string"],
        drum_patterns=["djent_syncopated", "prog_odd", "double_bass"],
        riff_styles=["djent", "palm_mute"],
        bass_styles=["root_lock", "sixteenth"],
        progressions=["djent_riff", "chromatic_descent", "breakdown"],
        structure=["riff", "riff", "breakdown", "riff",
                   "solo_section", "breakdown", "riff"],
        fill_frequency=0.35,
    ),

    "melodeath": MetalVibe(
        name="Melodic Death Metal",
        description="Melodic + aggressive. In Flames, At The Gates, Dark Tranquillity.",
        tempo_range=(140, 200),
        scales=["harmonic_minor", "natural_minor", "phrygian_dominant",
                "minor_pentatonic"],
        tunings=["drop_d", "drop_c", "standard_e"],
        drum_patterns=["double_bass", "blast_beat", "straight_eighth"],
        riff_styles=["tremolo", "gallop", "power_chords"],
        bass_styles=["root_lock", "octave_pulse", "melodic_walk"],
        progressions=["melodeath_gallop", "harmonic_minor_run",
                      "classic_metal", "phrygian_evil"],
        structure=["riff", "riff", "verse", "riff", "verse",
                   "solo_section", "breakdown", "riff", "riff"],
        fill_frequency=0.25,
    ),

    "death": MetalVibe(
        name="Death Metal",
        description="Brutal, fast, guttural. Cannibal Corpse, Death, Morbid Angel.",
        tempo_range=(160, 240),
        scales=["phrygian", "locrian", "chromatic", "diminished"],
        tunings=["drop_c", "drop_b", "drop_a"],
        drum_patterns=["blast_beat", "double_bass", "thrash_skank"],
        riff_styles=["tremolo", "palm_mute", "power_chords"],
        bass_styles=["sixteenth", "root_lock"],
        progressions=["chromatic_descent", "phrygian_evil", "thrash_chug"],
        structure=["riff", "riff", "riff", "breakdown",
                   "riff", "riff", "breakdown", "riff"],
        fill_frequency=0.2,
    ),

    "black": MetalVibe(
        name="Black Metal",
        description="Atmospheric, tremolo-heavy, blast beats. Mayhem, Burzum, Emperor.",
        tempo_range=(150, 220),
        scales=["natural_minor", "harmonic_minor", "phrygian", "diminished"],
        tunings=["standard_e", "drop_d"],
        drum_patterns=["blast_beat", "double_bass", "straight_eighth"],
        riff_styles=["tremolo", "power_chords"],
        bass_styles=["root_lock", "doom_sustain"],
        progressions=["phrygian_evil", "harmonic_minor_run", "classic_metal"],
        structure=["riff", "riff", "riff", "riff", "verse",
                   "riff", "riff", "riff", "riff"],
        fill_frequency=0.15,
    ),

    "groove": MetalVibe(
        name="Groove Metal",
        description="Mid-tempo, heavy groove. Pantera, Lamb of God, Machine Head.",
        tempo_range=(100, 140),
        scales=["minor_pentatonic", "blues", "natural_minor", "phrygian"],
        tunings=["drop_d", "drop_c"],
        drum_patterns=["half_time", "straight_eighth", "breakdown"],
        riff_styles=["palm_mute", "power_chords", "breakdown"],
        bass_styles=["root_lock", "octave_pulse"],
        progressions=["classic_metal", "breakdown", "doom_crawl"],
        structure=["riff", "verse", "riff", "verse", "breakdown",
                   "solo_section", "breakdown", "riff"],
        fill_frequency=0.2,
    ),

    "metalcore": MetalVibe(
        name="Metalcore",
        description="Heavy breakdowns + melodic parts. Killswitch, As I Lay Dying, Parkway Drive.",
        tempo_range=(120, 170),
        scales=["natural_minor", "harmonic_minor", "minor_pentatonic"],
        tunings=["drop_c", "drop_b", "drop_d"],
        drum_patterns=["double_bass", "breakdown", "half_time", "blast_beat"],
        riff_styles=["palm_mute", "tremolo", "breakdown", "power_chords"],
        bass_styles=["root_lock", "octave_pulse"],
        progressions=["classic_metal", "breakdown", "melodeath_gallop"],
        structure=["riff", "verse", "riff", "verse", "breakdown",
                   "breakdown", "solo_section", "riff"],
        fill_frequency=0.3,
    ),
}


def get_vibe(name: str) -> MetalVibe:
    """Get a vibe by name. Returns random vibe if name is 'random'."""
    if name == "random":
        name = random.choice(list(VIBES.keys()))
    return VIBES.get(name, VIBES["thrash"])


def list_vibes() -> List[str]:
    """Return all available vibe names."""
    return list(VIBES.keys())
