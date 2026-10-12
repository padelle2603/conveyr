#!/bin/bash
# Build a portable Conveyr AppImage.
#
# What goes in: CPython, Tkinter and the package. What does NOT: ffmpeg,
# ImageMagick, potrace, ghostscript, qpdf, poppler, librsvg. Those stay distro
# packages — bundling them turns a ~60 MB AppImage into ~400 MB with a pile of
# licence obligations. `conveyr --check-deps` and the GUI status row tell the
# user exactly what to install.
#
# Usage: ./packaging/build-appimage.sh [VERSION]
# Needs: pyinstaller, plus appimagetool (or linuxdeploy) to bake.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

VERSION="${1:-$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)}"
ARCH="${ARCH:-x86_64}"
APPDIR="${APPDIR:-AppDir}"
OUT="Conveyr-v${VERSION}-${ARCH}.AppImage"
BUNDLE="${BUNDLE:-build/appimage}"

command -v pyinstaller >/dev/null 2>&1 || { echo "pip install pyinstaller" >&2; exit 1; }

echo "==> Freezing Conveyr ${VERSION} (Python + Tkinter only)..."
rm -rf "${APPDIR}" "${BUNDLE}"
pyinstaller \
    --noconfirm --clean --onedir \
    --name conveyr \
    --distpath "${BUNDLE}" \
    --workpath "${BUNDLE}/work" \
    --specpath "${BUNDLE}" \
    --paths src \
    --add-data "$(pwd)/assets/icons:assets/icons" \
    --hidden-import conveyr.gui \
    --hidden-import conveyr.pdfgui \
    --hidden-import conveyr.videogui \
    packaging/appimage_entry.py

echo "==> Assembling ${APPDIR}..."
mkdir -p "${APPDIR}/usr/bin" "${APPDIR}/usr/share/doc/conveyr"
cp -r "${BUNDLE}/conveyr"/* "${APPDIR}/usr/bin/"

echo "==> Icons, desktop entry, docs..."
mkdir -p "${APPDIR}/usr/share/icons/hicolor/scalable/apps"
cp assets/icons/conveyr.svg "${APPDIR}/usr/share/icons/hicolor/scalable/apps/conveyr.svg"
for size in 16 22 24 32 48 64 128 256 512; do
    mkdir -p "${APPDIR}/usr/share/icons/hicolor/${size}x${size}/apps"
    cp "assets/icons/conveyr_${size}x${size}.png" \
       "${APPDIR}/usr/share/icons/hicolor/${size}x${size}/apps/conveyr.png"
done
# The GUI looks for <size>.png at the AppImage root first.
for size in 32 48 64 128 256; do
    cp "assets/icons/conveyr_${size}x${size}.png" "${APPDIR}/conveyr_${size}.png"
done
cp packaging/conveyr.desktop "${APPDIR}/conveyr.desktop"
cp README.md LEGAL.md PRIVACY.md "${APPDIR}/usr/share/doc/conveyr/"

# appimagetool looks for the icon named in the desktop entry at the AppDir
# root; the hicolor tree above is for anything that goes through the icon theme.
cp assets/icons/conveyr_256x256.png "${APPDIR}/conveyr.png"
cp assets/icons/conveyr.svg "${APPDIR}/conveyr.svg"

cat > "${APPDIR}/AppRun" <<'RUNNER'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export APPDIR="$HERE"
exec "$HERE/usr/bin/conveyr" "$@"
RUNNER
chmod +x "${APPDIR}/AppRun" "${APPDIR}/usr/bin/conveyr"

echo "==> Smoke test..."
"${APPDIR}/AppRun" --version
# --check-deps: 0 all present, 1 some missing. Either is a working bundle.
"${APPDIR}/AppRun" --check-deps || [ $? -eq 1 ]
# --check-update: 0 current, 10 newer, 1 no release yet / offline.
"${APPDIR}/AppRun" --check-update || [ $? -le 10 ]

echo "==> Baking ${OUT}..."
if command -v appimagetool >/dev/null 2>&1; then
    ARCH="${ARCH}" appimagetool "${APPDIR}" "${OUT}"
else
    command -v linuxdeploy >/dev/null 2>&1 || {
        echo "need appimagetool (https://github.com/AppImage/appimagetool) or linuxdeploy" >&2
        exit 1
    }
    OUTPUT="${OUT}" linuxdeploy --appdir "${APPDIR}" --output appimage
fi

echo "==> Done: ${OUT}"
ls -la "${OUT}"