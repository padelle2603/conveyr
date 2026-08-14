#!/usr/bin/env bash
#
# Uninstall Conveyr.
#
# Usage:
#   ./uninstall.sh            # remove the Python app + launchers + icons + desktop entry
#   ./uninstall.sh --purge-deps   # also remove ffmpeg/imagemagick/potrace + PDF tools
#
# The virtual environment is simply deleted, so this never touches your
# system Python.

set -euo pipefail

APP_NAME="conveyr"
VENV_DIR="${VENV_DIR:-$HOME/.local/share/conveyr/venv}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
PURGE_DEPS=0

for arg in "$@"; do
    case "$arg" in
        --purge-deps) PURGE_DEPS=1 ;;
        -h|--help)
            echo "Usage: $0 [--purge-deps]"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
apps_dir="$data_dir/applications"
icon_dir="$data_dir/icons/hicolor"

echo "[app] removing launchers from $BIN_DIR"
rm -f "$BIN_DIR/conveyr" "$BIN_DIR/conveyr-gui"

echo "[app] removing virtual environment $VENV_DIR"
rm -rf "$VENV_DIR"
rmdir "$(dirname "$VENV_DIR")" 2>/dev/null || true

echo "[app] removing desktop entry from $apps_dir"
rm -f "$apps_dir/$APP_NAME.desktop"

echo "[app] removing icons from $icon_dir"
rm -f "$icon_dir/scalable/apps/$APP_NAME.svg"
for size in 16 22 24 32 48 64 128 256 512; do
    rm -f "$icon_dir/${size}x${size}/apps/$APP_NAME.png"
done
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$icon_dir" >/dev/null 2>&1 || true
fi

if [ "$PURGE_DEPS" -eq 1 ]; then
    echo "[deps] purging system packages"
    local sudo_cmd="sudo"
    if [ "$(id -u)" -eq 0 ]; then
        sudo_cmd=""
    fi
    if command -v apt-get >/dev/null 2>&1; then
        $sudo_cmd apt-get purge -y ffmpeg imagemagick potrace librsvg2-bin poppler-utils ghostscript qpdf
    elif command -v dnf >/dev/null 2>&1; then
        $sudo_cmd dnf remove -y ffmpeg-free imagemagick potrace librsvg2-tools poppler-utils ghostscript qpdf
    elif command -v pacman >/dev/null 2>&1; then
        $sudo_cmd pacman -R --noconfirm ffmpeg imagemagick potrace librsvg poppler ghostscript qpdf
    elif command -v zypper >/dev/null 2>&1; then
        $sudo_cmd zypper remove -y ffmpeg imagemagick potrace librsvg2-tools poppler-tools ghostscript qpdf
    else
        echo "[deps] unsupported package manager; remove packages manually" >&2
    fi
fi

echo "Done. $APP_NAME has been removed."