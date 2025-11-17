.PHONY: sync priority status

sync:
	@if [ -n "$$(git status --porcelain)" ]; then \
		git add -A; \
		git commit -m "Auto-commit before sync"; \
		git push; \
	fi
	python3 sync_completed.py
	python3 task_status_view.py --write-files --quiet

priority:
	python3 filter_priority.py

status:
	python3 task_status_view.py $(if $(STATUS),--status $(STATUS),)
