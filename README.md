# Conveyr

A **100% local** file converter for Linux. Converts images, video and audio
directly on your machine using `ffmpeg`, ImageMagick, `potrace` and `librsvg`,
and handles **PDFs** (merge, split, compress, rotate, protect, unlock,
PDF ↔ images, text extraction) via `poppler-utils`, Ghostscript and `qpdf`.
**No cloud, no servers, no uploads** - your files never leave your computer.

Works on Debian/Ubuntu, Fedora/RHEL, Arch (and CachyOS, Manjaro, EndeavourOS)
and openSUSE.

## Features

- **Images**: jpg, png, webp, bmp, tiff, gif and svg
  - Raster → SVG via `potrace` vector tracing (black & white)
  - SVG → raster via `rsvg-convert` (falls back to ImageMagick)
- **Video**: gif, mp4, webm, mkv, avi, mov, mpg
  - GIF → video with proper H.264/VP9 encoding
  - Video → GIF with a quality palette (fps and width are configurable)
- **Audio**: wav, mp3, flac, ogg, m4a, aac, opus
  - Configurable audio bitrate
- **PDF tools** (iLovePDF-style, in the "PDF tools" GUI tab or `conveyr pdf`):
  - **Merge** several PDFs into one, **split** into single pages
  - **Compress** with quality presets (screen / ebook / printer)
  - **Rotate** pages (90/180/270°)
  - **Protect** with a password and **unlock**
  - **PDF ↔ Images** (JPG/PNG) and **PDF → Text**
- Real format detection via **magic bytes** (not just the file extension)
- Never overwrites an existing file unless you ask for `--force`
- Both a **command-line tool** and a **graphical interface** with a proper
  app icon and desktop entry

## Requirements

| Tool | Purpose | Required for |
|------|---------|--------------|
| ffmpeg | audio + video conversion | audio/video |
| ImageMagick (`magick`/`convert`) | image conversion + images → PDF | images, PDF |
| potrace | raster → SVG vector tracing | raster → svg |
| librsvg (`rsvg-convert`) | high-fidelity SVG rendering | svg → raster (optional) |
| poppler-utils (`pdfunite`, `pdfseparate`, `pdftoppm`, `pdftotext`) | merge/split/convert/extract PDFs | PDF tools |
| Ghostscript (`gs`) | PDF compression | PDF compress |
| qpdf | PDF rotation + password protection | PDF rotate/protect/unlock |
| Python 3.9+ | runs the app | everything |

## Install

Run the installer. It detects your distro, installs any missing system
packages, creates an isolated Python environment, adds the commands to
`~/.local/bin`, installs the **Conveyr icon set** and the **desktop entry**:

```bash
./install.sh
```

Or skip the system dependency step if you already have everything installed:

```bash
./install.sh --skip-deps
```

Afterwards you may need to ensure `~/.local/bin` is on your PATH:

```bash
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

### Manual dependency install

If you prefer to install the system tools yourself:

```bash
# Debian / Ubuntu
sudo apt install ffmpeg imagemagick potrace librsvg2-bin python3-venv poppler-utils ghostscript qpdf

# Fedora / RHEL
sudo dnf install ffmpeg-free imagemagick potrace librsvg2-tools poppler-utils ghostscript qpdf

# Arch / CachyOS / Manjaro / EndeavourOS
sudo pacman -S ffmpeg imagemagick potrace librsvg poppler ghostscript qpdf

# openSUSE
sudo zypper install ffmpeg imagemagick potrace librsvg2-tools poppler-tools ghostscript qpdf
```

## Uninstall

```bash
./uninstall.sh
```

This removes the Python environment, the `conveyr` / `conveyr-gui` launchers,
the icons and the desktop entry. Add `--purge-deps` to also remove the system
packages (ffmpeg, imagemagick, potrace):

```bash
./uninstall.sh --purge-deps
```

## Command-line usage

```
conveyr FILE... --to FORMAT [options]
```

### Examples

```bash
# Simple image conversion
conveyr photo.jpg --to png

# Batch conversion into a separate directory
conveyr *.jpg --to webp --out-dir converted/

# Vectorize an image (black & white tracing)
conveyr logo.png --to svg
conveyr logo.png --to svg --threshold 60

# Render an SVG to a raster image
conveyr icon.svg --to png

# Animated GIF to MP4
conveyr animation.gif --to mp4

# Video to GIF (tune fps and width)
conveyr clip.mp4 --to gif --fps 12 --width 640

# Audio conversions
conveyr sound.wav --to mp3
conveyr sound.wav --to mp3 --bitrate 192
conveyr track.mp3 --to flac
conveyr track.m4a --to opus --bitrate 128
```

### PDF tools

```
conveyr pdf TOOL FILE... [options]
```

```bash
# Merge several PDFs into one (order matters)
conveyr pdf merge part1.pdf part2.pdf part3.pdf -o book.pdf

# Split a PDF into one file per page
conveyr pdf split manual.pdf -d pages/

# Compress with a quality preset: screen / ebook / printer
conveyr pdf compress manual.pdf -o manual-small.pdf --preset ebook

# Rotate every page
conveyr pdf rotate scan.pdf -o scan-rotated.pdf --angle 90

# Protect / unlock with a password
conveyr pdf protect invoice.pdf -o invoice-locked.pdf --password secret
conveyr pdf unlock invoice-locked.pdf -o invoice.pdf --password secret

# Render each page to an image
conveyr pdf to-images slides.pdf -d out/ --format png --dpi 150

# Build a PDF from images
conveyr pdf from-images page1.jpg page2.jpg page3.png -o document.pdf

# Extract the text
conveyr pdf to-text report.pdf -o report.txt
```

### Options

| Option | Description |
|--------|-------------|
| `--to FORMAT` | target format (required) |
| `-o, --output PATH` | output path (single input only) |
| `-d, --out-dir DIR` | output directory (default: input directory) |
| `-f, --force` | overwrite existing output files |
| `-q, --quiet` | print only the output paths |
| `--crf N` | video quality, lower = better (default 23) |
| `--bitrate K` | audio bitrate in kbit/s (e.g. `192` or `192k`) |
| `--fps N` | frame rate for GIF output (default 10) |
| `--width N` | width for GIF output (default 480) |
| `--threshold N%` | B/W threshold for raster→SVG (default 50) |
| `--list-formats` | show every supported conversion |

## Supported conversions

```
Images:                 Animated GIF:
  jpg -> png webp bmp tiff gif svg   gif -> png jpg webp bmp tiff svg
  png -> jpg webp bmp tiff gif svg        -> mp4 webm mkv avi mov mpg
  webp -> jpg png bmp tiff gif svg
  bmp -> jpg png webp tiff gif svg  Video:
  tiff -> jpg png webp bmp gif svg   mp4 -> gif webm mkv avi mov mpg
                                      webm -> gif mp4 mkv avi mov mpg
Vector graphics:                     mkv -> gif mp4 webm avi mov mpg
  svg -> png jpg webp bmp tiff gif   avi -> gif mp4 webm mkv mov mpg
                                      mov -> gif mp4 webm mkv avi mpg
Audio:                               mpg -> gif mp4 webm mkv avi mov
  wav -> mp3 flac ogg m4a aac opus
  mp3 -> wav flac ogg m4a aac opus   Run `conveyr --list-formats` for
  flac -> wav mp3 ogg m4a aac opus   the complete list.
  ogg -> wav mp3 flac m4a aac opus
  m4a -> wav mp3 flac ogg aac opus
  aac -> wav mp3 flac ogg m4a opus
  opus -> wav mp3 flac ogg m4a aac
```

## GUI usage

```bash
conveyr-gui
```

The window has two tabs:

**Converter** - converts images, video and audio:

1. Click **Add files...** to select the files to convert. This uses your
   desktop's native file chooser (`kdialog` on KDE, `zenity` on GNOME) and
   falls back to the built-in Tk dialog when neither is installed.
2. The detected source formats are shown next to each file.
3. Pick the **Convert to** target - only valid conversions are offered.
4. Optionally choose an output directory (default: same as the input files).
5. Click **Convert** and watch the log.

Conversions use high-quality defaults automatically (the same defaults as the
CLI). Fine-tuning options such as CRF, bitrate, fps or threshold are available
from the command line for the users who want them.

**PDF tools** - iLovePDF-style operations:

1. Pick a **Tool** from the dropdown (Merge, Split, Compress, Rotate,
   Protect, Unlock, PDF to Images, Images to PDF, PDF to Text).
2. **Add files...** - for Merge/Images to PDF the order in the list is the
   order used in the output.
3. Set the options that appear (compression quality, rotation angle,
   password, image format). Output files are named automatically.
4. Optionally choose an output folder (default: next to the source file).
5. Click **Run** and watch the log.

When you switch tool, the file list is cleared automatically so files from a
previous action never carry over (untick **Clear files when changing tool**
to keep compatible files instead). Run still double-checks that the attached
files fit the selected tool.

Both tabs run in the background, so the window stays responsive. Image and PDF
operations run with a timeout guard, so a stuck backend can never freeze the
app - if something ever takes too long you get a clear error instead of an
endless spinner.

## Logo

The Conveyr logo lives in `assets/logo.svg` (vector source). `install.sh`
renders a PNG icon set from it into `~/.local/share/icons/hicolor/` so the
app shows up properly in your application menu and window titlebar.

## Notes and limitations

- **Raster → SVG is black & white vector tracing** via `potrace`. It works
  great on logos, line art and diagrams. Photographs become stylized B/W
  traces; multi-color tracing is a possible future enhancement. Use the
  `--threshold` option to tune where the B/W cut falls.
- GIF → image conversions use the **first frame** of the animation.
- Audio formats like `m4a`/`aac` are lossy; converting them back to `wav`
  cannot restore the original quality.
- All conversions use sensible defaults, but you can always tweak quality via
  `--crf`, `--bitrate`, `--fps` and `--width`.
- **PDF compress** re-encodes the document with Ghostscript using a preset
  (`screen` is the smallest, `printer` the highest quality). **PDF → images**
  renders every page to a raster image. **PDF → text** extracts the embedded
  text; scanned documents produce empty output unless they contain an OCR
  layer.
- Merging keeps the order you give the files; the same order is used when
  building a PDF from images.

## Troubleshooting

**`conveyr: command not found`** - `~/.local/bin` is not on your PATH.
Add it as shown in the install section.

**`ffmpeg is required for audio/video conversion`** - install the system
packages for your distro (see requirements above) or re-run `./install.sh`.

**`ImageMagick is required for image conversion`** - same as above.

**`potrace is required for raster-to-SVG vector tracing`** - install potrace;
SVG output will not work without it.

**PDF tool reports a missing binary** - install `poppler-utils` (pdfunite,
pdfseparate, pdftotext, pdftoppm), `ghostscript` (gs) and `qpdf` for your
distro, or re-run `./install.sh`.

**SVG rendering looks wrong** - the app prefers `rsvg-convert` (librsvg) for
SVG → raster. Install the librsvg tools for your distro for the best results.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/conveyr --list-formats
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

## License

- Conveyr is released under the **MIT License** — see [`LICENSE`](LICENSE).

Please only convert content you have the rights to. Conveyr is fully offline
and does not collect or transmit any data.