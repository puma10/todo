#!/usr/bin/env python3
"""
Show only [1] priority items from today's file.
"""

from pathlib import Path
import re
import sys
from typing import List, Tuple


TODAY_FILE = Path(__file__).resolve().parent / "02.1_today.txt"
PRIORITY_1_PATTERN = re.compile(r'^\s*\[1\]\s*(.*)$')


def parse_today_priority1(file_path: Path) -> List[Tuple[str, str]]:
    """
    Parse file and return list of [(section, task_text)] for [1] items only.
    Only returns top-level tasks, no nested children.
    """
    if not file_path.exists():
        print(f"Error: {file_path} not found", file=sys.stderr)
        sys.exit(1)
    
    lines = file_path.read_text().splitlines()
    priority1_items: List[Tuple[str, str]] = []
    
    current_section: str | None = None
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines and legend lines
        if not stripped or (stripped.startswith('[') and '=' in stripped):
            i += 1
            continue
        
        # Check if it's a section header (no leading whitespace)
        if line.lstrip() == line and stripped:
            current_section = stripped
            i += 1
            continue
        
        # Check for [1] priority tag
        match = PRIORITY_1_PATTERN.match(line)
        if match:
            # Extract just the task text (remove [1] tag and leading whitespace)
            task_text = match.group(1).strip()
            
            # Skip if empty
            if task_text:
                section_name = current_section or "Uncategorized"
                priority1_items.append((section_name, task_text))
            
            # Skip nested children - just move to next line
            i += 1
        else:
            i += 1
    
    return priority1_items


def display_priority1(items: List[Tuple[str, str]]):
    """Display [1] priority items in 'section / task' format."""
    if not items:
        print("No [1] priority items found in today's list.")
        return
    
    print(f"\n{'='*70}")
    print(f"TODAY'S PRIORITY [1] ITEMS")
    print(f"{'='*70}\n")
    
    for section, task_text in items:
        print(f"{section} / {task_text}")
    
    print(f"\n{'='*70}")
    print(f"Total: {len(items)} items")
    print(f"{'='*70}\n")


def main() -> int:
    items = parse_today_priority1(TODAY_FILE)
    display_priority1(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())

