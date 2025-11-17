# Status-Only Views

`task_status_view.py` surfaces anything tagged with `[i]`, `[b]`, `[w]`, `[d]`, or `[x]` across the daily files, tomorrow/next-week lists, `03_in_progress`, and everything in `projects/`. It keeps the section headings so you can still see the project context.

## Persisted files
- `03_in_progress_status.txt` &mdash; all `[i]` tasks plus `[b]` tasks (blocked counts as in progress).  
- `03_blocked.txt` &mdash; only the `[b]` items.

`make sync` now runs `python3 import_external_tasks.py --all-configured --quiet` followed by `python3 task_status_view.py --write-files --quiet`, so those files refresh automatically (and pull in any new work from external repos) whenever you sync. Run the same commands manually anytime you want to regenerate the views without doing a full sync.

## Command line usage
- `make status` &mdash; show every tagged task grouped by status.
- `make status STATUS=blocked,in-progress` &mdash; limit to specific statuses (comma separated).
- `python3 task_status_view.py --status waiting --status in-progress` &mdash; repeatable flags work the same as the make variable.
- `python3 task_status_view.py --list-sources` &mdash; confirm which files are included; helpful when you start pulling data in from other repos.
- `python3 task_status_view.py --write-files` &mdash; regenerate the persisted files (still prints to the terminal unless you add `--quiet`).

## Importing external tasks into today
Use `import_external_tasks.py` whenever you want to pull tagged tasks from an external file (anything you added in `extra_files`) into `02.1_today.txt`. Targets listed under `import_targets` in `task_sources.json` run automatically as part of `make sync`. Mark any line in an external file with `[t]` (“transfer”) and the importer will move that block into the matching section inside `02.1_today.txt` (using the closest section header unless you override it in the config).

Examples:
- `python3 import_external_tasks.py /Users/joshwardini/Documents/dev/admin/admin.txt --section "Admin"` &mdash; copy `[i]` and `[b]` tasks from that file into the existing **Admin** section.
- `python3 import_external_tasks.py admin --section "Admin" --status transfer --dry-run` &mdash; treat `admin` as the alias (matches entries in `extra_files`), limit to `[t]` tasks, and preview the block without editing the file.
- `python3 import_external_tasks.py --all-configured` &mdash; run every entry defined under `import_targets` (same as `make sync`).

By default the script imports `[i]` + `[b]` items, skips duplicates already present in `02.1_today.txt`, and appends the tasks to the target section (creating it if needed). Set `use_source_section: true` in `import_targets` to drop each `[t]` task under the matching header (or provide a `section_map` to translate names), and add `--allow-duplicates` if you intentionally want repeated items. This gives you a quick way to promote work from other repositories into the main “today” plan.

## Syncing project-specific todos (and outputs)
If other repos already have their own `todo.md`, add them to `task_sources.json`:

```json
{
  "extra_files": [
    "../shotmart/app/todo.md",
    "/Users/joshwardini/dev/serpwatch/notes.md"
  ],
  "glob_patterns": [
    "/Users/joshwardini/dev/**/TODOS/*.md"
  ],
  "status_outputs": [
    {
      "path": "03_in_progress_status.txt",
      "title": "In Progress (incl. Blocked)",
      "statuses": ["in-progress", "blocked"]
    },
    {
      "path": "03_blocked.txt",
      "title": "Blocked",
      "statuses": ["blocked"]
    }
  ],
  "import_targets": [
    {
      "name": "admin",
      "source": "/Users/joshwardini/Documents/dev/admin/admin.txt",
      "use_source_section": true,
      "statuses": ["transfer"],
      "section_map": {
        "Admin": "Admin",
        "Finance": "Tax"
      }
    }
  ]
}
```

Paths can be absolute or relative to this repo and you can mix-and-match globs. After editing the config, rerun `make status` and those external files get folded into the same filtered view. The `status_outputs` list defines which files are written when you pass `--write-files`, and `import_targets` controls which files get promoted into `02.1_today.txt` during `make sync` (each target can specify its own section/status filters and section mapping). This keeps every status change (`[i]`, `[b]`, `[x]`, `[t]`, etc.) in sync without having to re-copy text into `projects/`.
