.PHONY: test validate summary manifest check-manifest

test:
	python -m unittest discover -s tests

validate:
	python scripts/validate_results.py

summary:
	python scripts/summarize_results.py

manifest:
	python scripts/gen_manifest.py

check-manifest:
	python scripts/gen_manifest.py --check
