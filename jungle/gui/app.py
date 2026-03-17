"""PROJECTJUNGLE — Live Jam Station.

A real-time metal backing track player with live controls.
Generate a jam, hit play, and shred on top of it.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os
import random
import threading

from jungle import __version__
from jungle.vibes.metal import VIBES, get_vibe, list_vibes
from jungle.generators.session import generate_session
from jungle.core.midi_export import export_midi
from jungle.core.theory import TUNINGS, SCALES, note_name
from jungle.core.rhythm import TICKS_PER_BAR

# Try to import the live engine — it's optional if no MIDI backend is installed
try:
    from jungle.core.playback import LiveEngine, list_midi_ports, auto_detect_output
    HAS_PLAYBACK = True
except Exception:
    HAS_PLAYBACK = True  # module exists, backends checked at runtime


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
    "green_dim":    "#0E6B0E",
    "orange":       "#C4841E",
    "blue":         "#1E7EC4",
    "border":       "#333333",
    "muted":        "#4A2020",
    "playing_bar":  "#2A4A2A",
}

FONT_TITLE = ("Consolas", 22, "bold")
FONT_HEADER = ("Consolas", 13, "bold")
FONT_BODY = ("Consolas", 11)
FONT_SMALL = ("Consolas", 9)
FONT_BUTTON = ("Consolas", 12, "bold")
FONT_VIBE = ("Consolas", 11, "bold")
FONT_VIBE_DESC = ("Consolas", 8)
FONT_BIG_BUTTON = ("Consolas", 16, "bold")
FONT_TRANSPORT = ("Consolas", 14, "bold")
FONT_POSITION = ("Consolas", 28, "bold")
FONT_TRACK_BTN = ("Consolas", 11, "bold")


class JungleApp:
    """Live Jam Station — main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"PROJECTJUNGLE v{__version__} — Live Jam Station")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(True, True)
        self.root.minsize(960, 750)
        self.root.geometry("1020x800")

        # State
        self.selected_vibe = tk.StringVar(value="thrash")
        self.tempo_var = tk.IntVar(value=0)  # 0 = auto
        self.bars_var = tk.IntVar(value=32)
        self.tuning_var = tk.StringVar(value="auto")
        self.scale_var = tk.StringVar(value="auto")
        self.seed_var = tk.StringVar(value="")
        self.loop_var = tk.BooleanVar(value=True)
        self.auto_regen_var = tk.BooleanVar(value=False)
        self.last_session = None
        self.last_filepath = None

        # Live engine
        self.engine = None
        self._is_playing = False
        self._engine_error = None

        # Track mute state for UI
        self._track_mute_buttons = {}

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Clean shutdown."""
        if self.engine:
            try:
                self.engine.stop()
                self.engine.close_output()
            except Exception:
                pass
        self.root.destroy()

    def _build_ui(self):
        """Construct the entire UI."""
        main = tk.Frame(self.root, bg=COLORS["bg"], padx=15, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        self._build_title_bar(main)

        body = tk.Frame(main, bg=COLORS["bg"])
        body.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Left panel — vibe selector
        left = tk.Frame(body, bg=COLORS["bg_panel"], width=300)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)
        self._build_vibe_panel(left)

        # Right panel — everything else
        right = tk.Frame(body, bg=COLORS["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_controls_panel(right)
        self._build_transport_panel(right)
        self._build_mixer_panel(right)
        self._build_position_panel(right)
        self._build_export_panel(right)

    def _build_title_bar(self, parent):
        bar = tk.Frame(parent, bg=COLORS["bg"])
        bar.pack(fill=tk.X)
        tk.Label(bar, text="PROJECTJUNGLE", font=FONT_TITLE,
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(side=tk.LEFT)
        tk.Label(bar, text="Live Jam Station", font=FONT_BODY,
                 bg=COLORS["bg"], fg=COLORS["text_dim"]
                 ).pack(side=tk.LEFT, padx=(15, 0), pady=(8, 0))
        tk.Label(bar, text=f"v{__version__}", font=FONT_SMALL,
                 bg=COLORS["bg"], fg=COLORS["text_dim"]
                 ).pack(side=tk.RIGHT, pady=(8, 0))

    # ------------------------------------------------------------------ #
    #  Vibe selector (left panel)
    # ------------------------------------------------------------------ #

    def _build_vibe_panel(self, parent):
        tk.Label(parent, text="SELECT VIBE", font=FONT_HEADER,
                 bg=COLORS["bg_panel"], fg=COLORS["text"], pady=10
                 ).pack(fill=tk.X)

        canvas = tk.Canvas(parent, bg=COLORS["bg_panel"],
                           highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(parent, orient=tk.VERTICAL,
                                 command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["bg_panel"])
        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        self._create_vibe_card(scroll_frame, "random",
                               "Random", "Surprise me", "?? BPM")
        for name, vibe in VIBES.items():
            tempo_str = f"{vibe.tempo_range[0]}-{vibe.tempo_range[1]} BPM"
            self._create_vibe_card(scroll_frame, name,
                                   vibe.name, vibe.description, tempo_str)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_vibe_card(self, parent, key, title, desc, tempo):
        card = tk.Frame(parent, bg=COLORS["bg_card"], cursor="hand2",
                        padx=10, pady=6, relief=tk.FLAT)
        card.pack(fill=tk.X, padx=5, pady=2)

        title_lbl = tk.Label(card, text=title, font=FONT_VIBE,
                             bg=COLORS["bg_card"], fg=COLORS["text"],
                             anchor="w")
        title_lbl.pack(fill=tk.X)
        desc_lbl = tk.Label(card, text=desc, font=FONT_VIBE_DESC,
                            bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                            anchor="w", wraplength=250)
        desc_lbl.pack(fill=tk.X)
        tempo_lbl = tk.Label(card, text=tempo, font=FONT_SMALL,
                             bg=COLORS["bg_card"], fg=COLORS["orange"],
                             anchor="w")
        tempo_lbl.pack(fill=tk.X)

        def on_click(event=None):
            self.selected_vibe.set(key)
            self._update_vibe_highlights()

        for w in [card, title_lbl, desc_lbl, tempo_lbl]:
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>",
                   lambda e, c=card: c.configure(bg=COLORS["bg_card_hover"]))
            w.bind("<Leave>",
                   lambda e, c=card, k=key: c.configure(
                       bg=COLORS["bg_active"] if self.selected_vibe.get() == k
                       else COLORS["bg_card"]))

        card._jungle_key = key
        card._jungle_children = [title_lbl, desc_lbl, tempo_lbl]
        if not hasattr(self, '_vibe_cards'):
            self._vibe_cards = []
        self._vibe_cards.append(card)

    def _update_vibe_highlights(self):
        selected = self.selected_vibe.get()
        for card in self._vibe_cards:
            bg = COLORS["bg_active"] if card._jungle_key == selected else COLORS["bg_card"]
            card.configure(bg=bg)
            for child in card._jungle_children:
                child.configure(bg=bg)

    # ------------------------------------------------------------------ #
    #  Settings panel
    # ------------------------------------------------------------------ #

    def _build_controls_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" SETTINGS ", font=FONT_HEADER,
                              bg=COLORS["bg_panel"], fg=COLORS["text"],
                              bd=1, relief=tk.GROOVE, padx=15, pady=8)
        frame.pack(fill=tk.X, pady=(0, 8))

        # Row 1: Tempo + Bars
        row1 = tk.Frame(frame, bg=COLORS["bg_panel"])
        row1.pack(fill=tk.X, pady=(0, 6))

        tk.Label(row1, text="TEMPO", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(side=tk.LEFT)
        self.tempo_label = tk.Label(row1, text="Auto", font=FONT_BODY,
                                    bg=COLORS["bg_panel"],
                                    fg=COLORS["orange"], width=6)
        self.tempo_label.pack(side=tk.LEFT, padx=(5, 0))
        self.tempo_scale = tk.Scale(
            row1, from_=0, to=260, orient=tk.HORIZONTAL,
            variable=self.tempo_var, bg=COLORS["bg_panel"],
            fg=COLORS["text"], troughcolor=COLORS["bg_card"],
            highlightthickness=0, showvalue=False, length=130,
            command=self._on_tempo_change)
        self.tempo_scale.pack(side=tk.LEFT, padx=(5, 15))

        tk.Label(row1, text="BARS", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(side=tk.LEFT)
        tk.Spinbox(row1, from_=4, to=256, increment=4,
                   textvariable=self.bars_var, width=5,
                   bg=COLORS["bg_card"], fg=COLORS["text"],
                   font=FONT_BODY, buttonbackground=COLORS["bg_card"],
                   insertbackground=COLORS["text"]).pack(side=tk.LEFT, padx=(5, 0))

        # Row 2: Tuning + Scale + Seed
        row2 = tk.Frame(frame, bg=COLORS["bg_panel"])
        row2.pack(fill=tk.X)

        tk.Label(row2, text="TUNING", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(side=tk.LEFT)
        ttk.Combobox(row2, textvariable=self.tuning_var,
                     values=["auto"] + list(TUNINGS.keys()), width=12,
                     state="readonly").pack(side=tk.LEFT, padx=(5, 15))

        tk.Label(row2, text="SCALE", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(side=tk.LEFT)
        ttk.Combobox(row2, textvariable=self.scale_var,
                     values=["auto"] + list(SCALES.keys()), width=16,
                     state="readonly").pack(side=tk.LEFT, padx=(5, 15))

        tk.Label(row2, text="SEED", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(side=tk.LEFT)
        tk.Entry(row2, textvariable=self.seed_var, width=8,
                 bg=COLORS["bg_card"], fg=COLORS["text"],
                 font=FONT_BODY, insertbackground=COLORS["text"]
                 ).pack(side=tk.LEFT, padx=(5, 0))

    def _on_tempo_change(self, val):
        val = int(val)
        if val == 0:
            self.tempo_label.configure(text="Auto")
        else:
            self.tempo_label.configure(text=f"{val}")

    # ------------------------------------------------------------------ #
    #  Transport panel — the heart of the live jam station
    # ------------------------------------------------------------------ #

    def _build_transport_panel(self, parent):
        frame = tk.Frame(parent, bg=COLORS["bg"], pady=5)
        frame.pack(fill=tk.X)

        # Top row: GENERATE + PLAY/STOP
        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill=tk.X)

        # Generate button
        self.generate_btn = tk.Button(
            btn_row, text="GENERATE", font=FONT_BIG_BUTTON,
            bg=COLORS["accent"], fg=COLORS["text_bright"],
            activebackground=COLORS["accent_hover"],
            activeforeground=COLORS["text_bright"],
            relief=tk.FLAT, padx=20, pady=10, cursor="hand2",
            command=self._on_generate)
        self.generate_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.generate_btn.bind("<Enter>",
            lambda e: self.generate_btn.configure(bg=COLORS["accent_hover"]))
        self.generate_btn.bind("<Leave>",
            lambda e: self.generate_btn.configure(bg=COLORS["accent"]))

        # Play button
        self.play_btn = tk.Button(
            btn_row, text="PLAY", font=FONT_BIG_BUTTON,
            bg=COLORS["green_dim"], fg=COLORS["text_bright"],
            activebackground=COLORS["green"],
            activeforeground=COLORS["text_bright"],
            relief=tk.FLAT, padx=20, pady=10, cursor="hand2",
            command=self._on_play_stop, state=tk.DISABLED)
        self.play_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Options row: Loop + Auto-regen
        opt_row = tk.Frame(frame, bg=COLORS["bg"])
        opt_row.pack(fill=tk.X, pady=(5, 0))

        tk.Checkbutton(opt_row, text="Loop", variable=self.loop_var,
                       bg=COLORS["bg"], fg=COLORS["text"],
                       selectcolor=COLORS["bg_card"],
                       activebackground=COLORS["bg"],
                       activeforeground=COLORS["text"],
                       font=FONT_SMALL,
                       command=self._on_loop_toggle).pack(side=tk.LEFT)

        tk.Checkbutton(opt_row, text="New jam each loop",
                       variable=self.auto_regen_var,
                       bg=COLORS["bg"], fg=COLORS["text"],
                       selectcolor=COLORS["bg_card"],
                       activebackground=COLORS["bg"],
                       activeforeground=COLORS["text"],
                       font=FONT_SMALL).pack(side=tk.LEFT, padx=(15, 0))

        self.status_label = tk.Label(
            opt_row, text="Pick a vibe and generate",
            font=FONT_SMALL, bg=COLORS["bg"], fg=COLORS["text_dim"])
        self.status_label.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------ #
    #  Mixer panel — track mute/volume
    # ------------------------------------------------------------------ #

    def _build_mixer_panel(self, parent):
        self.mixer_frame = tk.LabelFrame(
            parent, text=" MIXER ", font=FONT_HEADER,
            bg=COLORS["bg_panel"], fg=COLORS["text"],
            bd=1, relief=tk.GROOVE, padx=15, pady=8)
        self.mixer_frame.pack(fill=tk.X, pady=(8, 0))

        self.mixer_inner = tk.Frame(self.mixer_frame, bg=COLORS["bg_panel"])
        self.mixer_inner.pack(fill=tk.X)

        # Placeholder — populated after generation
        self.mixer_placeholder = tk.Label(
            self.mixer_inner,
            text="Generate a jam to see track controls",
            font=FONT_SMALL, bg=COLORS["bg_panel"], fg=COLORS["text_dim"])
        self.mixer_placeholder.pack(pady=5)

        # Live tempo slider
        tempo_row = tk.Frame(self.mixer_frame, bg=COLORS["bg_panel"])
        tempo_row.pack(fill=tk.X, pady=(8, 0))

        tk.Label(tempo_row, text="LIVE TEMPO", font=FONT_SMALL,
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"]).pack(side=tk.LEFT)
        self.live_tempo_label = tk.Label(
            tempo_row, text="--", font=FONT_BODY,
            bg=COLORS["bg_panel"], fg=COLORS["orange"], width=6)
        self.live_tempo_label.pack(side=tk.LEFT, padx=(5, 0))
        self.live_tempo_scale = tk.Scale(
            tempo_row, from_=40, to=300, orient=tk.HORIZONTAL,
            bg=COLORS["bg_panel"], fg=COLORS["text"],
            troughcolor=COLORS["bg_card"],
            highlightthickness=0, showvalue=False, length=200,
            command=self._on_live_tempo_change)
        self.live_tempo_scale.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

    def _populate_mixer(self):
        """Rebuild mixer controls based on current session tracks."""
        # Clear existing
        for w in self.mixer_inner.winfo_children():
            w.destroy()
        self._track_mute_buttons = {}

        if not self.last_session:
            return

        track_info = {
            "drums": {"label": "DRUMS", "color": COLORS["orange"],
                      "hint": "Ch 10 — FPC / Superior Drummer"},
            "bass": {"label": "BASS", "color": COLORS["blue"],
                     "hint": "Ch 2 — MODO Bass / Trilian"},
            "rhythm_guitar": {"label": "GUITAR", "color": COLORS["accent"],
                              "hint": "Ch 3 — Neural DSP / AmpliTube"},
        }

        for track_name in self.last_session.tracks:
            info = track_info.get(track_name, {
                "label": track_name.upper(), "color": COLORS["text"],
                "hint": ""})

            row = tk.Frame(self.mixer_inner, bg=COLORS["bg_panel"])
            row.pack(fill=tk.X, pady=2)

            # Mute button
            btn = tk.Button(
                row, text=info["label"], font=FONT_TRACK_BTN,
                bg=info["color"], fg=COLORS["text_bright"],
                activebackground=info["color"],
                relief=tk.FLAT, width=10, pady=4, cursor="hand2")
            btn.pack(side=tk.LEFT, padx=(0, 10))
            btn._track_name = track_name
            btn._active_color = info["color"]
            btn._is_muted = False
            btn.configure(command=lambda b=btn: self._toggle_track_mute(b))
            self._track_mute_buttons[track_name] = btn

            # Volume slider
            vol_scale = tk.Scale(
                row, from_=0, to=100, orient=tk.HORIZONTAL,
                bg=COLORS["bg_panel"], fg=COLORS["text"],
                troughcolor=COLORS["bg_card"],
                highlightthickness=0, showvalue=False, length=150)
            vol_scale.set(100)
            vol_scale.pack(side=tk.LEFT, padx=(0, 10))
            vol_scale._track_name = track_name
            vol_scale.configure(
                command=lambda val, tn=track_name: self._on_track_volume(tn, val))

            # Hint
            tk.Label(row, text=info["hint"], font=FONT_SMALL,
                     bg=COLORS["bg_panel"], fg=COLORS["text_dim"]
                     ).pack(side=tk.LEFT)

    def _toggle_track_mute(self, btn):
        """Toggle mute for a track."""
        btn._is_muted = not btn._is_muted
        if btn._is_muted:
            btn.configure(bg=COLORS["muted"], fg=COLORS["text_dim"],
                          text=f"{btn.cget('text').split(' ')[0]} [MUTED]"
                          if "[MUTED]" not in btn.cget("text")
                          else btn.cget("text"))
            # Fix text
            base = btn._track_name.replace("rhythm_", "").upper()
            btn.configure(text=f"{base} [MUTE]")
            if self.engine:
                self.engine.mute_track(btn._track_name)
        else:
            base = btn._track_name.replace("rhythm_", "").upper()
            btn.configure(bg=btn._active_color, fg=COLORS["text_bright"],
                          text=base)
            if self.engine:
                self.engine.unmute_track(btn._track_name)

    def _on_track_volume(self, track_name, val):
        """Adjust track volume live."""
        if self.engine:
            self.engine.set_track_volume(track_name, int(val) / 100.0)

    def _on_live_tempo_change(self, val):
        """Change tempo in real-time during playback."""
        bpm = int(val)
        self.live_tempo_label.configure(text=f"{bpm}")
        if self.engine:
            self.engine.set_tempo(bpm)

    def _on_loop_toggle(self):
        if self.engine:
            self.engine.set_looping(self.loop_var.get())

    # ------------------------------------------------------------------ #
    #  Position display — shows current bar
    # ------------------------------------------------------------------ #

    def _build_position_panel(self, parent):
        frame = tk.Frame(parent, bg=COLORS["bg_card"], pady=8)
        frame.pack(fill=tk.X, pady=(8, 0))

        # Bar counter
        left = tk.Frame(frame, bg=COLORS["bg_card"])
        left.pack(side=tk.LEFT, padx=15)

        tk.Label(left, text="BAR", font=FONT_SMALL,
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack()
        self.bar_label = tk.Label(left, text="-- / --", font=FONT_POSITION,
                                  bg=COLORS["bg_card"], fg=COLORS["green"])
        self.bar_label.pack()

        # Session info
        right = tk.Frame(frame, bg=COLORS["bg_card"])
        right.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15)

        self.session_info_label = tk.Label(
            right, text="No session loaded", font=FONT_BODY,
            bg=COLORS["bg_card"], fg=COLORS["text_dim"],
            anchor="w", justify=tk.LEFT)
        self.session_info_label.pack(fill=tk.X)

        # Beat indicator (4 dots)
        beat_frame = tk.Frame(frame, bg=COLORS["bg_card"])
        beat_frame.pack(side=tk.RIGHT, padx=15)
        self.beat_dots = []
        for i in range(4):
            dot = tk.Label(beat_frame, text="  ", font=FONT_BODY,
                           bg=COLORS["border"], width=3, height=1)
            dot.pack(side=tk.LEFT, padx=2)
            self.beat_dots.append(dot)

    def _update_bar_display(self, bar, total_bars):
        """Called from engine thread — schedule on main thread."""
        self.root.after(0, lambda: self._set_bar_display(bar, total_bars))

    def _set_bar_display(self, bar, total_bars):
        self.bar_label.configure(text=f"{bar + 1:02d} / {total_bars:02d}")

    def _update_beat_display(self, beat):
        self.root.after(0, lambda: self._set_beat_display(beat))

    def _set_beat_display(self, beat):
        for i, dot in enumerate(self.beat_dots):
            if i == beat:
                dot.configure(bg=COLORS["green"])
            else:
                dot.configure(bg=COLORS["border"])

    # ------------------------------------------------------------------ #
    #  Export panel
    # ------------------------------------------------------------------ #

    def _build_export_panel(self, parent):
        frame = tk.Frame(parent, bg=COLORS["bg"])
        frame.pack(fill=tk.X, pady=(8, 0))

        self.export_btn = tk.Button(
            frame, text="EXPORT MIDI", font=FONT_BUTTON,
            bg=COLORS["bg_card"], fg=COLORS["text"],
            activebackground=COLORS["bg_card_hover"],
            relief=tk.FLAT, padx=15, pady=6, cursor="hand2",
            command=self._on_export, state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.quick_export_btn = tk.Button(
            frame, text="QUICK SAVE", font=FONT_BUTTON,
            bg=COLORS["bg_card"], fg=COLORS["text"],
            activebackground=COLORS["bg_card_hover"],
            relief=tk.FLAT, padx=15, pady=6, cursor="hand2",
            command=self._on_quick_export, state=tk.DISABLED)
        self.quick_export_btn.pack(side=tk.LEFT)

        self.midi_status = tk.Label(
            frame, text="", font=FONT_SMALL,
            bg=COLORS["bg"], fg=COLORS["text_dim"])
        self.midi_status.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #

    def _on_generate(self):
        """Generate a new jam session."""
        # Stop current playback
        if self._is_playing and self.engine:
            self.engine.stop()
            self._is_playing = False
            self.play_btn.configure(text="PLAY", bg=COLORS["green_dim"])

        self.generate_btn.configure(state=tk.DISABLED, text="GENERATING...")
        self.status_label.configure(text="Generating...", fg=COLORS["orange"])
        self.root.update()
        thread = threading.Thread(target=self._generate_worker, daemon=True)
        thread.start()

    def _generate_worker(self):
        try:
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
                vibe_name=vibe, bars=bars, tempo=tempo,
                tuning=tuning, scale=scale)
            self.last_session = session
            self.root.after(0, self._on_generate_complete)
        except Exception as e:
            self.root.after(0, lambda: self._on_generate_error(str(e)))

    def _on_generate_complete(self):
        session = self.last_session
        self.generate_btn.configure(state=tk.NORMAL, text="GENERATE")
        self.play_btn.configure(state=tk.NORMAL)
        self.export_btn.configure(state=tk.NORMAL)
        self.quick_export_btn.configure(state=tk.NORMAL)

        total_events = sum(len(v) for v in session.tracks.values())
        mins = int(session.duration_seconds() // 60)
        secs = int(session.duration_seconds() % 60)

        self.status_label.configure(
            text=f"Ready! {session.bars} bars | {total_events} events",
            fg=COLORS["green"])

        # Update session info
        self.session_info_label.configure(
            text=(f"{session.vibe_name}  |  {session.tempo} BPM  |  "
                  f"{note_name(session.key_root)} {session.scale}  |  "
                  f"{session.tuning}  |  ~{mins}:{secs:02d}"),
            fg=COLORS["text"])

        # Set live tempo slider
        self.live_tempo_scale.set(session.tempo)
        self.live_tempo_label.configure(text=f"{session.tempo}")

        # Update bar display
        self.bar_label.configure(text=f"01 / {session.bars:02d}")

        # Populate mixer
        self._populate_mixer()

        # Load into engine
        self._init_engine()
        if self.engine:
            self.engine.load_session(session)

    def _on_generate_error(self, error_msg):
        self.generate_btn.configure(state=tk.NORMAL, text="GENERATE")
        self.status_label.configure(text=f"Error: {error_msg}",
                                    fg=COLORS["accent"])

    def _init_engine(self):
        """Initialize the live engine (lazy — only when needed)."""
        if self.engine:
            return

        from jungle.core.playback import LiveEngine
        self.engine = LiveEngine()
        self.engine.on_bar_change = self._update_bar_display
        self.engine.set_looping(self.loop_var.get())
        self.engine.on_loop_restart = self._on_loop_restart
        self.engine.on_playback_stop = lambda: self.root.after(
            0, self._on_playback_stopped)

    def _on_play_stop(self):
        """Toggle play/stop."""
        if not self.last_session:
            return

        if self._is_playing:
            # STOP
            if self.engine:
                self.engine.stop()
            self._is_playing = False
            self.play_btn.configure(text="PLAY", bg=COLORS["green_dim"])
            self.status_label.configure(text="Stopped", fg=COLORS["text_dim"])
        else:
            # PLAY
            if not self.engine:
                self._init_engine()
            try:
                self.engine.open_output()
                self.engine.set_looping(self.loop_var.get())
                self.engine.play()
                self._is_playing = True
                self.play_btn.configure(text="STOP", bg=COLORS["accent"])
                self.status_label.configure(text="Playing...", fg=COLORS["green"])
            except Exception as e:
                self._show_midi_setup_help(str(e))

    def _on_playback_stopped(self):
        """Called when playback stops (from engine thread)."""
        self._is_playing = False
        self.play_btn.configure(text="PLAY", bg=COLORS["green_dim"])
        self.status_label.configure(text="Stopped", fg=COLORS["text_dim"])

    def _on_loop_restart(self):
        """Called when the loop restarts."""
        if self.auto_regen_var.get():
            # Generate a new jam for the next loop
            session = generate_session(
                vibe_name=self.selected_vibe.get(),
                bars=self.bars_var.get())
            self.last_session = session
            if self.engine:
                self.engine.load_session(session)
            self.root.after(0, self._on_generate_complete)

    def _show_midi_setup_help(self, error):
        """Show helpful error when MIDI output isn't available."""
        self.status_label.configure(
            text="No MIDI output — see below", fg=COLORS["accent"])
        self.midi_status.configure(
            text=(f"MIDI Error: {error}\n"
                  "Install: pip install pygame"),
            fg=COLORS["accent"])

    # ------------------------------------------------------------------ #
    #  Export
    # ------------------------------------------------------------------ #

    def _on_export(self):
        if not self.last_session:
            return
        vibe_safe = self.last_session.vibe_name.lower().replace(" ", "_")
        default_name = f"jungle_{vibe_safe}_{self.last_session.tempo}bpm.mid"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".mid",
            filetypes=[("MIDI files", "*.mid"), ("All files", "*.*")],
            initialfile=default_name,
            title="Export MIDI")
        if filepath:
            export_midi(self.last_session, filepath)
            self.midi_status.configure(
                text=f"Exported: {os.path.basename(filepath)}",
                fg=COLORS["green"])

    def _on_quick_export(self):
        if not self.last_session:
            return
        desktop = os.path.expanduser("~/Desktop")
        if not os.path.isdir(desktop):
            desktop = os.getcwd()
        vibe_safe = self.last_session.vibe_name.lower().replace(" ", "_")
        filename = f"jungle_{vibe_safe}_{self.last_session.tempo}bpm_{random.randint(1000,9999)}.mid"
        filepath = os.path.join(desktop, filename)
        export_midi(self.last_session, filepath)
        self.midi_status.configure(text=f"Saved: {filepath}", fg=COLORS["green"])

    # ------------------------------------------------------------------ #
    #  Run
    # ------------------------------------------------------------------ #

    def run(self):
        self._update_vibe_highlights()
        self.root.mainloop()


def launch():
    """Entry point for the GUI application."""
    app = JungleApp()
    app.run()


if __name__ == "__main__":
    launch()
