# Privacy Policy — Conveyr

_Last updated: 16 August 2026_

> **Disclaimer.** This policy may be updated from time to time. The current
> version is the one published in this document.

This policy describes how Conveyr handles data when you use it. The short
answer is: **Conveyr is fully offline. It does not collect, store, or transmit
your data. Your files never leave your device.**

## 1. Where your data stays

Conveyr converts your files **locally**:

- **Desktop (Linux)**: conversion runs on your machine using standard system
  tools (ffmpeg, ImageMagick, Ghostscript, qpdf, poppler-utils, etc.). Your
  input files are read directly from disk, processed, and the converted output
  is written next to the source file (or to the `--out-dir` you choose).
- **Web**: conversion runs **inside your browser** using WebAssembly engines
  bundled with the static site itself. Your files are read through the browser
  File API, processed in memory, and the results are downloaded back to you.

In both cases the files being converted **never leave your device**. Conveyr
has **no server, no backend, no cloud, no database**: there is no machine
listening for connections and no service to which your data could be sent.

## 2. Data processed

Conveyr processes **only the files you select** and only for the duration of a
conversion:

- **Input files**: read from disk (desktop) or from the File API (web) solely
  to be converted.
- **Converted output**: written locally (desktop) or downloaded to your browser
  (web), then discarded from memory.
- **Temporary files** (desktop): Conveyr may create small temporary files
  during conversion (e.g. intermediate `.pbm` for tracing, `.png` for SVG
  rendering). These are deleted automatically when the conversion finishes.

Conveyr does **not** collect, store, index, cache or retain:

- the contents of your files;
- file names, paths or metadata;
- your identity, IP address, or usage activity.

## 3. Persistent storage

Conveyr keeps **no persistent personal data**:

- **Desktop**: no configuration file, no database, no logs, no cache of your
  files. The only things written to your system are the output files you
  request and the application itself (its virtual environment and launchers
  under `~/.local` when installed via `install.sh`).
- **Web**: the web build uses **no** `localStorage`, `sessionStorage` or
  `IndexedDB`. Nothing is stored between sessions.

## 4. Network access

Conveyr performs **no tracking, analytics, telemetry or advertising** of any
kind.

The **desktop** build has **no network code at all**: it makes no outgoing
requests. The only external interaction is optional: the `install.sh` script
may invoke the system package manager (apt/dnf/pacman/zypper) to install the
conversion tools, which connects to your distribution's own repositories.

The **web** build is a static site (hosted on GitHub Pages). The only network
requests it makes are **same-origin fetches of the bundled engines** (the
WebAssembly binaries for ffmpeg, ImageMagick, potrace and the PDF tools) on
first use. These are assets of the site itself, loaded from the same origin;
they do not contain or transmit any of your data. There is no cross-origin
call to a Conveyr server because no such server exists.

## 5. Permissions

Conveyr requests **no special permissions**:

- **Desktop**: Conveyr reads and writes only the files you choose, and executes
  the system conversion tools. The `install.sh` installer invokes `sudo` only
  to install system packages if you opt in; the application itself never runs
  with elevated privileges.
- **Web**: Conveyr uses the browser File API (`<input type=file>` and
  drag-and-drop). No other browser permission is requested.

## 6. Third parties

Conveyr relies on **no third-party data services** and transmits your data to
**no one**. The only third-party components are the conversion engines
themselves:

- **Desktop**: system tools installed on your machine (ffmpeg, ImageMagick,
  Ghostscript, qpdf, poppler-utils, potrace), invoked as separate local
  processes. They process your files locally and send nothing anywhere.
- **Web**: WebAssembly engines bundled inside the static site itself. They run
  in your browser and never contact any server.

The static web build is **served by GitHub Pages** (the host of the website).
As with any website you visit, GitHub's servers may observe routine connection
data (e.g. your IP address) in accordance with GitHub's own privacy practices.
Conveyr itself does not collect this data and does not configure any analytics.

## 7. Backup and data export

Conveyr does **not** create backups, exports or copies of your files. The only
output is the converted file you explicitly request.

## 8. Children's privacy

Conveyr is a general-purpose file utility; it does not target children and does
not collect any personal data from any user, regardless of age.

## 9. Good faith

Conveyr is designed and maintained in good faith around one principle: **your
files are yours and never leave your device**. It collects nothing, tracks
nothing, and has no business model based on your data. For the legal
assessment of the tool, its dependencies and the responsibility of the user for
converted content, see **[LEGAL.md](LEGAL.md)**.