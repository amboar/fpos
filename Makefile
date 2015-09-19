SETUP_FLAGS:=
PYTHON:=python3
PIP:=pip
VIRTUALENV:=virtualenv
VE_NAME:=ve

build build_py build_ext build_clib build_scripts install install_lib install_headers install_scripts install_data sdist register bdist bdist_dumb bdist_wininst: configure
	$(PYTHON) setup.py $@ $(SETUP_FLAGS)

$(VE_NAME):
	$(VIRTUALENV) --python=$(PYTHON) $(VE_NAME)

pip:
	$(PIP) install -r requirements.txt

install-user: SETUP_FLAGS+=--user
install-user: install

check upload:
	$(PYTHON) setup.py $@ $(SETUP_FLAGS)

clean: SETUP_FLAGS+=--all
clean:
	rm -f ext/config.h
	$(PYTHON) setup.py $@ $(SETUP_FLAGS)

configure: ext/config.h

ext/config.h: ext/configurator
	$< > ext/config.h

ext/configurator: CFLAGS=-g3 -ggdb -Wall -Wstrict-prototypes -Wold-style-definition -Wmissing-prototypes -Wmissing-declarations -Wpointer-arith -Wwrite-strings -Wundef -DCCAN_STR_DEBUG=1
ext/configurator: LDLIBS=-lrt
ext/configurator: ext/configurator.o

.PHONY: dependencies clean pip