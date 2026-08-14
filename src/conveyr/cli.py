"""Command-line interface for Conveyr."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .backends import BackendError
from .core import (
    CATEGORY,
    CATEGORY_LABELS,
    convert,
    detect,
    list_formats,
    valid_targets,
)
from .pdf import (
    COMPRESS_PRESETS,
    IMAGE_FORMATS,
    ROTATE_ANGLES,
    run_tool,
)

BANNER = r"""
   ____                            __
  / __/__  __ _  ___ ___   __ ____/ /__ ____ ____
 / _// _ \/  ' \/ -_) _ \ / // / _  / -_) __/ __/
/_/  \___/_/_/_/\__/_//_/ \_,_/\_,_/\__/_/  \__/
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="conveyr",
        description=(
            "Conveyr - local file converter for images, video and audio.\n"
            "Everything runs on this machine - no cloud, no servers."
        ),
        epilog=(
            "Examples:\n"
            "  conveyr photo.jpg --to png\n"
            "  conveyr logo.png --to svg --threshold 60\n"
            "  conveyr anim.gif --to mp4\n"
            "  conveyr video.mp4 --to gif --fps 12 --width 640\n"
            "  conveyr sound.wav --to mp3 --bitrate 192\n"
            "  conveyr *.jpg --to webp --out-dir converted/"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files", nargs="*", metavar="FILE", help="input file(s) to convert"
    )
    parser.add_argument(
        "--to", "-t", metavar="FORMAT", default=None,
        help="target format (see --list-formats)",
    )
    parser.add_argument(
        "-o", "--output", metavar="PATH",
        help="output file path (only valid with a single input)",
    )
    parser.add_argument(
        "-d", "--out-dir", metavar="DIR",
        help="directory for output files (default: input directory)",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite existing output files"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="suppress progress output"
    )
    parser.add_argument(
        "--crf", type=int, default=None,
        help="video quality for H.264/VP9 encodes, lower is better (default 23)",
    )
    parser.add_argument(
        "--bitrate", metavar="K", default=None,
        help="audio bitrate in kbit/s, e.g. 192 or 192k",
    )
    parser.add_argument(
        "--fps", type=int, default=10, help="frame rate for GIF output (default 10)"
    )
    parser.add_argument(
        "--width", type=int, default=480,
        help="width for GIF output, height follows aspect (default 480)",
    )
    parser.add_argument(
        "--threshold", type=int, default=50,
        help="black/white threshold in %% for raster-to-SVG tracing (default 50)",
    )
    parser.add_argument(
        "--list-formats", action="store_true", help="show all supported conversions and exit"
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}{BANNER}",
    )
    return parser


def _print_formats() -> None:
    print(BANNER.strip("\n"))
    by_category: dict[str, list[str]] = {}
    for ext, targets in list_formats().items():
        cat = CATEGORY_LABELS.get(CATEGORY.get(ext, ""), "")
        by_category.setdefault(cat, []).append((ext, targets))

    for category, entries in by_category.items():
        print(f"{category}:")
        for ext, targets in entries:
            print(f"  {ext:6s} -> {' '.join(targets)}")
        print()


# --------------------------------------------------------------------------- #
# PDF tools (conveyr pdf ...)
# --------------------------------------------------------------------------- #


def _add_pdf_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument(
        "-o", "--output", metavar="PATH", help="output file path"
    )
    sp.add_argument(
        "-d", "--out-dir", metavar="DIR",
        help="directory for output files (default: input directory)",
    )
    sp.add_argument(
        "-f", "--force", action="store_true", help="overwrite existing output files"
    )
    sp.add_argument(
        "-q", "--quiet", action="store_true", help="print only the output paths"
    )


def _build_pdf_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="conveyr pdf",
        description=(
            "PDF tools for Conveyr - everything runs locally.\n"
            "Available: merge, split, compress, rotate, protect, unlock, "
            "to-images, from-images, to-text"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="tool", required=True, metavar="TOOL")

    merge = sub.add_parser("merge", help="merge PDFs into one file")
    _add_pdf_common(merge)
    merge.add_argument("files", nargs="+", metavar="PDF", help="PDFs to merge, in order")

    split = sub.add_parser("split", help="split a PDF into one file per page")
    _add_pdf_common(split)
    split.add_argument("file", metavar="PDF")

    compress = sub.add_parser("compress", help="reduce PDF size with a quality preset")
    _add_pdf_common(compress)
    compress.add_argument("file", metavar="PDF")
    compress.add_argument(
        "--preset", choices=COMPRESS_PRESETS, default="ebook",
        help="quality preset: screen (smallest), ebook, printer (best) (default: ebook)",
    )

    rotate = sub.add_parser("rotate", help="rotate every page of a PDF")
    _add_pdf_common(rotate)
    rotate.add_argument("file", metavar="PDF")
    rotate.add_argument(
        "--angle", choices=ROTATE_ANGLES, default="90",
        help="clockwise rotation in degrees (default: 90)",
    )

    protect = sub.add_parser("protect", help="lock a PDF with a password")
    _add_pdf_common(protect)
    protect.add_argument("file", metavar="PDF")
    protect.add_argument("--password", required=True, help="password to protect the PDF")

    unlock = sub.add_parser("unlock", help="remove the password protection of a PDF")
    _add_pdf_common(unlock)
    unlock.add_argument("file", metavar="PDF")
    unlock.add_argument(
        "--password", default="", help="password of the PDF, if it has one"
    )

    to_images = sub.add_parser("to-images", help="render a PDF to one image per page")
    _add_pdf_common(to_images)
    to_images.add_argument("file", metavar="PDF")
    to_images.add_argument(
        "--format", choices=IMAGE_FORMATS, default="png",
        help="image format (default: png)",
    )
    to_images.add_argument(
        "--dpi", type=int, default=150, help="resolution in DPI (default: 150)"
    )

    from_images = sub.add_parser("from-images", help="combine images into a PDF")
    _add_pdf_common(from_images)
    from_images.add_argument("files", nargs="+", metavar="IMG", help="images, in order")

    to_text = sub.add_parser("to-text", help="extract the plain text of a PDF")
    _add_pdf_common(to_text)
    to_text.add_argument("file", metavar="PDF")

    return parser


def _pdf_main(argv: list[str]) -> int:
    parser = _build_pdf_parser()
    args = parser.parse_args(argv)

    opts = {
        "force": args.force,
        "quiet": args.quiet,
        "preset": getattr(args, "preset", None),
        "angle": getattr(args, "angle", None),
        "format": getattr(args, "format", None),
        "dpi": getattr(args, "dpi", None),
        "password": getattr(args, "password", None),
    }

    if args.tool in ("merge", "from-images"):
        paths = list(args.files)
    else:
        paths = [args.file]

    try:
        results = run_tool(
            args.tool, paths, args.output, args.out_dir, opts
        )
    except (BackendError, ValueError, OSError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if isinstance(results, list):
        for item in results:
            print(item)
    else:
        print(results)
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "pdf":
        return _pdf_main(argv[1:])

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_formats:
        _print_formats()
        return 0

    if not args.files:
        parser.error("the following arguments are required: FILE")
    if not args.to:
        parser.error("the following arguments are required: --to")

    target = args.to.lower().lstrip(".")
    from .core import canonical, is_supported

    target = canonical(target)
    if not is_supported(target):
        parser.error(f"unsupported target format: {args.to} (see --list-formats)")

    if len(args.files) > 1 and args.output:
        parser.error("--output can only be used with a single input file")

    if args.out_dir:
        Path(args.out_dir).mkdir(parents=True, exist_ok=True)

    failures = 0
    for file in args.files:
        if not Path(file).is_file():
            print(f"skip: {file}: not a regular file")
            failures += 1
            continue

        src = detect(file)
        if not src:
            print(f"skip: {file}: unrecognized or unsupported format")
            failures += 1
            continue

        if target not in valid_targets(src):
            print(
                f"skip: {file}: cannot convert {src} to {target} "
                f"(supported: {' '.join(valid_targets(src))})"
            )
            failures += 1
            continue

        opts = {
            "output": args.output if len(args.files) == 1 else None,
            "out_dir": args.out_dir,
            "force": args.force,
            "quiet": args.quiet,
            "crf": args.crf,
            "bitrate": args.bitrate,
            "fps": args.fps,
            "width": args.width,
            "threshold": args.threshold,
        }

        try:
            out = convert(file, src, target, opts)
        except FileExistsError as exc:
            print(f"skip: {file}: {exc}")
            failures += 1
            continue
        except (BackendError, ValueError, OSError) as exc:
            print(f"error: {file}: {exc}")
            failures += 1
            continue

        if args.quiet:
            print(out)
        else:
            print(f"ok: {file} ({src}) -> {out}")

    if failures:
        print(f"\n{failures} file(s) failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())