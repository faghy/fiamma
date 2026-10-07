# 🔥 Fiamma

🇬🇧 **English** · 🇮🇹 [Italiano](README.it.md)

**Fiamma helps you focus.** You work for 25 minutes without distractions, then take a 5-minute break. Every 4 rounds you get a longer break. This method is called the *Pomodoro Technique*: each 25-minute block is a "pomodoro" (Italian for tomato 🍅).

## What it does, in plain words

1. **Press the big button and start working.** A colored ring fills up as time passes.
2. **When time is up, Fiamma plays a sound and tells you to take a break.** After the break, it lets you know it's time to start again.
3. **Write down what you need to do** in the *Tasks* tab and pick the one you're working on. Fiamma counts how many pomodoros you've spent on it.
4. **Check your progress** in the *Statistics* tab: how much you worked today, your streak of consecutive days, a weekly chart and a daily goal to reach.

Everything runs on your computer: no internet, no account. Your data stays in `~/.local/share/fiamma/data.json`.

> The app interface is currently in Italian.

## Features

- **Timer** with an animated ring that changes color: coral for focus, blue for short breaks, purple for long breaks
- **Automatic long break** every N pomodoros (4 by default), with dots showing where you are in the cycle
- **Tasks**: each completed pomodoro is counted on the selected task; deletions can be undone
- **Statistics**: today's pomodoros and minutes, day streak 🔥, total hours, daily goal, last-7-days chart, most worked-on tasks
- End-of-session chime, desktop notifications, automatic light/dark theme, adaptive layout for narrow windows
- Durations, daily goal and auto-start behavior configurable in Preferences

## Installation

Requires Linux with GNOME (or any system with GTK4 and libadwaita ≥ 1.5). On Debian/Ubuntu/Fedora with GNOME everything is already there; otherwise install `python3-gi`, `python3-gi-cairo` and `gir1.2-adw-1`.

```bash
git clone <repository-url>
cd fiamma
./fiamma.py      # try it right away
./install.sh     # add it to your app menu (command: fiamma)
```

Installation only touches your user folder; no admin rights needed.

## Keyboard shortcuts

| Key | Action |
|---|---|
| Space | Start / pause |
| R | Reset the timer |
| N | Skip to the next session |
| Ctrl + , | Preferences |
| Ctrl + Q | Quit |

## License

MIT
