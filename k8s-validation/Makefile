PY=.venv/bin/python
SESSION?=s20261031
.PHONY: all setup tests baseline smoke run clean
all: tests baseline smoke
	@echo 'STOP: author smoke approval required. Main is disabled.'
setup:
	$(PY) setup.py
tests:
	$(PY) verify_tests.py
baseline:
	$(PY) run.py setup --session $(SESSION)
smoke:
	$(PY) run.py smoke --session $(SESSION)
run:
	$(PY) main_runner.py
clean:
	@echo 'No evidence is deleted. Infrastructure cleanup requires explicit cluster ownership verification.'

.PHONY: resume-main analyze-main
resume-main:
	$(PY) main_runner.py --resume
analyze-main:
	$(PY) analyze.py
