#!/usr/bin/env python3
"""
Sync checked tasks from 02.1_today.txt into 02.4_completed.txt with date stamps.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent
TODAY_FILE = ROOT / "02.1_today.txt"
COMPLETED_FILE = ROOT / "02.4_completed.txt"

TASK_REGEX = re.compile(r"\[x\]\s*(.*)", re.IGNORECASE)


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


def parse_today() -> List[Tuple[str, str]]:
    if not TODAY_FILE.exists():
        raise FileNotFoundError(f"Could not find {TODAY_FILE}")

    tasks: List[Tuple[str, str]] = []
    current_section: str | None = None

    for raw_line in TODAY_FILE.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if raw_line.lstrip() == raw_line:
            current_section = stripped
            continue

        if "[x]" not in raw_line.lower():
            continue

        match = TASK_REGEX.search(raw_line)
        if not match:
            continue

        task_text = normalize_task(match.group(1))
        if not task_text:
            continue

        section_name = current_section or "General"
        tasks.append((section_name, task_text))

    return tasks


def sync_completed() -> Tuple[int, List[Tuple[str, str]]]:
    today_str = date.today().isoformat()
    section_order, section_entries, section_tasks = load_completed()
    tasks_added: List[Tuple[str, str]] = []

    for section_name, task_text in parse_today():
        if section_name not in section_entries:
            section_order.append(section_name)
            section_entries[section_name] = []
            section_tasks[section_name] = set()

        if task_text in section_tasks[section_name]:
            continue

        entry = f"\t[{today_str}] [x] {task_text}"
        section_entries[section_name].append(entry)
        section_tasks[section_name].add(task_text)
        tasks_added.append((section_name, task_text))

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

    return len(tasks_added), tasks_added


def main() -> int:
    try:
        count, additions = sync_completed()
    except FileNotFoundError as exc:
        print(exc)
        return 1

    if count == 0:
        print("No new completed tasks to add.")
    else:
        print(f"Added {count} task(s) to {COMPLETED_FILE.name}:")
        for section_name, task_text in additions:
            print(f"  - {section_name}: {task_text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
