#!/usr/bin/env bash
#
# Install Conveyr and its system dependencies.
#
# Usage:
#   ./install.sh                # detect distro, install deps + app
#   ./install.sh --skip-deps    # only install the Python app
#
# The Python app is installed into a dedicated virtual environment at
# ~/.local/share/conveyr/venv and symlinked into ~/.local/bin, so there are
# no pip/PEP 668 conflicts with your system Python. A desktop entry and the
# Conveyr icon set are installed under ~/.local/share.

set -euo pipefail

APP_NAME="conveyr"
VENV_DIR="${VENV_DIR:-$HOME/.local/share/conveyr/venv}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
SKIP_DEPS=0

for arg in "$@"; do
    case "$arg" in
        --skip-deps) SKIP_DEPS=1 ;;
        -h|--help)
            echo "Usage: $0 [--skip-deps]"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

detect_package_manager() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "apt"; return
    fi
    if command -v dnf >/dev/null 2>&1; then
        echo "dnf"; return
    fi
    if command -v pacman >/dev/null 2>&1; then
        echo "pacman"; return
    fi
    if command -v zypper >/dev/null 2>&1; then
        echo "zypper"; return
    fi
    echo ""
}

install_system_deps() {
    local pm="$1"
    local sudo_cmd="sudo"
    if [ "$(id -u)" -eq 0 ]; then
        sudo_cmd=""
    fi

    local missing=()
    for bin in ffmpeg magick convert potrace gs qpdf \
               pdfunite pdfseparate pdftotext pdftoppm; do
        if ! command -v "$bin" >/dev/null 2>&1; then
            missing+=("$bin")
        fi
    done

    local python_venv_ok
    python_venv_ok=0
    if python3 -m venv --help >/dev/null 2>&1; then
        python_venv_ok=1
    fi
    if [ "$python_venv_ok" -eq 0 ]; then
        missing+=("python3-venv")
    fi

    if [ "${#missing[@]}" -eq 0 ]; then
        echo "[deps] all required tools are already installed"
        return 0
    fi

    echo "[deps] installing: ${missing[*]} (via $pm)"
    case "$pm" in
        apt)
            $sudo_cmd apt-get update
            $sudo_cmd apt-get install -y ffmpeg imagemagick potrace python3-venv poppler-utils ghostscript qpdf
            ;;
        dnf)
            $sudo_cmd dnf install -y ffmpeg-free imagemagick potrace python3 poppler-utils ghostscript qpdf
            ;;
        pacman)
            $sudo_cmd pacman -S --needed --noconfirm ffmpeg imagemagick potrace poppler ghostscript qpdf
            ;;
        zypper)
            $sudo_cmd zypper install -y ffmpeg imagemagick potrace python3 poppler-tools ghostscript qpdf
            ;;
        *)
            echo "[deps] unsupported package manager; install ffmpeg, imagemagick, potrace, poppler-utils, ghostscript and qpdf manually" >&2
            ;;
    esac

    # Optional: librsvg for higher-fidelity SVG rendering.
    case "$pm" in
        apt)    $sudo_cmd apt-get install -y librsvg2-bin  >/dev/null 2>&1 || true ;;
        dnf)    $sudo_cmd dnf install -y librsvg2-tools   >/dev/null 2>&1 || true ;;
        pacman) $sudo_cmd pacman -S --needed --noconfirm librsvg >/dev/null 2>&1 || true ;;
        zypper) $sudo_cmd zypper install -y librsvg2-tools >/dev/null 2>&1 || true ;;
    esac
}

cleanup_legacy() {
    # Remove leftover artifacts from the previous "file-converter" brand.
    local data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
    local apps_dir="$data_dir/applications"
    local icon_dir="$data_dir/icons/hicolor"

    rm -f "$BIN_DIR/file-convert" "$BIN_DIR/file-convert-gui"
    rm -f "$apps_dir/file-converter.desktop"
    rm -f "$icon_dir/scalable/apps/file-converter.svg"
    for size in 16 22 24 32 48 64 128 256 512; do
        rm -f "$icon_dir/${size}x${size}/apps/file-converter.png"
    done
    if [ -e "$HOME/.local/share/file-converter" ]; then
        rm -rf "$HOME/.local/share/file-converter"
    fi
}

install_python_app() {
    echo "[app] creating virtual environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
    echo "[app] installing $APP_NAME"
    "$VENV_DIR/bin/pip" install --no-cache-dir "$SCRIPT_DIR"

    mkdir -p "$BIN_DIR"
    ln -sf "$VENV_DIR/bin/conveyr"     "$BIN_DIR/conveyr"
    ln -sf "$VENV_DIR/bin/conveyr-gui" "$BIN_DIR/conveyr-gui"

    echo "[app] created launchers in $BIN_DIR"
    if ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
        echo "[app] note: add $BIN_DIR to your PATH, e.g.:"
        echo "  echo 'export PATH=\"\$PATH:$BIN_DIR\"' >> ~/.bashrc"
    fi

    install_icons
    install_desktop_entry
}

install_icons() {
    local icons_src="$SCRIPT_DIR/assets/icons"
    if [ ! -d "$icons_src" ]; then
        echo "[icons] source icons not found at $icons_src (skipping)"
        return 0
    fi

    local data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
    local icon_dir="$data_dir/icons/hicolor"
    local png dest size

    mkdir -p "$icon_dir/scalable/apps"
    cp "$icons_src/$APP_NAME.svg" "$icon_dir/scalable/apps/$APP_NAME.svg"

    for png in "$icons_src"/"$APP_NAME"_*.png; do
        [[ "$(basename "$png")" =~ ^"$APP_NAME"_([0-9]+)x[0-9]+\.png$ ]] || continue
        size="${BASH_REMATCH[1]}"
        dest="$icon_dir/${size}x${size}/apps"
        mkdir -p "$dest"
        cp "$png" "$dest/$APP_NAME.png"
    done

    echo "[icons] installed Conveyr icons into $icon_dir"
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "$icon_dir" >/dev/null 2>&1 || true
    fi
}

install_desktop_entry() {
    local data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
    local apps_dir="$data_dir/applications"
    local desktop_file="$apps_dir/$APP_NAME.desktop"
    mkdir -p "$apps_dir"

    cat > "$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Conveyr
GenericName=File Converter
Comment=Convert images, video and audio locally - no cloud, no servers
Exec=$BIN_DIR/conveyr-gui
Icon=$APP_NAME
Terminal=false
Categories=Utility;Graphics;AudioVideo;
Keywords=convert;converter;conveyr;image;video;audio;svg;png;jpg;mp3;mp4;pdf;merge;split;local;
StartupNotify=true
EOF

    echo "[app] created desktop entry: $desktop_file"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$apps_dir" >/dev/null 2>&1 || true
    fi
}

main() {
    local pm
    pm="$(detect_package_manager)"

    cleanup_legacy

    if [ "$SKIP_DEPS" -eq 0 ]; then
        if [ -z "$pm" ]; then
            echo "[deps] could not detect a package manager; use --skip-deps after installing tools manually" >&2
        else
            install_system_deps "$pm"
        fi
    fi

    install_python_app

    echo
    echo "Done. Try:"
    echo "  conveyr --list-formats"
    echo "  conveyr photo.jpg --to png"
    echo "  conveyr-gui"
}

main "$@"
