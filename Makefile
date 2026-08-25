.PHONY: preflight test package tree
preflight:
	python scripts/preflight.py

test:
	cd apps/backend && pytest -q

package:
	python scripts/package_project.py

tree:
	python scripts/project_tree.py
