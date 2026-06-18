VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

venv:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"

test:
	$(VENV)/bin/pytest -q

download:
	$(PY) -m permatiles download

render:
	$(PY) -m permatiles render

pack:
	$(PY) -m permatiles pack

all:
	$(PY) -m permatiles all
