#!/usr/bin/env bash
# Installa Fiamma per l'utente corrente (nessun permesso di root richiesto).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/share/fiamma/app"
mkdir -p "$DEST" "$HOME/.local/bin" "$HOME/.local/share/applications" \
         "$HOME/.local/share/icons/hicolor/scalable/apps"
install -m755 "$SRC/fiamma.py" "$DEST/fiamma.py"
install -m644 "$SRC/Faghy.Fiamma.svg" "$DEST/"
install -m644 "$SRC/Faghy.Fiamma.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/"
ln -sf "$DEST/fiamma.py" "$HOME/.local/bin/fiamma"
cat > "$HOME/.local/share/applications/Faghy.Fiamma.desktop" <<DESK
[Desktop Entry]
Name=Fiamma
Comment=Timer di concentrazione con attività e statistiche
Exec=$DEST/fiamma.py
Icon=Faghy.Fiamma
Terminal=false
Type=Application
Categories=Utility;Office;GTK;
Keywords=pomodoro;timer;focus;produttività;
StartupNotify=true
DESK
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo "✔ Fiamma installata. Cercala tra le applicazioni o lancia: fiamma"
