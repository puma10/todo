# Status-Only Views

`task_status_view.py` surfaces anything tagged with `[i]`, `[b]`, `[w]`, `[d]`, or `[x]` across the daily files, tomorrow/next-week lists, `03_in_progress`, and everything in `projects/`. It keeps the section headings so you can still see the project context.

## Command line usage
- `make status` &mdash; show every tagged task grouped by status.
- `make status STATUS=blocked,in-progress` &mdash; limit to specific statuses (comma separated).
- `python3 task_status_view.py --status waiting --status in-progress` &mdash; repeatable flags work the same as the make variable.
- `python3 task_status_view.py --list-sources` &mdash; confirm which files are included; helpful when you start pulling data in from other repos.

## Syncing project-specific todos
If other repos already have their own `todo.md`, add them to `task_sources.json`:

```json
{
  "extra_files": [
    "../shotmart/app/todo.md",
    "/Users/joshwardini/dev/serpwatch/notes.md"
  ],
  "glob_patterns": [
    "/Users/joshwardini/dev/**/TODOS/*.md"
  ]
}
```

Paths can be absolute or relative to this repo and you can mix-and-match globs. After editing the config, rerun `make status` and those external files get folded into the same filtered view. This keeps every status change (`[i]`, `[b]`, `[x]`, etc.) in sync without having to re-copy text into `projects/`.

