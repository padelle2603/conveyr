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
    --add-data "$(pwd)/packaging/servicemenus:packaging/servicemenus" \
    --hidden-import conveyr.gui \
    --hidden-import conveyr.pdfgui \
    --hidden-import conveyr.videogui \
    --hidden-import conveyr.fm_progress \
    --hidden-import conveyr.menus \
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
mkdir -p "${APPDIR}/usr/share/kio/servicemenus"
cp packaging/servicemenus/*.desktop "${APPDIR}/usr/share/kio/servicemenus/"
cp README.md LEGAL.md PRIVACY.md "${APPDIR}/usr/share/doc/conveyr/"

# The CA store ships with the app. The frozen libcrypto cannot be relied on to
# find the host's: with it missing, TLS verification fails with "unable to get
# local issuer certificate" and the release check reports itself as offline.
# An AppImage that cannot verify TLS cannot check for updates.
CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
[ -f "$CA_BUNDLE" ] || CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt
[ -f "$CA_BUNDLE" ] || { echo "no CA bundle found; the AppImage would fail TLS" >&2; exit 1; }
mkdir -p "${APPDIR}/usr/share/ca-certificates"
cp "$CA_BUNDLE" "${APPDIR}/usr/share/ca-certificates/ca-certificates.crt"

# appimagetool looks for the icon named in the desktop entry at the AppDir
# root; the hicolor tree above is for anything that goes through the icon theme.
cp assets/icons/conveyr_256x256.png "${APPDIR}/conveyr.png"
cp assets/icons/conveyr.svg "${APPDIR}/conveyr.svg"

cat > "${APPDIR}/AppRun" <<'RUNNER'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export APPDIR="$HERE"
export SSL_CERT_FILE="$HERE/usr/share/ca-certificates/ca-certificates.crt"
export GIT_SSL_CAINFO="$SSL_CERT_FILE"
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