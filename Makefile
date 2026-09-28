# MICCAI index — reproducibility entry points.
#
# The pipeline is designed so any contributor can validate and reproduce the
# generated artifacts without network access, and a maintainer can run the
# full update locally with one command.

PYTHON ?= python3
PIP    ?= $(PYTHON) -m pip
PYTHONPATH := src

# Default scope is the broad all-years index to keep parity with the existing
# README content. Override on the command line:
#   make build SCOPE=miccai-2026 MODE=strict TRACKS=workshops
SCOPE  ?= miccai-all-years
MODE   ?= broad
TRACKS ?= all

.PHONY: help setup install test test-unit test-integration test-property \
        lint validate validate-offline render build build-offline report \
        clean clean-cache clean-data

help:
	@echo "Available targets:"
	@echo "  setup              - install Python dependencies"
	@echo "  test               - run the full test suite"
	@echo "  test-unit          - run unit tests only"
	@echo "  test-integration   - run integration tests only"
	@echo "  test-property      - run property-based tests only"
	@echo "  validate           - validate README + canonical data (online)"
	@echo "  validate-offline   - validate README + canonical data (no network)"
	@echo "  render             - render README from existing canonical data"
	@echo "  build              - run full pipeline (network required)"
	@echo "  build-offline      - render README from existing data only"
	@echo "  report             - print analytics over existing dataset"
	@echo "  clean              - remove generated artifacts"
	@echo "  clean-cache        - remove the cache directory"
	@echo "  clean-data         - remove the canonical dataset (CAUTION)"

setup:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

test-unit:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_*normalization.py' -v
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_classification.py' -v
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_conference_evidence.py' -v
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_validation.py' -v
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_storage.py' -v
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_unit' -v

test-integration:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_integration.py' -v

test-property:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_property.py' -v
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_render.py' -v

validate: validate-offline
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/validate_readme.py

validate-offline:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m miccai_index validate --offline --scope $(SCOPE) --mode $(MODE) --tracks $(TRACKS)

render:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m miccai_index render --scope $(SCOPE) --mode $(MODE) --tracks $(TRACKS)

build:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m miccai_index build --scope $(SCOPE) --mode $(MODE) --tracks $(TRACKS) --verbose

build-offline:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m miccai_index build --scope $(SCOPE) --mode $(MODE) --tracks $(TRACKS) --offline

report:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m miccai_index report --scope $(SCOPE) --mode $(MODE) --tracks $(TRACKS)

clean:
	rm -rf dist/ data/snapshots/ build.log

clean-cache:
	rm -rf .cache/

clean-data:
	rm -f data/papers.jsonl data/repositories.jsonl data/changelog.jsonl