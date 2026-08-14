# Conveyr

A **100% local** file converter for Linux. Converts images, video, audio and
PDFs directly on your machine using `ffmpeg`, ImageMagick, `potrace`,
`librsvg`, `poppler-utils`, Ghostscript and `qpdf`.
**No cloud, no servers, no uploads** — your files never leave your computer.

Works on Debian/Ubuntu, Fedora/RHEL, Arch (and CachyOS, Manjaro, EndeavourOS)
and openSUSE.

## Web version

A fully in-browser version (WebAssembly) runs at
**https://padelle2603.github.io/conveyr/** — same conversions, nothing to
install.

## Features

- **Images**: jpg, png, webp, bmp, tiff, gif, svg — including raster→SVG
  tracing via `potrace` and SVG→raster rendering
- **Video**: gif, mp4, webm, mkv, avi, mov, mpg — GIF↔video with quality
  palette and configurable fps/width
- **Audio**: wav, mp3, flac, ogg, m4a, aac, opus — configurable bitrate
- **PDF tools**: merge, split, compress, rotate, protect, unlock,
  PDF↔images, text extraction
- Real format detection via **magic bytes**
- Never overwrites existing files unless you ask for `--force`
- Both a **CLI** and a **GUI** with app icon and desktop entry

## Install

```bash
./install.sh                    # detects distro, installs deps, sets up
./install.sh --skip-deps        # if the system tools are already installed
```

This creates an isolated Python environment, adds `conveyr` / `conveyr-gui` to
`~/.local/bin` and installs the icon set and desktop entry. Ensure
`~/.local/bin` is on your PATH:

```bash
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc && source ~/.bashrc
```

To uninstall: `./uninstall.sh` (add `--purge-deps` to also remove the system
packages).

## Usage

```bash
conveyr photo.jpg --to png                      # convert an image
conveyr *.jpg --to webp --out-dir converted/    # batch convert
conveyr clip.mp4 --to gif --fps 12 --width 640  # video to GIF
conveyr track.mp3 --to flac                     # audio
conveyr --list-formats                          # all supported conversions
```

PDF tools:

```bash
conveyr pdf merge part1.pdf part2.pdf -o book.pdf
conveyr pdf split manual.pdf -d pages/
conveyr pdf compress manual.pdf --preset ebook
conveyr pdf rotate scan.pdf --angle 90
conveyr pdf protect invoice.pdf --password secret
conveyr pdf to-images slides.pdf -d out/ --format png
conveyr pdf to-text report.pdf -o report.txt
```

Key options: `--to FORMAT` (required), `-o/--output`, `-d/--out-dir`,
`-f/--force`, `-q/--quiet`, `--crf N`, `--bitrate K`, `--fps N`, `--width N`,
`--threshold N%`, `--list-formats`.

## GUI

Run `conveyr-gui`. Two tabs: **Converter** (images/video/audio) and
**PDF tools**. Add files, pick a target or tool, click **Convert**/**Run** —
operations run in the background with a timeout guard so the window never
freezes. Only valid conversions are offered based on detected source formats.

## Notes

- Raster→SVG is black & white vector tracing; photographs become stylized B/W
  traces (tune with `--threshold`)
- GIF→image conversions use the first frame
- PDF compress re-encodes the document (text becomes non-selectable); PDF→text
  extracts embedded text only (scanned pages need an OCR layer)

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/conveyr --list-formats
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

## License

Released under the **MIT License** — see [`LICENSE`](LICENSE).

Please only convert content you have the rights to. Conveyr is fully offline
and does not collect or transmit any data.