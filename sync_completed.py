#!/usr/bin/env python3
"""
Move checked tasks from daily and in-progress lists into 02.4_completed.txt.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent
TODAY_FILE = ROOT / "02.1_today.txt"
IN_PROGRESS_FILE = ROOT / "03_in_progress"
COMPLETED_FILE = ROOT / "02.4_completed.txt"

TASK_REGEX = re.compile(r"\[x\]\s*(.*)", re.IGNORECASE)


@dataclass(frozen=True)
class TaskEntry:
    section: str
    text: str
    file_path: Path
    line_index: int


def normalize_task(text: str) -> str:
    return " ".join(text.strip().split())


def extract_task_text(line: str) -> str:
    match = TASK_REGEX.search(line)
    if match:
        return normalize_task(match.group(1))
    return normalize_task(line)


def load_completed() -> Tuple[List[str], Dict[str, List[str]], Dict[str, Set[str]]]:
    section_order: List[str] = []
    section_entries: Dict[str, List[str]] = {}
    section_tasks: Dict[str, Set[str]] = {}
    current_section: str | None = None

    if not COMPLETED_FILE.exists():
        return section_order, section_entries, section_tasks

    for raw_line in COMPLETED_FILE.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if raw_line.lstrip() == raw_line:
            current_section = stripped
            if current_section not in section_entries:
                section_order.append(current_section)
                section_entries[current_section] = []
                section_tasks[current_section] = set()
            continue

        if current_section is None:
            continue

        entry_line = raw_line.rstrip()
        section_entries[current_section].append(entry_line)
        section_tasks[current_section].add(extract_task_text(entry_line))

    return section_order, section_entries, section_tasks


def extract_tasks_from_lines(lines: List[str], file_path: Path) -> List[TaskEntry]:
    tasks: List[TaskEntry] = []
    current_section: str | None = None

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped:
            continue

        match = TASK_REGEX.search(raw_line)
        if match:
            task_text = normalize_task(match.group(1))
            if not task_text:
                continue
            section_name = current_section or file_path.stem
            tasks.append(TaskEntry(section_name, task_text, file_path, idx))
            continue

        if raw_line.lstrip() == raw_line:
            current_section = stripped

    return tasks


def gather_source_tasks() -> Tuple[Dict[Path, List[str]], List[TaskEntry]]:
    sources: Dict[Path, List[str]] = {}
    tasks: List[TaskEntry] = []

    if not TODAY_FILE.exists():
        raise FileNotFoundError(f"Could not find {TODAY_FILE}")

    for file_path in (TODAY_FILE, IN_PROGRESS_FILE):
        if not file_path.exists():
            continue
        lines = file_path.read_text().splitlines()
        sources[file_path] = lines
        tasks.extend(extract_tasks_from_lines(lines, file_path))

    return sources, tasks


def remove_tasks_from_sources(
    sources: Dict[Path, List[str]], tasks: List[TaskEntry]
) -> Dict[Path, int]:
    removal_counts: Dict[Path, int] = {}
    indexes_by_file: Dict[Path, Set[int]] = defaultdict(set)

    for task in tasks:
        indexes_by_file[task.file_path].add(task.line_index)

    for file_path, indexes in indexes_by_file.items():
        lines = sources.get(file_path)
        if lines is None or not indexes:
            continue
        new_lines = [line for idx, line in enumerate(lines) if idx not in indexes]
        content = "\n".join(new_lines).rstrip()
        if content:
            file_path.write_text(content + "\n")
        else:
            file_path.write_text("")
        removal_counts[file_path] = len(indexes)

    return removal_counts


def sync_completed() -> Tuple[int, int, List[Tuple[str, str, str]], Dict[Path, int]]:
    sources, tasks = gather_source_tasks()
    total_found = len(tasks)
    if not tasks:
        return 0, 0, [], {}

    today_str = date.today().isoformat()
    section_order, section_entries, section_tasks = load_completed()
    tasks_added: List[Tuple[str, str, str]] = []

    for task in tasks:
        section_name = task.section
        task_text = task.text
        if section_name not in section_entries:
            section_order.append(section_name)
            section_entries[section_name] = []
            section_tasks[section_name] = set()

        if task_text in section_tasks[section_name]:
            continue

        entry = f"\t[{today_str}] [x] {task_text}"
        section_entries[section_name].append(entry)
        section_tasks[section_name].add(task_text)
        tasks_added.append((section_name, task_text, task.file_path.name))

    if tasks_added:
        lines: List[str] = []
        for idx, section_name in enumerate(section_order):
            lines.append(section_name)
            for entry in section_entries.get(section_name, []):
                entry_out = entry
                if not entry_out.startswith("\t"):
                    entry_out = "\t" + entry_out.lstrip()
                lines.append(entry_out.rstrip())
            if idx != len(section_order) - 1:
                lines.append("")
        COMPLETED_FILE.write_text("\n".join(lines).rstrip() + "\n")

    removal_counts = remove_tasks_from_sources(sources, tasks)
    return total_found, len(tasks_added), tasks_added, removal_counts


def main() -> int:
    try:
        total_found, added_count, additions, removals = sync_completed()
    except FileNotFoundError as exc:
        print(exc)
        return 1

    if total_found == 0:
        print("No completed tasks found in source files.")
        return 0

    if added_count == 0:
        print("No new entries added to 02.4_completed.txt (all tasks already logged).")
    else:
        print(f"Added {added_count} task(s) to {COMPLETED_FILE.name}:")
        for section_name, task_text, source_name in additions:
            print(f"  - {section_name}: {task_text} (from {source_name})")

    duplicates = total_found - added_count
    if duplicates:
        print(f"{duplicates} task(s) were already recorded in {COMPLETED_FILE.name}.")

    if removals:
        for file_path, count in removals.items():
            print(f"Removed {count} completed line(s) from {file_path.name}.")
    else:
        print("No checked lines were removed from source files.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
