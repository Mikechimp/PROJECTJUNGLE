"""PROJECTJUNGLE — Desktop GUI Application.

A polished standalone app for generating metal backing tracks.
Uses tkinter (included with Python) so there are zero dependencies.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random
import threading

from jungle import __version__
from jungle.vibes.metal import VIBES, get_vibe, list_vibes
from jungle.generators.session import generate_session
from jungle.core.midi_export import export_midi
from jungle.core.theory import TUNINGS, SCALES, note_name


# --------------------------------------------------------------------------- #
#  Color theme — dark metal aesthetic
# --------------------------------------------------------------------------- #

COLORS = {
    "bg":           "#0D0D0D",
    "bg_panel":     "#1A1A1A",
    "bg_card":      "#242424",
    "bg_card_hover":"#2E2E2E",
    "bg_active":    "#3A0A0A",
    "accent":       "#C41E1E",
    "accent_hover": "#E02020",
    "accent_dim":   "#8B1515",
    "text":         "#E8E8E8",
    "text_dim":     "#888888",
    "text_bright":  "#FFFFFF",
    "green":        "#1EC41E",
    "orange":       "#C4841E",
    "border":       "#333333",
}

FONT_TITLE = ("Consolas", 22, "bold")
FONT_HEADER = ("Consolas", 13, "bold")
FONT_BODY = ("Consolas", 11)
FONT_SMALL = ("Consolas", 9)
FONT_BUTTON = ("Consolas", 12, "bold")
FONT_VIBE = ("Consolas", 11, "bold")
FONT_VIBE_DESC = ("Consolas", 8)
FONT_BIG_BUTTON = ("Consolas", 16, "bold")


class JungleApp:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"PROJECTJUNGLE v{__version__}")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(True, True)
        self.root.minsize(900, 700)

        # Try to set a reasonable starting size
        self.root.geometry("960x780")

        # State
        self.selected_vibe = tk.StringVar(value="thrash")
        self.tempo_var = tk.IntVar(value=0)  # 0 = auto
        self.bars_var = tk.IntVar(value=32)
        self.tuning_var = tk.StringVar(value="auto")
        self.scale_var = tk.StringVar(value="auto")
        self.seed_var = tk.StringVar(value="")
        self.include_drums = tk.BooleanVar(value=True)
        self.include_bass = tk.BooleanVar(value=True)
        self.include_guitar = tk.BooleanVar(value=True)
        self.last_session = None
        self.last_filepath = None

        self._build_ui()

    def _build_ui(self):
        """Construct the entire UI."""
        # Main container with padding
        main = tk.Frame(self.root, bg=COLORS["bg"], padx=15, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Title bar
        self._build_title_bar(main)

        # Body: left (vibes) + right (controls + output)
        body = tk.Frame(main, bg=COLORS["bg"])
        body.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Left panel — vibe selector
        left = tk.Frame(body, bg=COLORS["bg_panel"], width=340)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)
        self._build_vibe_panel(left)

        # Right panel — controls + output
        right = tk.Frame(body, bg=COLORS["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_controls_panel(right)
        self._build_generate_section(right)
        self._build_output_panel(right)

    def _build_title_bar(self, parent):
        """Top title bar."""
        bar = tk.Frame(parent, bg=COLORS["bg"])
        bar.pack(fill=tk.X)

        tk.Label(
            bar, text="PROJECTJUNGLE", font=FONT_TITLE,
            bg=COLORS["bg"], fg=COLORS["accent"]
        ).pack(side=tk.LEFT)

        tk.Label(
            bar, text="AI Metal Jam Buddy", font=FONT_BODY,
            bg=COLORS["bg"], fg=COLORS["text_dim"]
        ).pack(side=tk.LEFT, padx=(15, 0), pady=(8, 0))

        tk.Label(
            bar, text=f"v{__version__}", font=FONT_SMALL,
            bg=COLORS["bg"], fg=COLORS["text_dim"]
        ).pack(side=tk.RIGHT, pady=(8, 0))

    # ------------------------------------------------------------------ #
    #  Vibe selector panel
    # ------------------------------------------------------------------ #

    def _build_vibe_panel(self, parent):
        """Left panel with metal vibe buttons."""
        tk.Label(
            parent, text="SELECT VIBE", font=FONT_HEADER,
            bg=COLORS["bg_panel"], fg=COLORS["text"], pady=10
        ).pack(fill=tk.X)

        # Scrollable frame for vibes
        canvas = tk.Canvas(parent, bg=COLORS["bg_panel"],
                           highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(parent, orient=tk.VERTICAL,
                                 command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["bg_panel"])

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Random vibe option
        self._create_vibe_card(scroll_frame, "random",
                               "Random", "Surprise me — pick any vibe",
                               "?? BPM")

        # All vibes
        for name, vibe in VIBES.items():
            tempo_str = f"{vibe.tempo_range[0]}-{vibe.tempo_range[1]} BPM"
            self._create_vibe_card(scroll_frame, name,
                                   vibe.name, vibe.description, tempo_str)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_vibe_card(self, parent, key, title, desc, tempo):
        """Create a clickable vibe card."""
        card = tk.Frame(parent, bg=COLORS["bg_card"], cursor="hand2",
                        padx=10, pady=8, relief=tk.FLAT)
        card.pack(fill=tk.X, padx=5, pady=3)

        title_lbl = tk.Label(card, text=title, font=FONT_VIBE,
                             bg=COLORS["bg_card"], fg=COLORS["text"],
                             anchor="w")
        title_lbl.pack(fill=tk.X)

        desc_lbl = tk.Label(card, text=desc, font=FONT_VIBE_DESC,
                            bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                            anchor="w", wraplength=280)
        desc_lbl.pack(fill=tk.X)

        tempo_lbl = tk.Label(card, text=tempo, font=FONT_SMALL,
                             bg=COLORS["bg_card"], fg=COLORS["orange"],
                             anchor="w")
        tempo_lbl.pack(fill=tk.X)

        # Click handler
        def on_click(event=None):
            self.selected_vibe.set(key)
            self._update_vibe_highlights()

        for widget in [card, title_lbl, desc_lbl, tempo_lbl]:
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>",
                        lambda e, c=card: c.configure(bg=COLORS["bg_card_hover"]))
            widget.bind("<Leave>",
                        lambda e, c=card, k=key: c.configure(
                            bg=COLORS["bg_active"] if self.selected_vibe.get() == k
                            else COLORS["bg_card"]))

        # Store reference for highlighting
        card._jungle_key = key
        card._jungle_children = [title_lbl, desc_lbl, tempo_lbl]

        if not hasattr(self, '_vibe_cards'):
            self._vibe_cards = []
        self._vibe_cards.append(card)

    def _update_vibe_highlights(self):
        """Update which vibe card is highlighted."""
        selected = self.selected_vibe.get()
        for card in self._vibe_cards:
            if card._jungle_key == selected:
                bg = COLORS["bg_active"]
            else:
                bg = COLORS["bg_card"]
            card.configure(bg=bg)
            for child in card._jungle_children:
                child.configure(bg=bg)

    # ------------------------------------------------------------------ #
    #  Controls panel
    # ------------------------------------------------------------------ #

    def _build_controls_panel(self, parent):
        """Right panel controls: tempo, bars, tuning, etc."""
        frame = tk.LabelFrame(
            parent, text=" SETTINGS ", font=FONT_HEADER,
            bg=COLORS["bg_panel"], fg=COLORS["text"],
            bd=1, relief=tk.GROOVE, padx=15, pady=10
        )
        frame.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Tempo + Bars
        row1 = tk.Frame(frame, bg=COLORS["bg_panel"])
        row1.pack(fill=tk.X, pady=(0, 8))

        # Tempo
        tk.Label(row1, text="TEMPO", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side=tk.LEFT)
        self.tempo_label = tk.Label(row1, text="Auto", font=FONT_BODY,
                                    bg=COLORS["bg_panel"],
                                    fg=COLORS["orange"], width=6)
        self.tempo_label.pack(side=tk.LEFT, padx=(5, 0))
        self.tempo_scale = tk.Scale(
            row1, from_=0, to=260, orient=tk.HORIZONTAL,
            variable=self.tempo_var, bg=COLORS["bg_panel"],
            fg=COLORS["text"], troughcolor=COLORS["bg_card"],
            highlightthickness=0, showvalue=False, length=150,
            command=self._on_tempo_change
        )
        self.tempo_scale.pack(side=tk.LEFT, padx=(5, 20))

        # Bars
        tk.Label(row1, text="BARS", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side=tk.LEFT)
        bars_spin = tk.Spinbox(
            row1, from_=4, to=256, increment=4,
            textvariable=self.bars_var, width=5,
            bg=COLORS["bg_card"], fg=COLORS["text"],
            font=FONT_BODY, buttonbackground=COLORS["bg_card"],
            insertbackground=COLORS["text"]
        )
        bars_spin.pack(side=tk.LEFT, padx=(5, 0))

        # Row 2: Tuning + Scale
        row2 = tk.Frame(frame, bg=COLORS["bg_panel"])
        row2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row2, text="TUNING", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side=tk.LEFT)
        tuning_options = ["auto"] + list(TUNINGS.keys())
        tuning_menu = ttk.Combobox(row2, textvariable=self.tuning_var,
                                   values=tuning_options, width=12,
                                   state="readonly")
        tuning_menu.pack(side=tk.LEFT, padx=(5, 20))

        tk.Label(row2, text="SCALE", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side=tk.LEFT)
        scale_options = ["auto"] + list(SCALES.keys())
        scale_menu = ttk.Combobox(row2, textvariable=self.scale_var,
                                  values=scale_options, width=16,
                                  state="readonly")
        scale_menu.pack(side=tk.LEFT, padx=(5, 0))

        # Row 3: Track toggles + Seed
        row3 = tk.Frame(frame, bg=COLORS["bg_panel"])
        row3.pack(fill=tk.X)

        tk.Label(row3, text="TRACKS", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side=tk.LEFT)
        for text, var in [("Drums", self.include_drums),
                          ("Bass", self.include_bass),
                          ("Guitar", self.include_guitar)]:
            cb = tk.Checkbutton(row3, text=text, variable=var,
                                bg=COLORS["bg_panel"], fg=COLORS["text"],
                                selectcolor=COLORS["bg_card"],
                                activebackground=COLORS["bg_panel"],
                                activeforeground=COLORS["text"],
                                font=FONT_SMALL)
            cb.pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(row3, text="SEED", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(
            side=tk.LEFT, padx=(20, 0))
        seed_entry = tk.Entry(row3, textvariable=self.seed_var, width=8,
                              bg=COLORS["bg_card"], fg=COLORS["text"],
                              font=FONT_BODY, insertbackground=COLORS["text"])
        seed_entry.pack(side=tk.LEFT, padx=(5, 0))

    def _on_tempo_change(self, val):
        val = int(val)
        if val == 0:
            self.tempo_label.configure(text="Auto")
        else:
            self.tempo_label.configure(text=f"{val}")

    # ------------------------------------------------------------------ #
    #  Generate section
    # ------------------------------------------------------------------ #

    def _build_generate_section(self, parent):
        """Big generate button + status."""
        frame = tk.Frame(parent, bg=COLORS["bg"], pady=5)
        frame.pack(fill=tk.X)

        self.generate_btn = tk.Button(
            frame, text="GENERATE JAM", font=FONT_BIG_BUTTON,
            bg=COLORS["accent"], fg=COLORS["text_bright"],
            activebackground=COLORS["accent_hover"],
            activeforeground=COLORS["text_bright"],
            relief=tk.FLAT, padx=30, pady=12, cursor="hand2",
            command=self._on_generate
        )
        self.generate_btn.pack(fill=tk.X)

        # Hover effect
        self.generate_btn.bind("<Enter>",
            lambda e: self.generate_btn.configure(bg=COLORS["accent_hover"]))
        self.generate_btn.bind("<Leave>",
            lambda e: self.generate_btn.configure(bg=COLORS["accent"]))

        self.status_label = tk.Label(
            frame, text="Select a vibe and hit generate",
            font=FONT_SMALL, bg=COLORS["bg"], fg=COLORS["text_dim"]
        )
        self.status_label.pack(pady=(5, 0))

    # ------------------------------------------------------------------ #
    #  Output / session info panel
    # ------------------------------------------------------------------ #

    def _build_output_panel(self, parent):
        """Session info display + export buttons."""
        self.output_frame = tk.LabelFrame(
            parent, text=" SESSION INFO ", font=FONT_HEADER,
            bg=COLORS["bg_panel"], fg=COLORS["text"],
            bd=1, relief=tk.GROOVE, padx=15, pady=10
        )
        self.output_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.info_text = tk.Text(
            self.output_frame, bg=COLORS["bg_card"], fg=COLORS["text"],
            font=FONT_BODY, height=8, wrap=tk.WORD, bd=0,
            insertbackground=COLORS["text"], state=tk.DISABLED,
            padx=10, pady=10
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Export buttons row
        btn_row = tk.Frame(self.output_frame, bg=COLORS["bg_panel"])
        btn_row.pack(fill=tk.X, pady=(10, 0))

        self.export_btn = tk.Button(
            btn_row, text="EXPORT MIDI", font=FONT_BUTTON,
            bg=COLORS["green"], fg=COLORS["bg"],
            activebackground="#25E025",
            relief=tk.FLAT, padx=20, pady=8, cursor="hand2",
            command=self._on_export, state=tk.DISABLED
        )
        self.export_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.quick_export_btn = tk.Button(
            btn_row, text="QUICK SAVE", font=FONT_BUTTON,
            bg=COLORS["bg_card"], fg=COLORS["text"],
            activebackground=COLORS["bg_card_hover"],
            relief=tk.FLAT, padx=20, pady=8, cursor="hand2",
            command=self._on_quick_export, state=tk.DISABLED
        )
        self.quick_export_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.regenerate_btn = tk.Button(
            btn_row, text="REGENERATE", font=FONT_BUTTON,
            bg=COLORS["bg_card"], fg=COLORS["text"],
            activebackground=COLORS["bg_card_hover"],
            relief=tk.FLAT, padx=20, pady=8, cursor="hand2",
            command=self._on_generate, state=tk.DISABLED
        )
        self.regenerate_btn.pack(side=tk.LEFT)

    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #

    def _on_generate(self):
        """Generate a new jam session."""
        self.generate_btn.configure(state=tk.DISABLED, text="GENERATING...")
        self.status_label.configure(text="Generating your jam...",
                                    fg=COLORS["orange"])
        self.root.update()

        # Run generation in a thread to keep UI responsive
        thread = threading.Thread(target=self._generate_worker, daemon=True)
        thread.start()

    def _generate_worker(self):
        """Worker thread for generation."""
        try:
            # Parse settings
            vibe = self.selected_vibe.get()
            tempo = self.tempo_var.get() if self.tempo_var.get() > 0 else None
            bars = self.bars_var.get()
            tuning = self.tuning_var.get()
            if tuning == "auto":
                tuning = None
            scale = self.scale_var.get()
            if scale == "auto":
                scale = None

            seed_str = self.seed_var.get().strip()
            if seed_str:
                random.seed(int(seed_str))

            session = generate_session(
                vibe_name=vibe,
                bars=bars,
                tempo=tempo,
                tuning=tuning,
                scale=scale,
            )

            # Remove tracks if unchecked
            if not self.include_drums.get() and "drums" in session.tracks:
                del session.tracks["drums"]
            if not self.include_bass.get() and "bass" in session.tracks:
                del session.tracks["bass"]
            if not self.include_guitar.get() and "rhythm_guitar" in session.tracks:
                del session.tracks["rhythm_guitar"]

            self.last_session = session
            self.root.after(0, self._on_generate_complete)

        except Exception as e:
            self.root.after(0, lambda: self._on_generate_error(str(e)))

    def _on_generate_complete(self):
        """Called on main thread when generation finishes."""
        session = self.last_session
        self.generate_btn.configure(state=tk.NORMAL, text="GENERATE JAM")
        self.export_btn.configure(state=tk.NORMAL)
        self.quick_export_btn.configure(state=tk.NORMAL)
        self.regenerate_btn.configure(state=tk.NORMAL)

        total_events = sum(len(v) for v in session.tracks.values())
        self.status_label.configure(
            text=f"Generated! {session.bars} bars | {total_events} events | "
                 f"{session.tempo} BPM",
            fg=COLORS["green"]
        )

        # Update info display
        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)

        mins = int(session.duration_seconds() // 60)
        secs = int(session.duration_seconds() % 60)

        info = (
            f"  Vibe:     {session.vibe_name}\n"
            f"  Tempo:    {session.tempo} BPM\n"
            f"  Key Root: MIDI {session.key_root} ({note_name(session.key_root)})\n"
            f"  Scale:    {session.scale}\n"
            f"  Tuning:   {session.tuning}\n"
            f"  Length:   {session.bars} bars (~{mins}:{secs:02d})\n"
            f"  Tracks:   {', '.join(session.tracks.keys())}\n"
            f"  Events:   {total_events}\n"
            f"\n"
            f"  HOW TO USE IN FL STUDIO:\n"
            f"  1. Click 'EXPORT MIDI' below\n"
            f"  2. Drag the .mid file into FL Studio's Playlist\n"
            f"  3. Assign tracks to your instruments:\n"
            f"     - drums  -> FPC / Superior Drummer / EZDrummer\n"
            f"     - bass   -> MODO Bass / Trilian / Ample Bass\n"
            f"     - guitar -> Neural DSP / Helix / AmpliTube\n"
            f"  4. Hit play and shred!\n"
        )
        self.info_text.insert("1.0", info)
        self.info_text.configure(state=tk.DISABLED)

    def _on_generate_error(self, error_msg):
        """Called if generation fails."""
        self.generate_btn.configure(state=tk.NORMAL, text="GENERATE JAM")
        self.status_label.configure(text=f"Error: {error_msg}",
                                    fg=COLORS["accent"])

    def _on_export(self):
        """Export to MIDI with file dialog."""
        if not self.last_session:
            return

        vibe_safe = self.last_session.vibe_name.lower().replace(" ", "_")
        default_name = f"jungle_{vibe_safe}_{self.last_session.tempo}bpm.mid"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".mid",
            filetypes=[("MIDI files", "*.mid"), ("All files", "*.*")],
            initialfile=default_name,
            title="Export MIDI — PROJECTJUNGLE"
        )
        if filepath:
            export_midi(self.last_session, filepath)
            self.last_filepath = filepath
            self.status_label.configure(
                text=f"Exported: {os.path.basename(filepath)}",
                fg=COLORS["green"]
            )

    def _on_quick_export(self):
        """Quick export to Desktop or current directory."""
        if not self.last_session:
            return

        # Try Desktop first, fall back to current directory
        desktop = os.path.expanduser("~/Desktop")
        if not os.path.isdir(desktop):
            desktop = os.getcwd()

        vibe_safe = self.last_session.vibe_name.lower().replace(" ", "_")
        seed_part = self.seed_var.get().strip()
        if seed_part:
            filename = f"jungle_{vibe_safe}_{self.last_session.tempo}bpm_s{seed_part}.mid"
        else:
            filename = f"jungle_{vibe_safe}_{self.last_session.tempo}bpm_{random.randint(1000,9999)}.mid"

        filepath = os.path.join(desktop, filename)
        export_midi(self.last_session, filepath)
        self.last_filepath = filepath
        self.status_label.configure(
            text=f"Saved to: {filepath}",
            fg=COLORS["green"]
        )

    # ------------------------------------------------------------------ #
    #  Run
    # ------------------------------------------------------------------ #

    def run(self):
        """Start the application."""
        # Select default vibe
        self._update_vibe_highlights()
        self.root.mainloop()


def launch():
    """Entry point for the GUI application."""
    app = JungleApp()
    app.run()


if __name__ == "__main__":
    launch()
