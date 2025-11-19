#!/usr/bin/env python3
"""Aggregate todo items by status across the repo."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

STATUS_TAGS = {
    "b": "blocked",
    "i": "in-progress",
    "w": "waiting",
    "d": "delegated",
    "x": "done",
    "t": "transfer",
}

STATUS_LABELS = {
    "blocked": "Blocked",
    "in-progress": "In Progress",
    "waiting": "Waiting",
    "delegated": "Delegated",
    "done": "Completed",
    "transfer": "Transfer",
}

STATUS_ORDER = ["blocked", "in-progress", "waiting", "delegated", "done"]
STATUS_PATTERN = re.compile(r"^\s*\[([bdwixt])\]\s*(.*)$", re.IGNORECASE)
LEGEND_PATTERN = re.compile(r"^\[[^\]]+\]\s*=", re.IGNORECASE)
HEADING_PATTERN = re.compile(r"^\s*(#+)\s*(.+?)\s*$")

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
    "t": "transfer",
    "transfer": "transfer",
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
    headings: List[str] = field(default_factory=list)


@dataclass
class StatusOutputTarget:
    path: Path
    statuses: List[str]
    title: str


def leading_indent(line: str) -> int:
    """Return indentation length treating tabs as four spaces."""
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def default_status_outputs() -> List[Dict[str, object]]:
    return [
        {
            "path": "03_in_progress_status.txt",
            "title": "In Progress (incl. Blocked)",
            "statuses": ["in-progress", "blocked"],
        },
        {
            "path": "03_blocked.txt",
            "title": "Blocked",
            "statuses": ["blocked"],
        },
    ]


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        return {
            "extra_files": [],
            "glob_patterns": [],
            "status_outputs": default_status_outputs(),
            "import_targets": [],
        }

    data = json.loads(config_path.read_text())
    extra_files = data.get("extra_files", [])
    glob_patterns = data.get("glob_patterns", [])
    status_outputs = data.get("status_outputs", default_status_outputs())
    import_targets = data.get("import_targets", [])

    if not isinstance(extra_files, list) or not isinstance(glob_patterns, list):
        raise ValueError("Config file must define lists for 'extra_files' and 'glob_patterns'.")
    if not isinstance(status_outputs, list):
        raise ValueError("Config file must define a list for 'status_outputs'.")
    if not isinstance(import_targets, list):
        raise ValueError("Config file must define a list for 'import_targets'.")

    return {
        "extra_files": list(extra_files),
        "glob_patterns": list(glob_patterns),
        "status_outputs": status_outputs or default_status_outputs(),
        "import_targets": import_targets or [],
    }


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


def gather_sources(root: Path) -> Tuple[List[Path], Dict[str, Any]]:
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

    return sources, config


def resolve_status_token(token: str) -> str | None:
    if not isinstance(token, str):
        return None
    key = token.strip().lower()
    if not key:
        return None
    return STATUS_ALIASES.get(key)


def parse_output_entry(root: Path, entry: Dict[str, Any]) -> StatusOutputTarget:
    if not isinstance(entry, dict):
        raise ValueError("Entries in 'status_outputs' must be objects.")

    path_value = entry.get("path")
    statuses_value = entry.get("statuses")
    title_value = entry.get("title")

    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("Each status output entry must include a non-empty 'path'.")
    if not isinstance(statuses_value, list) or not statuses_value:
        raise ValueError("Each status output entry must include a 'statuses' list.")

    normalized_statuses: List[str] = []
    for status_token in statuses_value:
        status_name = resolve_status_token(status_token)
        if not status_name:
            raise ValueError(f"Unknown status '{status_token}' in status_outputs.")
        if status_name not in normalized_statuses:
            normalized_statuses.append(status_name)

    if not normalized_statuses:
        raise ValueError("Each status output entry must include at least one valid status.")

    title_text: str
    if isinstance(title_value, str) and title_value.strip():
        title_text = title_value.strip()
    else:
        title_text = ", ".join(STATUS_LABELS.get(status, status.title()) for status in normalized_statuses)

    output_path = resolve_path(root, path_value)
    return StatusOutputTarget(path=output_path, statuses=normalized_statuses, title=title_text)


def build_output_targets(root: Path, config: Dict[str, Any]) -> List[StatusOutputTarget]:
    entries = config.get("status_outputs", default_status_outputs())
    targets: List[StatusOutputTarget] = []
    for entry in entries:
        try:
            targets.append(parse_output_entry(root, entry))
        except ValueError as exc:
            raise ValueError(f"Invalid status output entry: {exc}") from exc
    return targets


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
    heading_stack: List[str] = []

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if not stripped:
            idx += 1
            continue

        if LEGEND_PATTERN.match(stripped):
            idx += 1
            continue

        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            hashes = heading_match.group(1)
            heading_text = heading_match.group(2).strip()
            level = len(hashes)
            heading_label = f"{'#' * level} {heading_text}"
            while len(heading_stack) >= level:
                heading_stack.pop()
            heading_stack.append(heading_label)
            if line.lstrip() == line and stripped:
                section = stripped
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

        tasks.append(TaskEntry(status, section, file_path, block, list(heading_stack)))

    return tasks


def normalize_status_filters(raw_filters: Sequence[str] | None) -> List[str]:
    if not raw_filters:
        return STATUS_ORDER

    selected = []
    seen = set()
    for raw in raw_filters:
        for token in raw.split(","):
            status = resolve_status_token(token)
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
    parser.add_argument(
        "--write-files",
        action="store_true",
        help="Update the configured status output files.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress CLI output (useful when only writing files).",
    )
    return parser.parse_args()


def format_relative(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def build_section_lines(entries: List[TaskEntry], root: Path) -> List[str]:
    lines: List[str] = []
    current_section: Tuple[str, str] | None = None
    for entry in entries:
        rel_path = format_relative(root, entry.file_path)
        section_key = (entry.section, rel_path)
        if section_key != current_section:
            if current_section is not None:
                lines.append("")
            lines.append(f"{entry.section} — {rel_path}")
            current_section = section_key
        for line in entry.lines:
            lines.append(f"  {line}")
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def render_status_report(title: str, statuses: List[str], tasks_by_status: Dict[str, List[TaskEntry]], root: Path) -> str:
    heading = title.strip() or "Status Report"
    lines = [
        heading,
        "=" * len(heading),
        "",
    ]

    any_entries = False
    for status in statuses:
        entries = tasks_by_status.get(status, [])
        if not entries:
            continue
        any_entries = True
        label = STATUS_LABELS.get(status, status.title())
        lines.append(label)
        lines.append("-" * len(label))
        lines.extend(build_section_lines(entries, root))
        lines.append("")

    if not any_entries:
        lines.append("No tasks found for these statuses.")

    return "\n".join(lines).rstrip() + "\n"


def write_status_files(tasks_by_status: Dict[str, List[TaskEntry]], root: Path, targets: List[StatusOutputTarget]) -> List[Path]:
    written: List[Path] = []
    for target in targets:
        content = render_status_report(target.title, target.statuses, tasks_by_status, root)
        target.path.parent.mkdir(parents=True, exist_ok=True)
        target.path.write_text(content)
        written.append(target.path)
    return written


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
        section_lines = build_section_lines(entries, root)
        if section_lines:
            print()
            for line in section_lines:
                print(line)
        print()

    if not printed_any:
        print("No tasks found for the requested status filters.")


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    sources, config = gather_sources(root)

    if args.list_sources:
        for path in sources:
            print(format_relative(root, path))
        return 0

    selected_statuses = normalize_status_filters(args.status)

    tasks_by_status: Dict[str, List[TaskEntry]] = {status: [] for status in STATUS_ORDER}
    for src in sources:
        for task in parse_file(src):
            tasks_by_status.setdefault(task.status, []).append(task)

    try:
        output_targets = build_output_targets(root, config)
    except ValueError as exc:
        print(f"[status-view] {exc}", file=sys.stderr)
        return 2

    written_paths: List[Path] = []
    if args.write_files:
        written_paths = write_status_files(tasks_by_status, root, output_targets)
        if not args.quiet:
            for path in written_paths:
                print(f"[status-view] Updated {format_relative(root, path)}")

    if not args.quiet:
        output(tasks_by_status, root, selected_statuses)

    return 0


if __name__ == "__main__":
    sys.exit(main())
