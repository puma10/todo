#!/usr/bin/env python3
"""Copy tagged tasks from external files into 02.1_today.txt."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from task_status_view import (  # type: ignore
    CONFIG_FILE,
    TaskEntry,
    load_config,
    normalize_status_filters,
    parse_file,
)

ROOT = Path(__file__).resolve().parent
TODAY_FILE = ROOT / "02.1_today.txt"
DEFAULT_SECTION = "Imported"
DEFAULT_STATUS_FILTER = ["in-progress", "blocked"]


@dataclass
class ImportSpec:
    name: str
    source_path: Path
    section: str
    statuses: List[str]
    allow_duplicates: bool = False
    use_source_section: bool = False
    section_map: Dict[str, str] = field(default_factory=dict)


def normalize_status_input(raw: Sequence[str] | str | None) -> List[str]:
    if raw is None:
        tokens: List[str] = list(DEFAULT_STATUS_FILTER)
    elif isinstance(raw, str):
        tokens = [raw]
    else:
        tokens = [str(item) for item in raw]
    return normalize_status_filters(tokens)


def coerce_path(path_str: str) -> Path:
    expanded = os.path.expanduser(path_str)
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = (ROOT / candidate).resolve()
    return candidate


def resolve_manual_source(path_arg: str, config: Dict[str, Any], target_specs: Dict[str, ImportSpec]) -> Path:
    if not path_arg:
        raise FileNotFoundError("Source path cannot be empty.")

    if path_arg in target_specs:
        return target_specs[path_arg].source_path

    candidates = []

    direct = coerce_path(path_arg)
    if direct.exists():
        candidates.append(direct)

    relative = (ROOT / path_arg).resolve()
    if relative.exists():
        candidates.append(relative)

    for entry in config.get("extra_files", []):
        if not isinstance(entry, str):
            continue
        entry_path = coerce_path(entry)
        if not entry_path.exists():
            continue
        if entry_path.name == path_arg or entry_path.stem == path_arg:
            candidates.append(entry_path)

    if not candidates:
        raise FileNotFoundError(f"Could not find source '{path_arg}'.")

    return candidates[0]


def build_config_targets(config: Dict[str, Any]) -> Dict[str, ImportSpec]:
    targets: Dict[str, ImportSpec] = {}
    for entry in config.get("import_targets", []):
        if not isinstance(entry, dict):
            continue
        source_value = entry.get("source")
        if not isinstance(source_value, str) or not source_value.strip():
            print("[import] Skipping import target with missing 'source'.", file=sys.stderr)
            continue
        source_path = coerce_path(source_value)
        name_value = entry.get("name") or source_path.stem
        section_value = entry.get("section")
        if isinstance(section_value, str) and section_value.strip():
            section_name = section_value.strip()
        else:
            section_name = DEFAULT_SECTION
        statuses_value = entry.get("statuses")
        allow_duplicates = bool(entry.get("allow_duplicates", False))
        use_source_section = bool(entry.get("use_source_section", False))
        section_map_value = entry.get("section_map") or {}
        section_map: Dict[str, str] = {}
        if isinstance(section_map_value, dict):
            for key, val in section_map_value.items():
                if isinstance(key, str) and isinstance(val, str):
                    section_map[key.strip()] = val.strip()
        try:
            statuses = normalize_status_input(statuses_value)
        except SystemExit as exc:  # normalize_status_filters may sys.exit on invalid status
            raise ValueError(f"Invalid status list for import target '{name_value}'.") from exc
        targets[name_value] = ImportSpec(
            name=name_value,
            source_path=source_path,
            section=section_name,
            statuses=statuses,
            allow_duplicates=allow_duplicates,
            use_source_section=use_source_section,
            section_map=section_map,
        )
    return targets


def gather_tasks(source_path: Path, statuses: Sequence[str]) -> List[TaskEntry]:
    if not source_path.is_file():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    entries = parse_file(source_path)
    filtered: List[TaskEntry] = []
    seen_blocks: set[str] = set()
    for entry in entries:
        if entry.status not in statuses:
            continue
        block_text = canonicalize_lines(entry.lines)
        if not block_text or block_text in seen_blocks:
            continue
        seen_blocks.add(block_text)
        filtered.append(entry)
    return filtered


def find_section_indices(lines: List[str], section: str) -> tuple[int, int]:
    section_idx = -1
    insert_idx = len(lines)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if line.lstrip() != line:
            continue
        if stripped == section:
            section_idx = idx
            next_idx = len(lines)
            for j in range(idx + 1, len(lines)):
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped:
                    continue
                if next_line.lstrip() == next_line:
                    next_idx = j
                    break
            insert_idx = next_idx
            break
    return section_idx, insert_idx


def canonicalize_lines(lines: List[str]) -> str:
    normalized = [line.strip() for line in lines if line.strip()]
    return "\n".join(normalized)


def heading_level(label: str) -> int | None:
    stripped = label.lstrip()
    if not stripped.startswith("#"):
        return None
    count = len(stripped) - len(stripped.lstrip("#"))
    return count


def normalize_heading_chain(chain: List[str]) -> List[str]:
    cleaned = [label.strip() for label in chain if label.strip()]
    if not cleaned:
        return []
    levels = [heading_level(label) for label in cleaned]
    if any(level is not None and level >= 2 for level in levels):
        for idx, level in enumerate(levels):
            if level is not None and level >= 2:
                return cleaned[idx:]
    return cleaned


def reindent_entry_lines(lines: List[str], indent_prefix: str) -> List[str]:
    adjusted: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            adjusted.append("")
        else:
            adjusted.append(f"{indent_prefix}{stripped}")
    return adjusted


def build_heading_block(heading_chain: List[str], entries: List[TaskEntry]) -> List[str]:
    lines: List[str] = []
    if heading_chain:
        for level, heading in enumerate(heading_chain, start=1):
            lines.append(f"{'\t' * level}{heading}")
    entry_indent = "\t" * (len(heading_chain) + 1 if heading_chain else 1)
    for idx, entry in enumerate(entries):
        lines.extend(reindent_entry_lines(entry.lines, entry_indent))
        if idx != len(entries) - 1:
            lines.append("")
    if lines and lines[-1] != "":
        lines.append("")
    return lines


def determine_section(spec: ImportSpec, entry: TaskEntry) -> str:
    section_name = entry.section.strip() if entry.section else ""
    if section_name and section_name in spec.section_map:
        return spec.section_map[section_name] or spec.section
    if spec.use_source_section and section_name:
        return section_name
    return spec.section


def insert_into_section(lines: List[str], section: str, block: List[str]) -> List[str]:
    new_lines = list(lines)
    if not new_lines:
        new_lines = []
    section_idx, insert_idx = find_section_indices(new_lines, section)

    if section_idx == -1:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(section)
        new_lines.append("")
        insert_idx = len(new_lines)
    else:
        if insert_idx > 0 and new_lines[insert_idx - 1].strip():
            new_lines.insert(insert_idx, "")
            insert_idx += 1

    for line in block:
        new_lines.insert(insert_idx, line)
        insert_idx += 1

    if insert_idx < len(new_lines) and new_lines[insert_idx].strip():
        new_lines.insert(insert_idx, "")

    return new_lines


def run_single_import(spec: ImportSpec, *, dry_run: bool, quiet: bool) -> int:
    try:
        tasks = gather_tasks(spec.source_path, spec.statuses)
    except FileNotFoundError as exc:
        if not quiet:
            print(f"[{spec.name}] Skipping: {exc}")
        return 0

    if not tasks:
        if not quiet:
            print(f"[{spec.name}] No tasks matched statuses {spec.statuses}.")
        return 0

    today_text = TODAY_FILE.read_text()
    try:
        today_entries = parse_file(TODAY_FILE)
    except FileNotFoundError:
        today_entries = []
    existing_keys = {
        canonicalize_lines(entry.lines)
        for entry in today_entries
        if entry.status in spec.statuses
    }
    unique_tasks: List[TaskEntry] = []
    duplicates = 0

    for entry in tasks:
        block_key = canonicalize_lines(entry.lines)
        if not block_key:
            continue
        if not spec.allow_duplicates and block_key in existing_keys:
            duplicates += 1
            continue
        unique_tasks.append(entry)
        existing_keys.add(block_key)

    if not unique_tasks:
        if not quiet:
            print(f"[{spec.name}] Nothing new to import (all duplicates).")
        return 0

    section_groups: Dict[str, Dict[tuple[str, ...], List[TaskEntry]]] = {}
    section_order: List[str] = []
    heading_order: Dict[str, List[tuple[str, ...]]] = {}
    for entry in unique_tasks:
        target_section = determine_section(spec, entry)
        heading_chain = normalize_heading_chain(entry.headings.copy())
        fallback_heading = entry.section.strip() or target_section
        if not heading_chain:
            heading_chain = [fallback_heading]
        heading_key = tuple(heading_chain)
        if target_section not in section_groups:
            section_groups[target_section] = {}
            section_order.append(target_section)
            heading_order[target_section] = []
        if heading_key not in section_groups[target_section]:
            section_groups[target_section][heading_key] = []
            heading_order[target_section].append(heading_key)
        section_groups[target_section][heading_key].append(entry)

    if dry_run:
        if not quiet:
            total = sum(len(entries) for group in section_groups.values() for entries in group.values())
            print(f"[{spec.name}] Dry run — would insert {total} task(s) into sections: {', '.join(section_order)}")
            for section in section_order:
                print(f"\n  Section: {section}")
                for heading in heading_order[section]:
                    preview_block = build_heading_block(list(heading), section_groups[section][heading])
                    for line in preview_block:
                        print(line)
        return 0

    today_lines = today_text.splitlines()
    for section in section_order:
        block_lines: List[str] = []
        for heading in heading_order[section]:
            block_lines.extend(build_heading_block(list(heading), section_groups[section][heading]))
        while block_lines and block_lines[-1] == "":
            block_lines.pop()
        today_lines = insert_into_section(today_lines, section, block_lines)
    TODAY_FILE.write_text("\n".join(today_lines).rstrip() + "\n")

    inserted_total = sum(len(entries) for group in section_groups.values() for entries in group.values())

    if not quiet:
        print(f"[{spec.name}] Inserted {inserted_total} task(s) into sections: {', '.join(section_order)}.")
        if duplicates:
            print(f"[{spec.name}] Skipped {duplicates} duplicate block(s).")
    return inserted_total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy status-tagged tasks into 02.1_today.txt.")
    parser.add_argument(
        "source",
        nargs="?",
        help="Path (or alias) to the source todo file. Not required when using --target/--all-configured.",
    )
    parser.add_argument(
        "-s",
        "--status",
        action="append",
        help="Statuses to import (comma separated). Defaults to in-progress and blocked.",
    )
    parser.add_argument(
        "--section",
        default=DEFAULT_SECTION,
        help=f"Destination section inside 02.1_today.txt (default: {DEFAULT_SECTION}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be inserted without modifying 02.1_today.txt.",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Insert tasks even if an identical block already exists in 02.1_today.txt.",
    )
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        help="Name of an import target defined in task_sources.json (can be repeated).",
    )
    parser.add_argument(
        "--all-configured",
        action="store_true",
        help="Import all targets listed under 'import_targets' in task_sources.json.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational output (useful when running from make).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config((ROOT / CONFIG_FILE).resolve())
    target_specs = build_config_targets(config)

    specs: List[ImportSpec] = []
    seen_names: set[str] = set()

    def add_spec(spec: ImportSpec) -> None:
        key = spec.name
        if key in seen_names:
            return
        seen_names.add(key)
        specs.append(spec)

    if args.all_configured:
        for spec in target_specs.values():
            add_spec(spec)

    if args.targets:
        for target_name in args.targets:
            spec = target_specs.get(target_name)
            if spec is None:
                print(f"[import] Unknown target '{target_name}'.", file=sys.stderr)
                return 2
            add_spec(spec)

    if args.source:
        try:
            source_path = resolve_manual_source(args.source, config, target_specs)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        statuses = normalize_status_input(args.status)
        manual_spec = ImportSpec(
            name=f"manual:{args.source}",
            source_path=source_path,
            section=args.section or DEFAULT_SECTION,
            statuses=statuses,
            allow_duplicates=args.allow_duplicates,
        )
        specs.append(manual_spec)

    if not specs:
        print("No import targets specified. Provide a source or use --target/--all-configured.", file=sys.stderr)
        return 1

    total_inserted = 0
    for spec in specs:
        inserted = run_single_import(spec, dry_run=args.dry_run, quiet=args.quiet)
        total_inserted += inserted

    if args.dry_run:
        return 0

    if args.quiet:
        if total_inserted:
            print(f"[import] Inserted {total_inserted} task(s).")
        return 0

    if total_inserted:
        print(f"Imported {total_inserted} task(s) total.")
    else:
        print("No tasks imported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
