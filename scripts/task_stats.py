#!/usr/bin/env python3
"""
Analyze completed tasks: count per day and calculate average.
"""

from pathlib import Path
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict

COMPLETED_FILE = Path(__file__).resolve().parent.parent / "04_completed.txt"
DATE_PATTERN = re.compile(r'\[(\d{4}-\d{2}-\d{2})\]')


def parse_completed_tasks(file_path: Path) -> Dict[str, int]:
    """
    Parse completed file and return dict: {date: count}
    """
    if not file_path.exists():
        print(f"Error: {file_path} not found", file=sys.stderr)
        sys.exit(1)
    
    tasks_per_day: Dict[str, int] = defaultdict(int)
    lines = file_path.read_text().splitlines()
    
    for line in lines:
        match = DATE_PATTERN.search(line)
        if match:
            date_str = match.group(1)
            tasks_per_day[date_str] += 1
    
    return dict(tasks_per_day)


def format_date(date_str: str) -> str:
    """Format date string for display."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d (%a)")
    except ValueError:
        return date_str


def calculate_stats(tasks_per_day: Dict[str, int]) -> tuple:
    """Calculate statistics."""
    if not tasks_per_day:
        return 0, 0, 0, []
    
    total_tasks = sum(tasks_per_day.values())
    total_days = len(tasks_per_day)
    average = total_tasks / total_days if total_days > 0 else 0
    
    # Sort by date
    sorted_days = sorted(tasks_per_day.items())
    
    return total_tasks, total_days, average, sorted_days


def display_stats(tasks_per_day: Dict[str, int]):
    """Display task statistics."""
    total_tasks, total_days, average, sorted_days = calculate_stats(tasks_per_day)
    
    if total_days == 0:
        print("No completed tasks found.")
        return
    
    print(f"\n{'='*70}")
    print(f"TASK COMPLETION STATISTICS")
    print(f"{'='*70}\n")
    
    print(f"Total tasks completed: {total_tasks}")
    print(f"Total days with completions: {total_days}")
    print(f"Average tasks per day: {average:.2f}\n")
    
    print(f"{'='*70}")
    print(f"TASKS PER DAY")
    print(f"{'='*70}\n")
    
    for date_str, count in sorted_days:
        formatted_date = format_date(date_str)
        bar = "█" * min(count, 50)  # Cap bar at 50 for display
        print(f"{formatted_date:25} {count:3} tasks  {bar}")
    
    print()


def main() -> int:
    tasks_per_day = parse_completed_tasks(COMPLETED_FILE)
    display_stats(tasks_per_day)
    return 0


if __name__ == "__main__":
    sys.exit(main())








