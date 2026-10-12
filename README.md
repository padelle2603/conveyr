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
install. Source lives in `web/`.

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

Download the **AppImage** from [Releases](https://github.com/padelle2603/conveyr/releases):

```bash
chmod +x Conveyr-*-x86_64.AppImage
./Conveyr-*-x86_64.AppImage
```

No installer, no `sudo`, no Python environment: the AppImage carries Python and
Tkinter. To uninstall, delete the file.

### The conversion tools

The AppImage deliberately does **not** bundle ffmpeg, ImageMagick, potrace,
ghostscript, qpdf, poppler or librsvg — those are distro packages. Conveyr
tells you which ones are missing when it starts, and **Install** opens a
terminal with the right command for your distribution.

```bash
./Conveyr-*.AppImage --check-deps      # list what is missing
```

<details><summary>Install them by hand</summary>

| Distribution | Command |
|---|---|
| Debian, Ubuntu, Mint | `sudo apt install ffmpeg imagemagick potrace poppler-utils ghostscript qpdf librsvg2-bin` |
| Fedora, RHEL, CentOS | `sudo dnf install ffmpeg-free imagemagick potrace poppler-utils ghostscript qpdf librsvg2-tools` |
| Arch, CachyOS, Manjaro, EndeavourOS | `sudo pacman -S ffmpeg imagemagick potrace poppler ghostscript qpdf librsvg` |
| openSUSE | `sudo zypper install ffmpeg imagemagick potrace poppler-tools ghostscript qpdf librsvg2-tools` |

</details>

## Usage

```bash
conveyr photo.jpg --to png                      # convert an image
conveyr *.jpg --to webp --out-dir converted/    # batch convert
conveyr clip.mp4 --to gif --fps 12 --width 640  # video to GIF
conveyr track.mp3 --to flac                     # audio
conveyr --list-formats                          # all supported conversions
conveyr --check-update                          # is a newer release out? 0=no 10=yes 1=offline
conveyr --check-deps                            # which tools are missing
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

## License

Released under the **MIT License** — see [`LICENSE`](LICENSE).

Please only convert content you have the rights to. Conveyr does not collect
or transmit your data — the only network call is an anonymous check for a
newer release. See [PRIVACY.md](PRIVACY.md) for exactly what it sends.

*Developed with the assistance of [opencode](https://opencode.ai).*
