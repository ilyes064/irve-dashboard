PY ?= python3

.PHONY: install data refresh run test reference clean

install:            ## create a virtualenv and install pinned dependencies
	$(PY) -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

data:               ## download the IRVE file once (cached) and build data/processed/
	$(PY) scripts/download_data.py

refresh:            ## force a fresh download of the latest IRVE file
	$(PY) scripts/download_data.py --force

run:                ## start the dashboard on http://localhost:8501
	streamlit run app.py

test:               ## unit tests for the cleaning rules (no download needed)
	$(PY) -m pytest -q tests

reference:          ## rebuild bundled population table + department boundaries
	$(PY) scripts/build_reference.py

clean:              ## remove downloaded and processed data
	rm -f data/raw/*.csv data/raw/manifest.json data/processed/*
