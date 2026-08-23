.PHONY: test validate summary

test:
	python -m unittest discover -s tests

validate:
	python scripts/validate_results.py

summary:
	python scripts/summarize_results.py
