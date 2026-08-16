# Legal Notice — Conveyr

_Last updated: 16 August 2026_

> **Disclaimer.** This document is provided for **informational purposes only**
> and **does not constitute legal advice**. It was not drafted by a lawyer or a
> qualified professional: the author of this document is not a legal
> practitioner. The assessments contained here are based on a reasoned
> interpretation of the applicable law and may therefore be **revised**, updated
> or corrected at any time. For binding opinions or for specific issues
> (liability, jurisdiction, commercial use) consult a qualified professional.

## 1. Premise

Conveyr is a **local file converter** for images, video, audio and PDF. It runs
entirely on the user's own machine (Linux desktop) or in the user's own browser
(the web build), and it is explicitly designed around the principle of
**local processing**: "no cloud, no servers, no uploads". The project is open
source, licensed under the **MIT License**, and is developed and distributed in
**good faith** as a general-purpose utility.

## 2. What Conveyr does — and what it does not do

Conveyr converts files between common formats:

- **Images**: jpg, png, webp, bmp, tiff, gif, svg (including raster-to-SVG
  tracing and SVG-to-raster rendering);
- **Video**: gif, mp4, webm, mkv, avi, mov, mpg (GIF-to-video and
  video-to-GIF, with configurable frame rate, width and quality);
- **Audio**: wav, mp3, flac, ogg, m4a, aac, opus (configurable bitrate);
- **PDF**: merge, split, compress, rotate, protect (encrypt), unlock
  (decrypt), PDF-to-image and image-to-PDF, text extraction.

Conveyr is a **neutral tool**. It does **not**:

- host, embed or index any content;
- stream, broadcast or make content publicly available;
- scrape, mine or download content from the internet;
- circumvent any technological protection measure or DRM.

It simply transforms the files that the user selects, on the device where it
runs. It refuses to overwrite existing files unless explicitly told to do so
(`--force`), a deliberate safeguard against accidental data loss.

## 3. How conversion works

On the **desktop**, Conveyr orchestrates standard system tools as separate
processes (`ffmpeg`, ImageMagick, `potrace`, Ghostscript, `qpdf`,
poppler-utils). These are invoked with `subprocess` and never via a shell;
Conveyr adds no third-party Python runtime dependencies.

In the **web** build, the same engines are compiled to WebAssembly and bundled
with the static site itself (no CDN). All processing happens inside the user's
browser session.

In both cases the conversion happens **on the user's machine and only on the
user's machine**: the files being converted are not sent anywhere.

## 4. Copyright and responsibility for converted content

Conveyr can transcode audio and video (for example with the H.264, VP9, AAC,
MP3, Opus, FLAC, WAV or MPEG-2 codecs) and can extract or render PDF content.
This capability is a generic, format-agnostic utility: the same tool can encode
a home video, a presentation you authored, or — if misused — content you do not
own. **What you convert is your responsibility.**

The copyright framework at the international, European and national level
sanctions those who **reproduce, distribute or communicate to the public**
protected works without authorization. A local conversion tool that transforms
files on the user's own device does not itself perform any of those acts:
converting a file you lawfully possess, for personal use, is a neutral
operation. If you convert content you are not entitled to convert, the
responsibility is yours alone, under the laws of your country.

Conveyr does not, and cannot, know the provenance of the files it converts.
It is built in good faith: the README explicitly asks users to **only convert
content they have the rights to**.

## 5. Licensing and dependencies

Conveyr itself is released under the **MIT License**, Copyright (c) 2026
Conveyr contributors.

The desktop build **invokes** external programs as separate processes rather
than linking them. This is an aggregation, not a derivative work: the GPL and
AGPL licensing of some of those tools (e.g. ffmpeg, Ghostscript, potrace,
poppler-utils) applies to those programs themselves and does not impose copyleft
obligations on Conveyr's own MIT-licensed code, which remains independent.

The web build **bundles** the engines as WebAssembly. In this distribution the
bundled libraries keep their own licenses (notably `@ffmpeg/core`, which is
GPL-2.0-or-later, and `esm-potrace-wasm`, which is GPL-2.0, alongside
Apache-2.0 and MIT components). Users and redistributors of the web build
should be aware of these third-party license obligations, which govern those
libraries in accordance with their respective terms.

## 6. Patents

Conveyr relies on encoders and decoders provided by the underlying tools.
Relevant patent situation, in good-faith summary:

- **MP3** and **AAC**: patent licensing for these codecs has been effectively
  royalty-free since approximately 2017 (the relevant patent pools expired or
  ended their licensing programs);
- **H.264/AVC**: patent licensing is administered by patent pools such as Access
  Advance; licensing may apply for commercial or broadcasting uses;
- **VP8, VP9, Opus, FLAC, WAV**: royalty-free codecs, no patent licensing
  required for use.

Conveyr does not sell or distribute encoded content; the codec question, where
relevant, concerns the user's own use of the output files and is governed by the
applicable laws and license terms of each codec.

## 7. No liability for third-party content

Conveyr does not fetch, index, host or recommend any content. It is a local
transformation tool. The author therefore accepts **no responsibility** for the
content of the files a user chooses to convert, for the legality of the source
files, or for the use the user makes of the output. Any dispute regarding
converted content concerns the user and the relevant rights holders, not
Conveyr.

## 8. Good faith

Conveyr is developed and published in good faith as a legitimate, general-purpose
utility:

- it performs a standard, openly documented function (format conversion);
- it processes files only on the device of the user;
- it transmits nothing, collects nothing and tracks nothing (see
  [PRIVACY.md](PRIVACY.md));
- it explicitly asks users to convert only content they have rights to;
- it has no feature whose purpose or effect is to bypass protections,
  monetization systems or access controls.