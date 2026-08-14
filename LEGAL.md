# Legal notes and compliance

This document summarises the legal and licensing situation of Conveyr. It is
provided for information only and is **not legal advice**. For commercial
distribution, professional review of your specific situation is recommended.

## 1. Conveyr license

Conveyr is distributed under the **MIT License** (see [`LICENSE`](LICENSE)).
You are free to use, modify and redistribute it, subject to the copyright
notice and permission notice included in all copies or substantial portions
of the software.

## 2. Dependencies and their licenses

Conveyr does **not** link, embed or copy code from its dependencies. It
invokes them as external command-line programs via subprocess, which means
their licenses do **not** impose any copyleft obligations on Conveyr's own
code.

| Tool | License | Used for |
|------|---------|----------|
| ffmpeg | GPL-3.0-only (this build) | audio/video conversion |
| ImageMagick | ImageMagick License (permissive) | image conversion |
| potrace | GPL-2.0-or-later | raster-to-SVG tracing |
| librsvg (`rsvg-convert`) | LGPL-2.1-or-later | SVG rendering (optional) |

If you redistribute Conveyr together with these tools (for example a bundled
package), the terms of *their* licenses apply to the bundled binaries.

## 3. Patents and codec formats

Conveyr enables encoding to a variety of formats. Some of these formats
involve (or have involved) patents, which are independent of software
copyright and vary by jurisdiction:

- **MP3** — MP3 patents expired in 2017 in the US and earlier in the EU.
  Encoding MP3 is now royalty-free.
- **AAC / M4A** — the last AAC patents expired around 2017. Encoding AAC is
  now royalty-free.
- **H.264 / AVC** (used for MP4, MKV, MOV, AVI) — an active patent pool
  (administered by Access Advance) still licenses H.264 encoders/decoders.
  For **personal, non-commercial use** the practical exposure is negligible.
  If you **distribute Conveyr commercially** or use it to produce content for
  commercial purposes, check the current terms of the H.264 patent pool.
- **H.265 / HEVC** — not used by Conveyr.
- **VP8 / VP9 / Opus / FLAC / WAV / PNG / JPEG / WebP / GIF** — royalty-free
  (the GIF/LZW patent expired in 2003/2004).

In the EU and Italy, patents on software "as such" are not granted
(Art. 52 of the European Patent Convention), so the conversion logic itself
is not patentable or patent-infringing in these jurisdictions.

## 4. Privacy and data protection

Conveyr is fully offline: it performs all conversions on the local machine
and **does not connect to the network, collect telemetry, or process personal
data**. Because no personal data is processed, the EU General Data Protection
Regulation (Regulation (EU) 2016/679) and the Italian Data Protection Code
(Legislative Decree 196/2003, as amended) are **not engaged** by Conveyr
itself.

## 5. Copyright of converted content

Conveyr is a format converter. It does not bypass DRM or access controls.
Users are responsible for converting only content they have the rights to
(e.g. their own creations or content released under a compatible license),
in line with Italian copyright law (Law 633/1941) and EU Directive
2001/29/EC.

## 6. Trademark

"Conveyr" is an invented word. Several unrelated third-party products in
other fields (business-process automation, AI telephony, social platforms)
currently use the name. For non-commercial open-source use the practical risk
is low, but before a commercial launch you should:

- search the **EUIPO** trademark register (eutm.europa.eu),
- search the Italian **UIBM** register,
- consider registering an EU trademark (EUTM) or choosing a more distinctive
  name.

## 7. Disclaimer

This document reflects the author's understanding as of 2026. Patent pools,
licenses and registers change over time. Verify the current status before
making legal or commercial decisions.
