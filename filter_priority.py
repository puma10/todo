#!/usr/bin/env python3
"""
Filter and display tasks by priority [1], [2], [3] sequentially.
"""

from pathlib import Path
import re
import sys
from typing import Dict, List, Tuple

TODAY_FILE = Path(__file__).resolve().parent / "02.1_today.txt"
PRIORITY_PATTERN = re.compile(r'^\s*\[([123])\]\s*(.*)$')


def leading_indent(line: str) -> int:
    """Count leading tabs/spaces."""
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def parse_file(file_path: Path) -> Dict[int, List[Tuple[str, List[str]]]]:
    """
    Parse file and return dict: {priority: [(section, [lines])]}
    """
    if not file_path.exists():
        print(f"Error: {file_path} not found", file=sys.stderr)
        sys.exit(1)
    
    lines = file_path.read_text().splitlines()
    priorities: Dict[int, List[Tuple[str, List[str]]]] = {1: [], 2: [], 3: []}
    
    current_section: str | None = None
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines and legend lines
        if not stripped or stripped.startswith('[') and '=' in stripped:
            i += 1
            continue
        
        # Check if it's a section header (no leading whitespace)
        if line.lstrip() == line and stripped:
            current_section = stripped
            i += 1
            continue
        
        # Check for priority tag
        match = PRIORITY_PATTERN.match(line)
        if match:
            priority = int(match.group(1))
            task_line = line
            
            # Collect nested subtasks
            task_lines = [task_line]
            task_indent = leading_indent(line)
            i += 1
            
            # Collect all nested lines until we hit same or higher level
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()
                
                # Stop at section headers (unindented non-empty lines)
                if next_line.lstrip() == next_line and next_stripped:
                    break
                
                # Stop if next line is at same or higher indent level (another task)
                next_indent = leading_indent(next_line)
                if next_stripped and next_indent <= task_indent:
                    # Check if it's another priority task
                    if PRIORITY_PATTERN.match(next_line):
                        break
                    # Otherwise it's a sibling task, stop collecting
                    break
                
                # Include empty lines and nested content
                task_lines.append(next_line)
                i += 1
            
            # Add to priorities dict
            section_name = current_section or "Uncategorized"
            priorities[priority].append((section_name, task_lines))
        else:
            i += 1
    
    return priorities


def output_priorities(priorities: Dict[int, List[Tuple[str, List[str]]]]):
    """Output priorities sequentially: 1, 2, 3"""
    for priority in [1, 2, 3]:
        items = priorities[priority]
        if not items:
            continue
        
        print(f"\n{'='*60}")
        print(f"PRIORITY [{priority}]")
        print(f"{'='*60}\n")
        
        current_section = None
        for section, task_lines in items:
            if section != current_section:
                if current_section is not None:
                    print()
                print(section)
                current_section = section
            
            for task_line in task_lines:
                print(task_line)
        
        print()


def main() -> int:
    priorities = parse_file(TODAY_FILE)
    
    # Check if any priorities found
    if not any(priorities.values()):
        print("No priority [1], [2], or [3] items found.")
        return 0
    
    output_priorities(priorities)
    return 0


if __name__ == "__main__":
    sys.exit(main())

