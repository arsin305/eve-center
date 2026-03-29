#!/usr/bin/env python3
"""
EVE Online Window Centering Tool
Centers the EVE client on your ultrawide monitor when running in
fixed window mode at a different resolution (e.g. for streaming).

Requirements:
    sudo dnf install xdotool xrandr python3-tkinter
"""

import tkinter as tk
from tkinter import font as tkfont
import subprocess
import re
import sys


# ── Palette ────────────────────────────────────────────────────────────────────
BG         = "#090d14"
BG2        = "#0e1520"
PANEL      = "#111c2b"
BORDER     = "#1a3050"
ACCENT     = "#00c8ff"
ACCENT2    = "#0076a3"
GOLD       = "#c8a84b"
TEXT       = "#c8dce8"
TEXT_DIM   = "#4a6a82"
SUCCESS    = "#00e5a0"
ERROR      = "#ff4060"
BTN_BG     = "#0a2a40"
BTN_HOVER  = "#0d3a58"


# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd: list[str]) -> tuple[str, str, int]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def check_dependency(cmd: str) -> bool:
    _, _, code = run(["which", cmd])
    return code == 0


def get_displays() -> list[dict]:
    """Return list of {name, width, height, x, y, primary} from xrandr."""
    displays = []
    out, _, _ = run(["xrandr", "--current"])
    for line in out.splitlines():
        # Match: NAME connected [primary] WxH+X+Y
        m = re.match(
            r'^(\S+) connected (primary )?(\d+)x(\d+)\+(\d+)\+(\d+)', line
        )
        if m:
            displays.append({
                "name":    m.group(1),
                "primary": bool(m.group(2)),
                "width":   int(m.group(3)),
                "height":  int(m.group(4)),
                "x":       int(m.group(5)),
                "y":       int(m.group(6)),
            })
    return displays


def find_eve_windows() -> list[str]:
    """Search XWayland windows whose name contains 'EVE'."""
    out, _, code = run(["xdotool", "search", "--name", "EVE"])
    if code != 0 or not out:
        return []
    return [w for w in out.splitlines() if w.strip()]


def get_window_geometry(wid: str) -> dict | None:
    """Return {x, y, width, height} for a window id."""
    out, _, code = run(["xdotool", "getwindowgeometry", wid])
    if code != 0:
        return None
    pos = re.search(r'Position:\s*(-?\d+),(-?\d+)', out)
    geo = re.search(r'Geometry:\s*(\d+)x(\d+)', out)
    if pos and geo:
        return {
            "x": int(pos.group(1)), "y": int(pos.group(2)),
            "width": int(geo.group(1)), "height": int(geo.group(2)),
        }
    return None


def center_on_display(wid: str, display: dict, win_w: int, win_h: int) -> tuple[int, int]:
    """Move a window to the center of a given display. Returns (x, y)."""
    x = display["x"] + (display["width"]  - win_w) // 2
    y = display["y"] + (display["height"] - win_h) // 2
    run(["xdotool", "windowmove", wid, str(x), str(y)])
    return x, y


# ── Application ────────────────────────────────────────────────────────────────

class EveCenterApp(tk.Tk):

    PRESETS = [
        ("1920 × 1080  (streaming / Full HD)", 1920, 1080),
        ("2560 × 1440  (QHD)", 2560, 1440),
        ("3440 × 1440  (Ultrawide QHD)", 3440, 1440),
        ("2560 × 1080  (Ultrawide FHD)", 2560, 1080),
        ("1280 × 720   (720p streaming)", 1280, 720),
        ("Custom", 0, 0),
    ]

    def __init__(self):
        super().__init__()
        self.title("EVE Window Centering Tool")
        self.resizable(False, False)
        self.configure(bg=BG)

        # Fonts
        mono  = tkfont.Font(family="Monospace", size=9)
        head  = tkfont.Font(family="Monospace", size=11, weight="bold")
        title = tkfont.Font(family="Monospace", size=14, weight="bold")
        tiny  = tkfont.Font(family="Monospace", size=8)

        self._fonts = (mono, head, title, tiny)   # keep refs alive

        # ── Title bar ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG, pady=0)
        hdr.pack(fill="x", padx=0)

        top_bar = tk.Frame(hdr, bg=ACCENT2, height=2)
        top_bar.pack(fill="x")

        inner = tk.Frame(hdr, bg=BG, padx=20, pady=12)
        inner.pack(fill="x")

        tk.Label(inner, text="◈  EVE ONLINE", font=title,
                 fg=ACCENT, bg=BG).pack(side="left")
        tk.Label(inner, text="Window Centering Tool", font=mono,
                 fg=TEXT_DIM, bg=BG).pack(side="left", padx=(10, 0), pady=(4, 0))

        # ── Dependency warning banner (shown only if xdotool missing) ──────────
        self.dep_frame = tk.Frame(self, bg="#2a0a0a", padx=20, pady=8)
        self.dep_label = tk.Label(
            self.dep_frame,
            text="⚠  xdotool not found — install with:  sudo dnf install xdotool",
            font=tiny, fg=ERROR, bg="#2a0a0a", justify="left"
        )
        self.dep_label.pack(anchor="w")

        # ── Main content ───────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG, padx=20, pady=4)
        body.pack(fill="both")

        # ── Display detection panel ────────────────────────────────────────────
        self._section(body, "MONITOR")

        disp_frame = tk.Frame(body, bg=PANEL, bd=0, relief="flat",
                              highlightthickness=1, highlightbackground=BORDER)
        disp_frame.pack(fill="x", pady=(0, 14))
        disp_inner = tk.Frame(disp_frame, bg=PANEL, padx=14, pady=10)
        disp_inner.pack(fill="x")

        tk.Label(disp_inner, text="Target display:", font=mono,
                 fg=TEXT_DIM, bg=PANEL).grid(row=0, column=0, sticky="w")

        self.display_var = tk.StringVar()
        self.display_menu = tk.OptionMenu(disp_inner, self.display_var, "")
        self._style_option_menu(self.display_menu, mono)
        self.display_menu.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        disp_inner.columnconfigure(1, weight=1)

        self.disp_info = tk.Label(disp_inner, text="", font=tiny,
                                  fg=TEXT_DIM, bg=PANEL)
        self.disp_info.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        tk.Button(disp_inner, text="↺  Refresh", command=self._refresh_displays,
                  font=tiny, fg=ACCENT, bg=PANEL, activeforeground=ACCENT,
                  activebackground=PANEL, bd=0, cursor="hand2",
                  relief="flat").grid(row=0, column=2, padx=(10, 0))

        # ── Window size panel ──────────────────────────────────────────────────
        self._section(body, "EVE WINDOW RESOLUTION")

        win_frame = tk.Frame(body, bg=PANEL, bd=0, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER)
        win_frame.pack(fill="x", pady=(0, 14))
        win_inner = tk.Frame(win_frame, bg=PANEL, padx=14, pady=10)
        win_inner.pack(fill="x")

        tk.Label(win_inner, text="Preset:", font=mono,
                 fg=TEXT_DIM, bg=PANEL).grid(row=0, column=0, sticky="w")

        self.preset_var = tk.StringVar()
        preset_labels = [p[0] for p in self.PRESETS]
        self.preset_menu = tk.OptionMenu(
            win_inner, self.preset_var, *preset_labels,
            command=self._on_preset
        )
        self._style_option_menu(self.preset_menu, mono)
        self.preset_menu.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(10, 0))
        win_inner.columnconfigure(1, weight=1)

        # Custom width / height
        row2 = tk.Frame(win_inner, bg=PANEL)
        row2.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        tk.Label(row2, text="Width:", font=mono, fg=TEXT_DIM, bg=PANEL).pack(side="left")
        self.width_var = tk.StringVar(value="1920")
        self.width_entry = self._entry(row2, self.width_var, mono, width=7)
        self.width_entry.pack(side="left", padx=(6, 16))

        tk.Label(row2, text="Height:", font=mono, fg=TEXT_DIM, bg=PANEL).pack(side="left")
        self.height_var = tk.StringVar(value="1080")
        self.height_entry = self._entry(row2, self.height_var, mono, width=7)
        self.height_entry.pack(side="left", padx=(6, 0))

        # ── Window detection panel ─────────────────────────────────────────────
        self._section(body, "EVE CLIENT")

        eve_frame = tk.Frame(body, bg=PANEL, bd=0, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER)
        eve_frame.pack(fill="x", pady=(0, 14))
        eve_inner = tk.Frame(eve_frame, bg=PANEL, padx=14, pady=10)
        eve_inner.pack(fill="x")

        top_row = tk.Frame(eve_inner, bg=PANEL)
        top_row.pack(fill="x")

        self.eve_status = tk.Label(top_row, text="● Not detected",
                                   font=mono, fg=ERROR, bg=PANEL)
        self.eve_status.pack(side="left")

        tk.Button(top_row, text="↺  Scan", command=self._refresh_eve,
                  font=tiny, fg=ACCENT, bg=PANEL, activeforeground=ACCENT,
                  activebackground=PANEL, bd=0, cursor="hand2",
                  relief="flat").pack(side="right")

        self.eve_detail = tk.Label(eve_inner, text="", font=tiny,
                                   fg=TEXT_DIM, bg=PANEL)
        self.eve_detail.pack(anchor="w", pady=(4, 0))

        # ── Action button ──────────────────────────────────────────────────────
        btn_frame = tk.Frame(body, bg=BG, pady=6)
        btn_frame.pack(fill="x")

        self.center_btn = tk.Button(
            btn_frame,
            text="⊹  CENTER EVE WINDOW",
            command=self._do_center,
            font=head,
            fg=BG, bg=ACCENT, activeforeground=BG, activebackground=ACCENT2,
            bd=0, relief="flat", cursor="hand2",
            padx=24, pady=12,
        )
        self.center_btn.pack(fill="x")
        self.center_btn.bind("<Enter>", lambda e: self.center_btn.config(bg=ACCENT2))
        self.center_btn.bind("<Leave>", lambda e: self.center_btn.config(bg=ACCENT))

        # ── Status bar ─────────────────────────────────────────────────────────
        self.status_bar = tk.Label(
            self, text="", font=tiny, fg=TEXT_DIM, bg=BG2,
            anchor="w", padx=20, pady=6
        )
        self.status_bar.pack(fill="x", side="bottom")

        bot_bar = tk.Frame(self, bg=ACCENT2, height=2)
        bot_bar.pack(fill="x", side="bottom")

        # ── Init ───────────────────────────────────────────────────────────────
        self._displays: list[dict] = []
        self._eve_wids: list[str] = []

        self.preset_var.set(self.PRESETS[0][0])

        self._check_deps()
        self._refresh_displays()
        self._refresh_eve()

        # Center this tool window itself
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = self.winfo_width()
        h  = self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── UI helpers ─────────────────────────────────────────────────────────────

    def _section(self, parent, text):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", pady=(6, 4))
        tk.Label(f, text=text, font=tkfont.Font(family="Monospace", size=7, weight="bold"),
                 fg=GOLD, bg=BG).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x",
                                               expand=True, padx=(8, 0), pady=(2, 0))

    def _entry(self, parent, textvariable, fnt, width=10):
        e = tk.Entry(
            parent, textvariable=textvariable, font=fnt,
            fg=TEXT, bg=BG2, insertbackground=ACCENT,
            highlightthickness=1, highlightcolor=ACCENT,
            highlightbackground=BORDER, bd=0, relief="flat", width=width
        )
        return e

    def _style_option_menu(self, menu, fnt):
        menu.config(
            font=fnt, fg=TEXT, bg=BTN_BG, activeforeground=ACCENT,
            activebackground=BTN_HOVER, bd=0, relief="flat",
            highlightthickness=1, highlightbackground=BORDER,
            indicatoron=True, padx=8, pady=4, cursor="hand2",
        )
        menu["menu"].config(
            font=fnt, fg=TEXT, bg=PANEL,
            activeforeground=ACCENT, activebackground=BTN_HOVER,
            bd=0, relief="flat",
        )

    # ── Logic ──────────────────────────────────────────────────────────────────

    def _check_deps(self):
        if not check_dependency("xdotool"):
            self.dep_frame.pack(fill="x", after=self.nametowidget(self.winfo_children()[1]))
            self.dep_frame.pack(fill="x")
            self.center_btn.config(state="disabled", bg=TEXT_DIM)
        if not check_dependency("xrandr"):
            self._set_status("⚠  xrandr not found — display detection unavailable", ERROR)

    def _refresh_displays(self):
        self._displays = get_displays()
        menu = self.display_menu["menu"]
        menu.delete(0, "end")

        if not self._displays:
            self.display_var.set("No displays detected")
            self.disp_info.config(text="Run 'xrandr --current' to debug")
            return

        for d in self._displays:
            label = (
                f"{'★ ' if d['primary'] else '  '}"
                f"{d['name']}  {d['width']}×{d['height']}"
                f"  @+{d['x']},+{d['y']}"
            )
            menu.add_command(
                label=label,
                command=lambda lbl=label, dsp=d: self._select_display(lbl, dsp)
            )

        # Default to primary
        primary = next((d for d in self._displays if d["primary"]), self._displays[0])
        label = (
            f"{'★ ' if primary['primary'] else '  '}"
            f"{primary['name']}  {primary['width']}×{primary['height']}"
            f"  @+{primary['x']},+{primary['y']}"
        )
        self._select_display(label, primary)

    def _select_display(self, label: str, display: dict):
        self.display_var.set(label)
        self._active_display = display
        self.disp_info.config(
            text=f"Resolution: {display['width']}×{display['height']}  "
                 f"| Offset: +{display['x']},+{display['y']}"
        )

    def _on_preset(self, selection):
        for label, w, h in self.PRESETS:
            if selection == label:
                if w and h:
                    self.width_var.set(str(w))
                    self.height_var.set(str(h))
                    self.width_entry.config(state="disabled", fg=TEXT_DIM)
                    self.height_entry.config(state="disabled", fg=TEXT_DIM)
                else:
                    self.width_entry.config(state="normal", fg=TEXT)
                    self.height_entry.config(state="normal", fg=TEXT)
                break

    def _refresh_eve(self):
        self._eve_wids = find_eve_windows()
        if self._eve_wids:
            self.eve_status.config(
                text=f"● Running  ({len(self._eve_wids)} window{'s' if len(self._eve_wids) > 1 else ''})",
                fg=SUCCESS
            )
            geo = get_window_geometry(self._eve_wids[0])
            if geo:
                self.eve_detail.config(
                    text=f"Current position: ({geo['x']}, {geo['y']})  "
                         f"Size: {geo['width']}×{geo['height']}"
                )
        else:
            self.eve_status.config(text="● Not detected", fg=ERROR)
            self.eve_detail.config(text="Launch EVE Online first, then click Scan.")

    def _set_status(self, msg: str, color: str = TEXT_DIM):
        self.status_bar.config(text=msg, fg=color)

    def _do_center(self):
        # Validate inputs
        try:
            win_w = int(self.width_var.get())
            win_h = int(self.height_var.get())
            assert win_w > 0 and win_h > 0
        except (ValueError, AssertionError):
            self._set_status("⚠  Invalid window size — enter positive integers.", ERROR)
            return

        display = getattr(self, "_active_display", None)
        if display is None:
            self._set_status("⚠  No display selected.", ERROR)
            return

        # Re-scan for Eve windows
        self._refresh_eve()
        if not self._eve_wids:
            self._set_status("⚠  EVE Online window not found. Is the client running?", ERROR)
            return

        # Warn if window is larger than display
        if win_w > display["width"] or win_h > display["height"]:
            self._set_status(
                f"⚠  Window ({win_w}×{win_h}) is larger than display "
                f"({display['width']}×{display['height']}).",
                ERROR
            )
            return

        moved = []
        for wid in self._eve_wids:
            x, y = center_on_display(wid, display, win_w, win_h)
            moved.append(f"wid={wid} → ({x},{y})")

        self._set_status(
            f"✓  Centered {len(moved)} window(s) at {display['name']} "
            f"[{win_w}×{win_h} on {display['width']}×{display['height']}]",
            SUCCESS
        )
        self._refresh_eve()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # On XWayland, force X11 backend so xdotool coordinates align
    import os
    os.environ.setdefault("GDK_BACKEND", "x11")

    app = EveCenterApp()
    app.mainloop()
