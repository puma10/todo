#!/usr/bin/env python3
"""Aggregate todo items by status across the repo."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

STATUS_TAGS = {
    "b": "blocked",
    "i": "in-progress",
    "w": "waiting",
    "d": "delegated",
    "x": "done",
}

STATUS_LABELS = {
    "blocked": "Blocked",
    "in-progress": "In Progress",
    "waiting": "Waiting",
    "delegated": "Delegated",
    "done": "Completed",
}

STATUS_ORDER = ["blocked", "in-progress", "waiting", "delegated", "done"]
STATUS_PATTERN = re.compile(r"^\s*\[([bdwix])\]\s*(.*)$", re.IGNORECASE)
LEGEND_PATTERN = re.compile(r"^\[[^\]]+\]\s*=", re.IGNORECASE)

STATUS_ALIASES = {
    "b": "blocked",
    "blocked": "blocked",
    "block": "blocked",
    "i": "in-progress",
    "ip": "in-progress",
    "in-progress": "in-progress",
    "inprogress": "in-progress",
    "progress": "in-progress",
    "w": "waiting",
    "wait": "waiting",
    "waiting": "waiting",
    "hold": "waiting",
    "d": "delegated",
    "delegate": "delegated",
    "delegated": "delegated",
    "x": "done",
    "done": "done",
    "complete": "done",
    "completed": "done",
}

DEFAULT_SOURCES = [
    Path("02.1_today.txt"),
    Path("02.2_tomorrow"),
    Path("02.3_next_week"),
    Path("03_in_progress"),
]

PROJECTS_DIR = Path("projects")
CONFIG_FILE = Path("task_sources.json")


@dataclass
class TaskEntry:
    status: str
    section: str
    file_path: Path
    lines: List[str]


def leading_indent(line: str) -> int:
    """Return indentation length treating tabs as four spaces."""
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def load_config(config_path: Path) -> Dict[str, List[str]]:
    if not config_path.exists():
        return {"extra_files": [], "glob_patterns": []}

    data = json.loads(config_path.read_text())
    extra_files = data.get("extra_files", [])
    glob_patterns = data.get("glob_patterns", [])

    if not isinstance(extra_files, list) or not isinstance(glob_patterns, list):
        raise ValueError("Config file must define lists for 'extra_files' and 'glob_patterns'.")

    return {"extra_files": list(extra_files), "glob_patterns": list(glob_patterns)}


def resolve_path(base: Path, path_str: str) -> Path:
    expanded = os.path.expanduser(path_str)
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def expand_glob(base: Path, pattern: str) -> List[Path]:
    pattern_path = pattern
    if not os.path.isabs(pattern):
        pattern_path = str((base / pattern).resolve())
    matches = []
    for match in glob(os.path.expanduser(pattern_path), recursive=True):
        path_obj = Path(match)
        if path_obj.is_file():
            matches.append(path_obj.resolve())
    return matches


def gather_sources(root: Path) -> List[Path]:
    """Return resolved file list for aggregation."""
    seen = set()
    sources: List[Path] = []

    def add_path(path: Path) -> None:
        if not path.is_file():
            print(f"[status-view] Skipping missing file: {path}", file=sys.stderr)
            return
        if path in seen:
            return
        seen.add(path)
        sources.append(path)

    for relative in DEFAULT_SOURCES:
        add_path((root / relative).resolve())

    projects_dir = (root / PROJECTS_DIR).resolve()
    if projects_dir.is_dir():
        for child in sorted(projects_dir.iterdir()):
            if child.is_file():
                add_path(child.resolve())

    config_path = (root / CONFIG_FILE).resolve()
    try:
        config = load_config(config_path)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[status-view] Invalid config {config_path}: {exc}", file=sys.stderr)
        sys.exit(2)

    for extra in config["extra_files"]:
        if not isinstance(extra, str):
            print(f"[status-view] Ignoring non-string entry in extra_files: {extra}", file=sys.stderr)
            continue
        add_path(resolve_path(root, extra))

    for pattern in config["glob_patterns"]:
        if not isinstance(pattern, str):
            print(f"[status-view] Ignoring non-string entry in glob_patterns: {pattern}", file=sys.stderr)
            continue
        for matched in expand_glob(root, pattern):
            add_path(matched)

    return sources


def parse_file(file_path: Path) -> List[TaskEntry]:
    """Extract status-tagged tasks from a file."""
    try:
        lines = file_path.read_text().splitlines()
    except UnicodeDecodeError:
        print(f"[status-view] Cannot decode file (skipping): {file_path}", file=sys.stderr)
        return []

    tasks: List[TaskEntry] = []
    section = "Uncategorized"
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if not stripped:
            idx += 1
            continue

        if LEGEND_PATTERN.match(stripped):
            idx += 1
            continue

        if line.lstrip() == line and not STATUS_PATTERN.match(line):
            section = stripped
            idx += 1
            continue

        match = STATUS_PATTERN.match(line)
        if not match:
            idx += 1
            continue

        status_key = match.group(1).lower()
        status = STATUS_TAGS.get(status_key)
        if status is None:
            idx += 1
            continue

        block = [line.rstrip()]
        base_indent = leading_indent(line)
        idx += 1

        while idx < len(lines):
            next_line = lines[idx]
            next_stripped = next_line.strip()
            next_indent = leading_indent(next_line)

            if not next_stripped:
                block.append(next_line.rstrip())
                idx += 1
                continue

            if next_line.lstrip() == next_line and next_stripped and not STATUS_PATTERN.match(next_line):
                break

            next_match = STATUS_PATTERN.match(next_line)
            if next_match and next_indent <= base_indent:
                break

            if next_indent <= base_indent:
                break

            block.append(next_line.rstrip())
            idx += 1

        tasks.append(TaskEntry(status, section, file_path, block))

    return tasks


def normalize_status_filters(raw_filters: Sequence[str] | None) -> List[str]:
    if not raw_filters:
        return STATUS_ORDER

    selected = []
    seen = set()
    for raw in raw_filters:
        for token in raw.split(","):
            key = token.strip().lower()
            if not key:
                continue
            status = STATUS_ALIASES.get(key)
            if not status:
                print(f"[status-view] Unknown status filter '{token}'.", file=sys.stderr)
                sys.exit(2)
            if status not in seen:
                seen.add(status)
                selected.append(status)

    return selected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show all tasks tagged with [i], [b], [w], [d], or [x].")
    parser.add_argument(
        "-s",
        "--status",
        action="append",
        help="Filter by status (comma separated). e.g. --status blocked,in-progress",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="Print the files being scanned and exit.",
    )
    return parser.parse_args()


def format_relative(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def output(tasks_by_status: Dict[str, List[TaskEntry]], root: Path, selected: List[str]) -> None:
    printed_any = False
    for status in selected:
        entries = tasks_by_status.get(status, [])
        if not entries:
            continue

        printed_any = True
        label = STATUS_LABELS[status]
        print(f"\n{'=' * 70}")
        print(f"{label} ({len(entries)})")
        print(f"{'=' * 70}")

        current_section: Tuple[str, str] | None = None
        for entry in entries:
            rel_path = format_relative(root, entry.file_path)
            section_key = (entry.section, rel_path)
            if section_key != current_section:
                print(f"\n{entry.section} — {rel_path}")
                current_section = section_key

            for line in entry.lines:
                print(f"  {line}")
        print()

    if not printed_any:
        print("No tasks found for the requested status filters.")


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    selected_statuses = normalize_status_filters(args.status)
    sources = gather_sources(root)

    if args.list_sources:
        for path in sources:
            print(format_relative(root, path))
        return 0

    tasks_by_status: Dict[str, List[TaskEntry]] = {status: [] for status in STATUS_ORDER}
    for src in sources:
        for task in parse_file(src):
            tasks_by_status.setdefault(task.status, []).append(task)

    output(tasks_by_status, root, selected_statuses)
    return 0


if __name__ == "__main__":
    sys.exit(main())
