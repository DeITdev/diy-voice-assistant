#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Consolidate branch-isolated progress fragments into context/progress-tracker.md."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

COMPLETED_HEADING_RE = re.compile(r"^## Completed[ \t]*$", re.MULTILINE)


def collect_fragments(progress_dir: Path) -> list[tuple[Path, str]]:
    """Return sorted non-empty top-level Markdown fragments in ``progress_dir``."""
    if not progress_dir.exists():
        return []

    fragments: list[tuple[Path, str]] = []
    for entry in sorted(progress_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_file():
            continue
        if entry.name.startswith(".") or entry.suffix.lower() != ".md":
            continue
        content = entry.read_text(encoding="utf-8").strip()
        if not content:
            continue
        fragments.append((entry, content))
    return fragments


def build_insertion_block(fragments: list[tuple[Path, str]]) -> str:
    """Format fragments with source markers for insertion under ``## Completed``."""
    sections = [f"<!-- From {path.name} -->\n{content}" for path, content in fragments]
    return "\n\n".join(sections)


def insert_under_completed(tracker_text: str, insertion_block: str) -> str:
    """Prepend ``insertion_block`` directly beneath the ``## Completed`` heading."""
    match = COMPLETED_HEADING_RE.search(tracker_text)
    if match is None:
        msg = "Target tracker file is missing a '## Completed' heading."
        raise ValueError(msg)

    heading_end = match.end()
    before = tracker_text[:heading_end]
    after = tracker_text[heading_end:].lstrip("\r\n")
    if after:
        return f"{before}\n\n{insertion_block}\n\n{after}"
    return f"{before}\n\n{insertion_block}\n"


def archive_fragments(
    fragments: list[tuple[Path, str]],
    archive_dir: Path,
    *,
    delete: bool,
    timestamp: str,
) -> list[Path]:
    """Archive processed fragments into ``archive_dir`` or delete them."""
    destinations: list[Path] = []
    if not delete:
        archive_dir.mkdir(parents=True, exist_ok=True)

    for path, _ in fragments:
        if delete:
            path.unlink()
        else:
            dest = archive_dir / f"{path.stem}-{timestamp}.md"
            shutil.move(str(path), str(dest))
            destinations.append(dest)
    return destinations


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Consolidate context/progress/*.md fragments into context/progress-tracker.md.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files or moving fragments.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete processed fragment files instead of moving them to context/progress/archive/.",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("context/progress-tracker.md"),
        help="Target tracker file (default: context/progress-tracker.md).",
    )
    parser.add_argument(
        "--progress-dir",
        type=Path,
        default=Path("context/progress"),
        help="Directory containing progress fragments (default: context/progress).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run fragment consolidation."""
    args = parse_args(argv)
    fragments = collect_fragments(args.progress_dir)
    if not fragments:
        print(f"No non-empty progress fragments found in {args.progress_dir}.")
        return 0

    if not args.target.is_file():
        print(f"Error: target tracker not found: {args.target}", file=sys.stderr)
        return 1

    tracker_text = args.target.read_text(encoding="utf-8")
    insertion_block = build_insertion_block(fragments)

    try:
        updated_text = insert_under_completed(tracker_text, insertion_block)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    fragment_list = ", ".join(path.name for path, _ in fragments)
    if args.dry_run:
        print(f"[dry-run] Target: {args.target}")
        print(f"[dry-run] Fragments ({len(fragments)}): {fragment_list}")
        action = "delete" if args.delete else f"move to {args.progress_dir / 'archive'}"
        print(f"[dry-run] Post-consolidation action: {action}")
        print("[dry-run] Block to insert under '## Completed':\n")
        print(insertion_block)
        return 0

    args.target.write_text(updated_text, encoding="utf-8")
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    destinations = archive_fragments(
        fragments,
        args.progress_dir / "archive",
        delete=args.delete,
        timestamp=timestamp,
    )

    print(f"Consolidated {len(fragments)} fragment(s) into {args.target}: {fragment_list}")
    if args.delete:
        print("Deleted processed fragment file(s).")
    else:
        archived = ", ".join(str(dest) for dest in destinations)
        print(f"Archived fragment(s) to: {archived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
