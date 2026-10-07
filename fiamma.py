#!/usr/bin/env python3
"""Fiamma — timer di concentrazione, attività e statistiche.

GTK4 + libadwaita, nessuna dipendenza esterna.
"""
import datetime as dt
import json
import math
import os
import struct
import sys
import uuid
import wave

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("PangoCairo", "1.0")
gi.require_foreign("cairo")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango, PangoCairo  # noqa: E402

APP_ID = "Faghy.Fiamma"
VERSION = "1.0.0"
DATA_DIR = os.path.join(GLib.get_user_data_dir(), "fiamma")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
CHIME_FILE = os.path.join(DATA_DIR, "chime.wav")

MODES = {
    "focus": {"label": "Concentrazione", "short": "Focus", "colors": ("#ff7a59", "#e8336d")},
    "short": {"label": "Pausa breve", "short": "Pausa", "colors": ("#2ec4b6", "#3a86ff")},
    "long": {"label": "Pausa lunga", "short": "Pausa lunga", "colors": ("#8e7dff", "#c86dd7")},
}
WEEKDAYS = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]

DEFAULT_SETTINGS = {
    "focus": 25, "short": 5, "long": 15, "every": 4, "goal": 8,
    "auto_breaks": True, "auto_focus": False, "sound": True, "notify": True,
}

CSS = """
.timer-digits { font-size: 58pt; font-weight: 300; font-feature-settings: "tnum"; letter-spacing: -1px; }
.timer-caption { font-size: 11pt; font-weight: 600; letter-spacing: 2px; opacity: .65; }
.task-caption { font-size: 11pt; opacity: .8; }
.play-btn { min-width: 76px; min-height: 76px; border-radius: 999px; color: white; font-weight: 700; }
.play-btn image { -gtk-icon-size: 30px; }
.side-btn { min-width: 48px; min-height: 48px; border-radius: 999px; }
.mode-focus .play-btn { background: linear-gradient(135deg, #ff7a59, #e8336d); }
.mode-short .play-btn { background: linear-gradient(135deg, #2ec4b6, #3a86ff); }
.mode-long  .play-btn { background: linear-gradient(135deg, #8e7dff, #c86dd7); }
.play-btn:hover { filter: brightness(1.08); }
.dot { min-width: 10px; min-height: 10px; border-radius: 99px; background: alpha(currentColor, .18); }
.mode-focus .dot.on { background: #ff7a59; }
.mode-short .dot.on { background: #2ec4b6; }
.mode-long  .dot.on { background: #8e7dff; }
.stat-card { padding: 18px; border-radius: 16px; }
.stat-value { font-size: 26pt; font-weight: 700; font-feature-settings: "tnum"; }
.stat-label { font-size: 10pt; opacity: .7; }
.current-task { color: #ff7a59; }
"""


# ---------------------------------------------------------------- dati

def today():
    return dt.date.today()


class Store:
    def __init__(self):
        self.settings = dict(DEFAULT_SETTINGS)
        self.tasks = []
        self.history = []
        self.current_task = None
        self.load()

    def load(self):
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        self.settings.update(d.get("settings", {}))
        self.tasks = d.get("tasks", [])
        self.history = d.get("history", [])
        self.current_task = d.get("current_task")

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"settings": self.settings, "tasks": self.tasks,
                       "history": self.history, "current_task": self.current_task},
                      f, ensure_ascii=False, indent=1)
        os.replace(tmp, DATA_FILE)

    def task(self, tid):
        return next((t for t in self.tasks if t["id"] == tid), None)

    def add_task(self, title):
        t = {"id": uuid.uuid4().hex[:10], "title": title, "done": False, "pomos": 0}
        self.tasks.append(t)
        if self.current_task is None:
            self.current_task = t["id"]
        self.save()

    def record_session(self, minutes):
        self.history.append({"ts": dt.datetime.now().isoformat(timespec="seconds"),
                             "minutes": minutes, "task": self.current_task})
        t = self.task(self.current_task)
        if t:
            t["pomos"] += 1
        self.save()

    # statistiche
    def per_day(self):
        days = {}
        for h in self.history:
            d = dt.date.fromisoformat(h["ts"][:10])
            c, m = days.get(d, (0, 0))
            days[d] = (c + 1, m + h["minutes"])
        return days

    def streak(self):
        days = self.per_day()
        d = today()
        if d not in days:
            d -= dt.timedelta(days=1)
        n = 0
        while d in days:
            n += 1
            d -= dt.timedelta(days=1)
        return n


def ensure_chime():
    """Genera un rintocco morbido (tre note) se non esiste già."""
    if os.path.exists(CHIME_FILE):
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    rate, frames = 44100, []
    notes = [(0.0, 659.25), (0.18, 783.99), (0.36, 1046.5)]
    length = 2.0
    for i in range(int(rate * length)):
        t = i / rate
        s = 0.0
        for start, f in notes:
            if t >= start:
                tt = t - start
                env = math.exp(-3.2 * tt) * min(1.0, tt * 200)
                s += env * (math.sin(2 * math.pi * f * tt) + 0.3 * math.sin(4 * math.pi * f * tt))
        frames.append(struct.pack("<h", int(max(-1, min(1, s * 0.22)) * 32767)))
    with wave.open(CHIME_FILE, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(frames))


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ---------------------------------------------------------------- anello

class Ring(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.progress = 0.0
        self.colors = MODES["focus"]["colors"]
        self.set_content_width(300)
        self.set_content_height(300)
        self.set_draw_func(self.draw)

    def update(self, progress, colors):
        self.progress, self.colors = progress, colors
        self.queue_draw()

    def draw(self, _area, cr, w, h):
        fg = self.get_color()
        size = min(w, h)
        lw = size * 0.055
        r = size / 2 - lw
        cx, cy = w / 2, h / 2

        cr.set_line_width(lw)
        cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.08)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()

        # tacche dei minuti
        cr.set_line_width(max(1.0, lw * 0.12))
        for i in range(60):
            a = i / 60 * 2 * math.pi - math.pi / 2
            inner = r - lw * (1.4 if i % 5 == 0 else 1.0)
            outer = r - lw * 0.75
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.22 if i % 5 == 0 else 0.09)
            cr.move_to(cx + inner * math.cos(a), cy + inner * math.sin(a))
            cr.line_to(cx + outer * math.cos(a), cy + outer * math.sin(a))
            cr.stroke()

        p = max(0.0, min(1.0, self.progress))
        if p <= 0:
            return
        import cairo
        c1, c2 = hex_rgb(self.colors[0]), hex_rgb(self.colors[1])
        grad = cairo.LinearGradient(cx - r, cy - r, cx + r, cy + r)
        grad.add_color_stop_rgb(0, *c1)
        grad.add_color_stop_rgb(1, *c2)
        start = -math.pi / 2
        end = start + p * 2 * math.pi

        # alone
        for k, alpha in ((2.6, 0.06), (1.8, 0.10)):
            cr.set_line_width(lw * k)
            cr.set_source_rgba(*c2, alpha)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.arc(cx, cy, r, start, end)
            cr.stroke()

        cr.set_source(grad)
        cr.set_line_width(lw)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.arc(cx, cy, r, start, end)
        cr.stroke()

        # punto luminoso in testa
        hx, hy = cx + r * math.cos(end), cy + r * math.sin(end)
        cr.set_source_rgba(1, 1, 1, 0.95)
        cr.arc(hx, hy, lw * 0.28, 0, 2 * math.pi)
        cr.fill()


# ---------------------------------------------------------------- grafico

class WeekChart(Gtk.DrawingArea):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.set_content_height(220)
        self.set_hexpand(True)
        self.set_draw_func(self.draw)

    def draw(self, _area, cr, w, h):
        import cairo
        fg = self.get_color()
        days = self.store.per_day()
        last = [today() - dt.timedelta(days=i) for i in range(6, -1, -1)]
        vals = [days.get(d, (0, 0))[1] for d in last]
        top = max(max(vals), 60)
        top = int(math.ceil(top / 30) * 30)

        pad_l, pad_b, pad_t = 36, 28, 14
        cw, ch = w - pad_l - 6, h - pad_b - pad_t
        layout = PangoCairo.create_layout(cr)
        fd = Pango.FontDescription.from_string("Sans 8")
        layout.set_font_description(fd)

        # griglia
        for i in range(4):
            v = top * i / 3
            y = pad_t + ch - ch * i / 3
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.08)
            cr.set_line_width(1)
            cr.move_to(pad_l, y + 0.5)
            cr.line_to(w - 6, y + 0.5)
            cr.stroke()
            layout.set_text(f"{int(v)}m", -1)
            tw, th = layout.get_pixel_size()
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.5)
            cr.move_to(pad_l - tw - 6, y - th / 2)
            PangoCairo.show_layout(cr, layout)

        slot = cw / 7
        bw = min(34, slot * 0.56)
        c1, c2 = hex_rgb("#ff7a59"), hex_rgb("#e8336d")
        for i, (d, v) in enumerate(zip(last, vals)):
            x = pad_l + slot * i + (slot - bw) / 2
            bh = ch * v / top
            y = pad_t + ch - bh
            if v > 0:
                rad = min(8, bw / 2, bh / 2)
                grad = cairo.LinearGradient(0, y, 0, y + bh)
                grad.add_color_stop_rgb(0, *c1)
                grad.add_color_stop_rgb(1, *c2)
                cr.set_source(grad)
                cr.new_sub_path()
                cr.arc(x + bw - rad, y + rad, rad, -math.pi / 2, 0)
                cr.line_to(x + bw, y + bh)
                cr.line_to(x, y + bh)
                cr.arc(x + rad, y + rad, rad, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.fill()
                layout.set_text(str(v), -1)
                tw, th = layout.get_pixel_size()
                cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.75)
                cr.move_to(x + bw / 2 - tw / 2, y - th - 2)
                PangoCairo.show_layout(cr, layout)
            label = "Oggi" if d == today() else WEEKDAYS[d.weekday()]
            layout.set_text(label, -1)
            tw, th = layout.get_pixel_size()
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.9 if d == today() else 0.55)
            cr.move_to(x + bw / 2 - tw / 2, h - pad_b + 8)
            PangoCairo.show_layout(cr, layout)


# ---------------------------------------------------------------- finestra

class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Fiamma")
        self.app = app
        self.store = app.store
        self.set_default_size(460, 720)
        self.set_size_request(360, 560)

        self.mode = "focus"
        self.cycle = 0               # sessioni di focus completate nel ciclo
        self.running = False
        self.end_time = 0            # monotonic, microsecondi
        self.remaining = self.duration(self.mode)
        self.tick_id = 0
        self._media = None

        self.stack = Adw.ViewStack()
        self.stack.add_titled_with_icon(self.build_timer(), "timer", "Timer", "alarm-symbolic")
        self.stack.add_titled_with_icon(self.build_tasks(), "tasks", "Attività", "checkbox-checked-symbolic")
        self.stack.add_titled_with_icon(self.build_stats(), "stats", "Statistiche", "power-profile-performance-symbolic")
        self.stack.connect("notify::visible-child-name", lambda *_: self.refresh_stats())

        header = Adw.HeaderBar()
        switcher = Adw.ViewSwitcher(stack=self.stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)
        menu = Gio.Menu()
        menu.append("Preferenze", "win.prefs")
        menu.append("Scorciatoie da tastiera", "win.shortcuts")
        menu.append("Informazioni su Fiamma", "win.about")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu,
                                       tooltip_text="Menu principale"))

        bottom = Adw.ViewSwitcherBar(stack=self.stack)
        tv = Adw.ToolbarView()
        tv.add_top_bar(header)
        tv.add_bottom_bar(bottom)
        tv.set_content(self.stack)
        self.toast = Adw.ToastOverlay(child=tv)
        self.set_content(self.toast)

        bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 520sp"))
        bp.add_setter(switcher, "visible", False)
        bp.add_setter(bottom, "reveal", True)
        self.add_breakpoint(bp)

        for name, cb in (("prefs", self.show_prefs), ("about", self.show_about),
                         ("shortcuts", self.show_shortcuts), ("toggle", self.toggle),
                         ("reset", self.reset), ("skip", self.skip)):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda *_a, f=cb: f())
            self.add_action(a)

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)

        self.apply_mode()
        self.refresh_tasks()

    # ----- costruzione pagine

    def build_timer(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22,
                      margin_top=18, margin_bottom=24, margin_start=18, margin_end=18,
                      valign=Gtk.Align.CENTER)

        self.mode_buttons = {}
        modes = Gtk.Box(css_classes=["linked"], halign=Gtk.Align.CENTER)
        group = None
        for key in ("focus", "short", "long"):
            b = Gtk.ToggleButton(label=MODES[key]["short"], group=group)
            group = group or b
            b.connect("toggled", self.on_mode_toggled, key)
            modes.append(b)
            self.mode_buttons[key] = b
        self.mode_buttons["focus"].set_active(True)
        box.append(modes)

        self.ring = Ring()
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.caption = Gtk.Label(css_classes=["timer-caption"])
        self.digits = Gtk.Label(css_classes=["timer-digits"])
        self.dots = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER, margin_top=8)
        center.append(self.caption)
        center.append(self.digits)
        center.append(self.dots)
        overlay = Gtk.Overlay(child=self.ring, halign=Gtk.Align.CENTER)
        overlay.add_overlay(center)
        clamp = Adw.Clamp(maximum_size=340, child=overlay)
        box.append(clamp)

        self.task_label = Gtk.Button(css_classes=["flat", "task-caption"], halign=Gtk.Align.CENTER)
        self.task_label.connect("clicked", lambda *_: self.stack.set_visible_child_name("tasks"))
        box.append(self.task_label)

        controls = Gtk.Box(spacing=26, halign=Gtk.Align.CENTER)
        reset = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Azzera (R)",
                           css_classes=["side-btn"], valign=Gtk.Align.CENTER, action_name="win.reset")
        self.play = Gtk.Button(icon_name="media-playback-start-symbolic", tooltip_text="Avvia / pausa (Spazio)",
                               css_classes=["play-btn"], action_name="win.toggle")
        skip = Gtk.Button(icon_name="media-skip-forward-symbolic", tooltip_text="Salta (N)",
                          css_classes=["side-btn"], valign=Gtk.Align.CENTER, action_name="win.skip")
        for w in (reset, self.play, skip):
            controls.append(w)
        box.append(controls)

        self.timer_page = box
        return Gtk.ScrolledWindow(child=box, hscrollbar_policy=Gtk.PolicyType.NEVER)

    def build_tasks(self):
        page = Adw.PreferencesPage()
        add_group = Adw.PreferencesGroup(title="Su cosa vuoi concentrarti?",
                                         description="Seleziona il bersaglio per lavorare su un'attività: "
                                                     "ogni pomodoro completato verrà conteggiato lì.")
        self.entry = Adw.EntryRow(title="Nuova attività", show_apply_button=True)
        self.entry.connect("apply", self.on_add_task)
        self.entry.connect("entry-activated", self.on_add_task)
        add_group.add(self.entry)
        page.add(add_group)

        self.todo_group = Adw.PreferencesGroup(title="Da fare")
        self.done_group = Adw.PreferencesGroup(title="Completate")
        clear = Gtk.Button(label="Svuota", css_classes=["flat"], valign=Gtk.Align.CENTER)
        clear.connect("clicked", self.on_clear_done)
        self.done_group.set_header_suffix(clear)
        page.add(self.todo_group)
        page.add(self.done_group)
        self.task_rows = []
        return page

    def build_stats(self):
        page = Adw.PreferencesPage()
        g = Adw.PreferencesGroup()
        grid = Gtk.Grid(column_spacing=12, row_spacing=12, column_homogeneous=True)
        self.stat_labels = {}
        cards = [("today", "Pomodori oggi"), ("minutes", "Minuti di focus oggi"),
                 ("streak", "Giorni di fila"), ("total", "Ore totali")]
        for i, (key, text) in enumerate(cards):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, css_classes=["card", "stat-card"])
            v = Gtk.Label(xalign=0, css_classes=["stat-value"])
            card.append(v)
            card.append(Gtk.Label(label=text, xalign=0, css_classes=["stat-label"], wrap=True))
            grid.attach(card, i % 2, i // 2, 1, 1)
            self.stat_labels[key] = v
        g.add(grid)
        page.add(g)

        goal = Adw.PreferencesGroup(title="Obiettivo giornaliero")
        self.goal_bar = Gtk.LevelBar(min_value=0, max_value=1, margin_top=6)
        self.goal_label = Gtk.Label(xalign=0, css_classes=["dim-label"], margin_top=6)
        goal.add(self.goal_bar)
        goal.add(self.goal_label)
        page.add(goal)

        week = Adw.PreferencesGroup(title="Ultimi 7 giorni", description="Minuti di concentrazione al giorno")
        frame = Gtk.Box(css_classes=["card"])
        self.chart = WeekChart(self.store)
        self.chart.set_margin_top(14)
        self.chart.set_margin_bottom(10)
        self.chart.set_margin_start(10)
        self.chart.set_margin_end(14)
        frame.append(self.chart)
        week.add(frame)
        page.add(week)

        self.top_group = Adw.PreferencesGroup(title="Attività più lavorate")
        page.add(self.top_group)
        self.top_rows = []
        self.refresh_stats()
        return page

    # ----- timer

    def duration(self, mode):
        return self.store.settings[mode] * 60

    def apply_mode(self):
        win_classes = [c for c in self.get_css_classes() if not c.startswith("mode-")]
        self.set_css_classes(win_classes + [f"mode-{self.mode}"])
        if not self.mode_buttons[self.mode].get_active():
            self._silent = True
            self.mode_buttons[self.mode].set_active(True)
            self._silent = False
        self.caption.set_label(MODES[self.mode]["label"].upper())
        child = self.dots.get_first_child()
        while child:
            self.dots.remove(child)
            child = self.dots.get_first_child()
        every = self.store.settings["every"]
        for i in range(every):
            on = i < self.cycle % every or (self.mode == "long" and self.cycle and self.cycle % every == 0)
            self.dots.append(Gtk.Box(css_classes=["dot", "on"] if on else ["dot"], valign=Gtk.Align.CENTER))
        self.refresh_display()

    def refresh_display(self):
        secs = max(0, int(math.ceil(self.remaining)))
        txt = f"{secs // 60:02d}:{secs % 60:02d}"
        self.digits.set_label(txt)
        total = self.duration(self.mode)
        self.ring.update(1 - self.remaining / total if total else 0, MODES[self.mode]["colors"])
        self.play.set_icon_name("media-playback-pause-symbolic" if self.running
                                else "media-playback-start-symbolic")
        self.set_title(f"{txt} · {MODES[self.mode]['short']} — Fiamma" if self.running else "Fiamma")

    def on_mode_toggled(self, btn, key):
        if not btn.get_active() or getattr(self, "_silent", False) or key == self.mode:
            return
        self.stop()
        self.mode = key
        self.remaining = self.duration(key)
        self.apply_mode()

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.running = True
            self.end_time = GLib.get_monotonic_time() + int(self.remaining * 1e6)
            self.tick_id = GLib.timeout_add(50, self.on_tick)
        self.refresh_display()

    def stop(self):
        if self.running:
            self.remaining = max(0, (self.end_time - GLib.get_monotonic_time()) / 1e6)
        self.running = False
        if self.tick_id:
            GLib.source_remove(self.tick_id)
            self.tick_id = 0

    def reset(self):
        self.stop()
        self.remaining = self.duration(self.mode)
        self.refresh_display()

    def skip(self):
        self.stop()
        self.advance(completed=False)

    def on_tick(self):
        self.remaining = (self.end_time - GLib.get_monotonic_time()) / 1e6
        if self.remaining <= 0:
            self.tick_id = 0
            self.running = False
            self.remaining = 0
            self.finish()
            return GLib.SOURCE_REMOVE
        self.refresh_display()
        return GLib.SOURCE_CONTINUE

    def finish(self):
        s = self.store.settings
        if self.mode == "focus":
            self.store.record_session(s["focus"])
            self.refresh_tasks()
            done_today = self.store.per_day().get(today(), (0, 0))[0]
            title = "Pomodoro completato! 🍅"
            body = f"{done_today} oggi. Concediti una pausa."
            if done_today == s["goal"]:
                self.toast.add_toast(Adw.Toast(title="🎉 Obiettivo giornaliero raggiunto!", timeout=6))
        else:
            title = "Pausa finita"
            body = "Pronto a ripartire?"
        self.alert(title, body)
        self.advance(completed=True)
        auto = s["auto_breaks"] if self.mode != "focus" else s["auto_focus"]
        if auto:
            self.toggle()

    def advance(self, completed):
        if self.mode == "focus":
            if completed:
                self.cycle += 1
            every = self.store.settings["every"]
            self.mode = "long" if self.cycle and self.cycle % every == 0 and completed else "short"
        else:
            if self.mode == "long":
                self.cycle = 0
            self.mode = "focus"
        self.remaining = self.duration(self.mode)
        self.apply_mode()

    def alert(self, title, body):
        s = self.store.settings
        if s["sound"]:
            try:
                ensure_chime()
                self._media = Gtk.MediaFile.new_for_filename(CHIME_FILE)
                self._media.play()
            except Exception:
                pass
        if s["notify"] and not self.is_active():
            n = Gio.Notification.new(title)
            n.set_body(body)
            n.set_priority(Gio.NotificationPriority.HIGH)
            self.app.send_notification("fiamma-timer", n)
        self.toast.add_toast(Adw.Toast(title=title, timeout=4))

    def on_key(self, _ctl, keyval, _code, state):
        if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            return False
        if isinstance(self.get_focus(), Gtk.Text):
            return False
        action = {Gdk.KEY_space: self.toggle, Gdk.KEY_r: self.reset, Gdk.KEY_n: self.skip}.get(keyval)
        if action:
            action()
            return True
        return False

    # ----- attività

    def on_add_task(self, entry):
        title = entry.get_text().strip()
        if not title:
            return
        self.store.add_task(title)
        entry.set_text("")
        self.refresh_tasks()

    def on_clear_done(self, _btn):
        self.store.tasks = [t for t in self.store.tasks if not t["done"]]
        self.store.save()
        self.refresh_tasks()

    def refresh_tasks(self):
        for group, row in self.task_rows:
            group.remove(row)
        self.task_rows = []
        todo = [t for t in self.store.tasks if not t["done"]]
        done = [t for t in self.store.tasks if t["done"]]

        for t in todo + done:
            group = self.done_group if t["done"] else self.todo_group
            row = Adw.ActionRow(title=GLib.markup_escape_text(t["title"]))
            n = t["pomos"]
            row.set_subtitle("🍅 " * min(n, 8) + (f" {n}" if n > 8 else "") if n else "Nessun pomodoro ancora")
            check = Gtk.CheckButton(active=t["done"], valign=Gtk.Align.CENTER)
            check.connect("toggled", self.on_task_done, t["id"])
            row.add_prefix(check)
            row.set_activatable_widget(check)
            if not t["done"]:
                is_cur = t["id"] == self.store.current_task
                target = Gtk.Button(icon_name="find-location-symbolic" if not is_cur else "media-record-symbolic",
                                    tooltip_text="Attività corrente" if is_cur else "Lavora su questa",
                                    css_classes=["flat", "circular"] + (["current-task"] if is_cur else []),
                                    valign=Gtk.Align.CENTER)
                target.connect("clicked", self.on_task_select, t["id"])
                row.add_suffix(target)
                if is_cur:
                    row.set_title(f"<b>{GLib.markup_escape_text(t['title'])}</b>")
            else:
                row.add_css_class("dim-label")
            delete = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Elimina",
                                css_classes=["flat", "circular"], valign=Gtk.Align.CENTER)
            delete.connect("clicked", self.on_task_delete, t["id"])
            row.add_suffix(delete)
            group.add(row)
            self.task_rows.append((group, row))

        if not todo:
            row = Adw.ActionRow(title="Tutto fatto ✨", subtitle="Aggiungi qui sopra la prossima attività")
            self.todo_group.add(row)
            self.task_rows.append((self.todo_group, row))
        self.done_group.set_visible(bool(done))

        cur = self.store.task(self.store.current_task)
        if cur and not cur["done"]:
            self.task_label.set_label(f"◎  {cur['title']}")
        else:
            self.task_label.set_label("＋  Scegli un'attività")

    def on_task_done(self, check, tid):
        t = self.store.task(tid)
        if not t:
            return
        t["done"] = check.get_active()
        if t["done"] and self.store.current_task == tid:
            nxt = next((x for x in self.store.tasks if not x["done"]), None)
            self.store.current_task = nxt["id"] if nxt else None
        self.store.save()
        GLib.idle_add(self.refresh_tasks)

    def on_task_select(self, _btn, tid):
        self.store.current_task = tid
        self.store.save()
        self.refresh_tasks()
        self.stack.set_visible_child_name("timer")

    def on_task_delete(self, _btn, tid):
        t = self.store.task(tid)
        self.store.tasks = [x for x in self.store.tasks if x["id"] != tid]
        if self.store.current_task == tid:
            self.store.current_task = None
        self.store.save()
        self.refresh_tasks()
        toast = Adw.Toast(title=f"«{t['title']}» eliminata", button_label="Annulla", timeout=5)
        toast.connect("button-clicked", self.on_undo_delete, t)
        self.toast.add_toast(toast)

    def on_undo_delete(self, _toast, t):
        self.store.tasks.append(t)
        self.store.save()
        self.refresh_tasks()

    # ----- statistiche

    def refresh_stats(self):
        days = self.store.per_day()
        c, m = days.get(today(), (0, 0))
        total = sum(h["minutes"] for h in self.store.history)
        self.stat_labels["today"].set_label(str(c))
        self.stat_labels["minutes"].set_label(str(m))
        self.stat_labels["streak"].set_label(f"{self.store.streak()} 🔥")
        self.stat_labels["total"].set_label(f"{total / 60:.1f}")
        goal = self.store.settings["goal"]
        self.goal_bar.set_value(min(1.0, c / goal) if goal else 0)
        self.goal_label.set_label(f"{c} di {goal} pomodori"
                                  + (" — obiettivo raggiunto! 🎉" if c >= goal else f" — ne mancano {goal - c}"))
        self.chart.queue_draw()

        for row in self.top_rows:
            self.top_group.remove(row)
        self.top_rows = []
        top = sorted((t for t in self.store.tasks if t["pomos"]), key=lambda t: -t["pomos"])[:5]
        for t in top:
            row = Adw.ActionRow(title=GLib.markup_escape_text(t["title"]),
                                subtitle=f"{t['pomos']} pomodori · {t['pomos'] * self.store.settings['focus']} min")
            if t["done"]:
                row.add_suffix(Gtk.Image(icon_name="object-select-symbolic"))
            self.top_group.add(row)
            self.top_rows.append(row)
        self.top_group.set_visible(bool(top))

    # ----- dialoghi

    def show_prefs(self):
        s = self.store.settings
        dlg = Adw.PreferencesDialog(title="Preferenze")
        page = Adw.PreferencesPage(title="Generali", icon_name="preferences-system-symbolic")
        dur = Adw.PreferencesGroup(title="Durate", description="In minuti")

        def spin(title, key, lo, hi, subtitle=None):
            row = Adw.SpinRow.new_with_range(lo, hi, 1)
            row.set_title(title)
            if subtitle:
                row.set_subtitle(subtitle)
            row.set_value(s[key])
            row.connect("notify::value", self.on_setting, key, True)
            return row

        dur.add(spin("Concentrazione", "focus", 1, 120))
        dur.add(spin("Pausa breve", "short", 1, 30))
        dur.add(spin("Pausa lunga", "long", 1, 60))
        dur.add(spin("Pausa lunga ogni", "every", 2, 8, "Numero di pomodori"))
        page.add(dur)

        flow = Adw.PreferencesGroup(title="Comportamento")
        flow.add(spin("Obiettivo giornaliero", "goal", 1, 24, "Pomodori al giorno"))
        for title, key, sub in (("Avvia le pause automaticamente", "auto_breaks", None),
                                ("Avvia il focus dopo le pause", "auto_focus", None),
                                ("Suono di fine sessione", "sound", "Un rintocco morbido a tre note"),
                                ("Notifiche di sistema", "notify", "Quando la finestra non è in primo piano")):
            row = Adw.SwitchRow(title=title, active=s[key])
            if sub:
                row.set_subtitle(sub)
            row.connect("notify::active", self.on_setting, key, False)
            flow.add(row)
        page.add(flow)
        dlg.add(page)
        dlg.present(self)

    def on_setting(self, row, _pspec, key, numeric):
        self.store.settings[key] = int(row.get_value()) if numeric else row.get_active()
        self.store.save()
        if numeric and not self.running:
            if key == self.mode or key == "every":
                self.remaining = self.duration(self.mode)
            self.apply_mode()
        self.refresh_stats()

    def show_shortcuts(self):
        dlg = Adw.Dialog(title="Scorciatoie", content_width=340)
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        g = Adw.PreferencesGroup(margin_top=6, margin_bottom=18, margin_start=18, margin_end=18)
        for keys, what in (("Spazio", "Avvia / metti in pausa"), ("R", "Azzera il timer"),
                           ("N", "Passa alla sessione successiva"), ("Ctrl + ,", "Preferenze"),
                           ("Ctrl + Q", "Esci")):
            row = Adw.ActionRow(title=what)
            row.add_suffix(Gtk.Label(label=keys, css_classes=["dim-label", "monospace"]))
            g.add(row)
        tv.set_content(g)
        dlg.set_child(tv)
        dlg.present(self)

    def show_about(self):
        Adw.AboutDialog(application_name="Fiamma", application_icon="Faghy.Fiamma",
                        version=VERSION, developer_name="Creato con Claude",
                        comments="Timer di concentrazione con attività e statistiche.\n"
                                 "Piccolo, veloce, tutto in locale.",
                        license_type=Gtk.License.MIT_X11).present(self)

    def do_close_request(self):
        self.stop()
        self.store.save()
        return False


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.store = Store()

    def do_startup(self):
        Adw.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        here = os.path.dirname(os.path.abspath(__file__))
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(here)
        quit_ = Gio.SimpleAction.new("quit", None)
        quit_.connect("activate", lambda *_: self.quit())
        self.add_action(quit_)
        self.set_accels_for_action("app.quit", ["<Ctrl>q"])
        self.set_accels_for_action("win.prefs", ["<Ctrl>comma"])

    def do_activate(self):
        win = self.props.active_window or Window(self)
        win.present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
