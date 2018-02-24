SETUP_FLAGS:=
PYTHON:=python3
PIP:=pip3
NOSETESTS_NAMES:=nosetests-3.5 nosetests-3.4 nosetests-3.3 nosetests3 nosetests
NOSETESTS:=$(firstword $(foreach exec,$(NOSETESTS_NAMES),$(shell which $(exec) 2> /dev/null)))
COVERAGE:=$(shell which coverage 2> /dev/null)
VIRTUALENV:=virtualenv
VE_NAME:=.venv

build build_py build_ext build_clib build_scripts install_lib install_headers install_scripts install_data sdist register bdist bdist_dumb bdist_wininst: configure
	$(PYTHON) setup.py $@ $(SETUP_FLAGS)

install_internal: configure
	$(PYTHON) setup.py install $(SETUP_FLAGS)

$(VE_NAME):
	$(VIRTUALENV) --python=$(PYTHON) --system-site-packages $(VE_NAME)

pip:
	$(PIP) install --user --upgrade -r requirements.txt

pip-$(VE_NAME):
	$(PIP) install --upgrade -r requirements.txt

install: SETUP_FLAGS+=--user
install: install_internal

install-$(VE_NAME): install_internal

check:
	$(PYTHON) setup.py $@ $(SETUP_FLAGS)
	$(if $(NOSETESTS),,$(error NOSETESTS is not defined, couldn\'t find any of $(NOSETESTS_NAMES)))
	$(NOSETESTS)

check-code-coverage:
	$(if $(COVERAGE),,$(error COVERAGE is not defined))
	$(COVERAGE) run --source=fpos lib/tests/__init__.py || true
	$(COVERAGE) html

upload:
	$(PYTHON) setup.py $@ $(SETUP_FLAGS)

clean: SETUP_FLAGS+=--all
clean:
	$(RM) ext/config.h
	$(PYTHON) setup.py $@ $(SETUP_FLAGS)
	$(RM) -r .coverage htmlcov

configure: ext/config.h

ext/config.h: ext/configurator
	$< > ext/config.h

ext/configurator: CFLAGS=-g3 -ggdb -Wall -Wstrict-prototypes -Wold-style-definition -Wmissing-prototypes -Wmissing-declarations -Wpointer-arith -Wwrite-strings -Wundef -DCCAN_STR_DEBUG=1
ext/configurator: ext/configurator.o

.PHONY: clean pip pip-$(VE_NAME) install install-user install-$(VE_NAME) check check-code-coverage
