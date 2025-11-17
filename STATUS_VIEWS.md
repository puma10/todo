# Status-Only Views

`task_status_view.py` surfaces anything tagged with `[i]`, `[b]`, `[w]`, `[d]`, or `[x]` across the daily files, tomorrow/next-week lists, `03_in_progress`, and everything in `projects/`. It keeps the section headings so you can still see the project context.

## Persisted files
- `03_in_progress_status.txt` &mdash; all `[i]` tasks plus `[b]` tasks (blocked counts as in progress).  
- `03_blocked.txt` &mdash; only the `[b]` items.

`make sync` now runs `python3 task_status_view.py --write-files --quiet`, so those files refresh automatically whenever you sync. Run the same command manually anytime you want to regenerate the views without doing a full sync.

## Command line usage
- `make status` &mdash; show every tagged task grouped by status.
- `make status STATUS=blocked,in-progress` &mdash; limit to specific statuses (comma separated).
- `python3 task_status_view.py --status waiting --status in-progress` &mdash; repeatable flags work the same as the make variable.
- `python3 task_status_view.py --list-sources` &mdash; confirm which files are included; helpful when you start pulling data in from other repos.
- `python3 task_status_view.py --write-files` &mdash; regenerate the persisted files (still prints to the terminal unless you add `--quiet`).

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
  ]
}
```

Paths can be absolute or relative to this repo and you can mix-and-match globs. After editing the config, rerun `make status` and those external files get folded into the same filtered view. The `status_outputs` list defines which files are written when you pass `--write-files`, so you can add more (waiting, delegated, etc.) or point to different filenames if you want to keep them elsewhere. This keeps every status change (`[i]`, `[b]`, `[x]`, etc.) in sync without having to re-copy text into `projects/`.
