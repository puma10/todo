.PHONY: sync priority

sync:
	@if [ -n "$$(git status --porcelain)" ]; then \
		git add -A; \
		git commit -m "Auto-commit before sync"; \
		git push; \
	fi
	python3 sync_completed.py

priority:
	python3 filter_priority.py

