PYTHON ?= python

.PHONY: install verify publication-check score reproduce test

install:
	$(PYTHON) -m pip install -r requirements-lock.txt

verify:
	$(PYTHON) scripts/verify_release.py

publication-check:
	$(PYTHON) scripts/verify_release.py --publication

score:
	$(PYTHON) scripts/score_predictions.py --check

reproduce:
	$(PYTHON) scripts/score_predictions.py --check
	$(PYTHON) scripts/reproduce_analysis.py --check
	$(PYTHON) scripts/build_publication_tables.py --check
	$(PYTHON) scripts/reproduce_mixed_effects.py --check

test:
	$(PYTHON) -m pytest -p no:cacheprovider
