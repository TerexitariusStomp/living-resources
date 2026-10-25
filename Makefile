# SPDX-License-Identifier: AGPL-3.0-or-later
# Makefile — living-resources
#
# `make test` runs the e2e suites under guile when it is on PATH; where it
# is not, the same target degrades to static checks that still exercise
# what can be exercised: parenthesis balance across every .scm, SPDX
# headers, a compile+sim of the firmware skeleton, and the rego package
# declarations. `make check-custom-budget` counts first-party lines
# against the adopted-OSS seam stubs — the ≤5% rule's bookkeeping.
#
# (The scheme linter rides as printf args piped to `python3 -` because GNU
# make strips leading whitespace on recipe continuation lines — a heredoc
# loses the program's indentation.)

GUILE     ?= $(shell command -v guile 2>/dev/null)
PYTHON3   ?= python3
SCM_TESTS := tests/e2e/sensing-cell.scm tests/e2e/refused-lanes.scm tests/e2e/write-lanes.scm tests/e2e/connectome-witness.scm
ADOPTED_STUBS := adapters/reticulum.scm adapters/mic.scm adapters/camera.scm adapters/sonar.scm adapters/c4d.scm adapters/weather.scm adapters/connectome.scm
FIRST_PARTY := module/living adapters tests/e2e firmware deploy/policies/living
CUSTOM_BUDGET ?= 4000

test:
ifeq ($(strip $(GUILE)),)
	@echo "guile not found — running static checks (e2e needs guile on PATH)"
	@printf '%s\n' \
	  'import sys, glob' \
	  'def bal(s):' \
	  '    d = 0; i = 0; st = 0' \
	  '    while i < len(s):' \
	  '        c = s[i]' \
	  '        if st == 1:' \
	  '            if c == chr(92): i += 1' \
	  '            elif c == chr(34): st = 0' \
	  '        elif st == 2:' \
	  '            if c == chr(10): st = 0' \
	  '        elif st == 3:' \
	  '            if s[i:i+2] == "|#": st = 0; i += 1' \
	  '        else:' \
	  '            if c == ";": st = 2' \
	  '            elif c == chr(34): st = 1' \
	  '            elif s[i:i+2] == "#|": st = 3; i += 1' \
	  '            elif s[i:i+2] == "#" + chr(92): i += 2' \
	  '            elif s[i:i+2] == "#;": i += 1' \
	  '            elif c == "(": d += 1' \
	  '            elif c == ")":' \
	  '                d -= 1' \
	  '                if d < 0: return -1' \
	  '        i += 1' \
	  '    return d' \
	  'files = sorted(glob.glob("module/**/*.scm", recursive=True) + glob.glob("adapters/*.scm") + glob.glob("tests/**/*.scm", recursive=True))' \
	  'bad = [f for f in files if bal(open(f).read()) != 0]' \
	  'for f in bad: print("unbalanced parens:", f)' \
	  'missing = [f for f in files if "SPDX-License-Identifier: AGPL" not in open(f).read()[:200]]' \
	  'for f in missing: print("missing SPDX header:", f)' \
	  'if bad or missing: sys.exit(1)' \
	  'print("scm static check ok: %d files balanced, SPDX present" % len(files))' \
	  | $(PYTHON3) -
	@$(PYTHON3) -m py_compile firmware/node/main.py
	@$(PYTHON3) firmware/node/main.py
	@grep -q "^package living.lanegate" deploy/policies/living/lane-gate.rego && \
	 grep -q "^package living.consent" deploy/policies/living/consent.rego && \
	 echo "rego policies declared"
	@echo "static checks passed — install guile to run the e2e suites"
else
	@set -e; for t in $(SCM_TESTS); do \
	  echo "── $$t"; \
	  $(GUILE) --no-auto-compile -L module -L . $$t; \
	done
endif

check-custom-budget:
	@$(PYTHON3) -c 'import os,sys; exts=(".scm",".py",".rego"); roots="$(FIRST_PARTY)".split(); files=[os.path.join(dp,f) for r in roots for dp,_,fs in os.walk(r) for f in fs if f.endswith(exts)]+["AGENTS.md","Makefile"]; total=sum(len(open(f,errors="replace").readlines()) for f in files if os.path.isfile(f)); stubs=sum(len(open(f).readlines()) for f in "$(ADOPTED_STUBS)".split()); custom=total-stubs; print("adopted-stub LOC: %d | custom non-stub LOC: %d | total: %d | budget: %d" % (stubs,custom,total,$(CUSTOM_BUDGET))); sys.exit(1 if custom>$(CUSTOM_BUDGET) else 0)'

.PHONY: test check-custom-budget
