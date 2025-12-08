.PHONY: sync priority status stats focus

sync:
	@if [ -n "$$(git status --porcelain)" ]; then \
		git add -A; \
		git commit -m "Auto-commit before sync"; \
		git push; \
	fi
	python3 scripts/sync_completed.py
	python3 scripts/import_external_tasks.py --all-configured --quiet
	python3 scripts/task_status_view.py --write-files --quiet

priority:
	python3 scripts/filter_priority.py

status:
	python3 scripts/task_status_view.py $(if $(STATUS),--status $(STATUS),)

stats:
	python3 scripts/task_stats.py

focus:
	python3 scripts/focus_today.py
