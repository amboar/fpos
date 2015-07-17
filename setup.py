#!/usr/bin/python3

from __future__ import print_function
from distutils.core import setup, Extension
import sys

v = sys.version_info
if v < (3,):
    msg = "FAIL: fpos requires Python 3.x, but setup.py was run using {}.{}.{}"
    print(msg.format(v.major, v.minor, v.micro))
    print("NOTE: Installation failed. Run setup.py using python3")
    sys.exit(1)

pylcs = Extension('pylcs',
    extra_compile_args = [ '-O2' ],
    sources = [ "ext/pylcs.c",
        "ext/lcs.c" ],
    )

pystrgrp = Extension('pystrgrp',
    include_dirs = ['ext'],
    extra_compile_args = [ '-O2', '-fwrapv', '-Wall', '-Wstrict-prototypes' ],
    extra_link_args = [ ],
    sources = [
        "ext/ccan/talloc/talloc.c",
        "ext/ccan/str/str.c",
        "ext/ccan/str/debug.c",
        "ext/ccan/list/list.c",
        "ext/ccan/htable/htable.c",
        "ext/ccan/hash/hash.c",
        "ext/lcs.c",
        "ext/pystrgrp.c",
        "ext/strgrp.c"
        ]
    )

setup(name='fpos',
        version='0.1',
        description='Financial Position',
        author='Andrew Jeffery',
        author_email='andrew@aj.id.au',
        url='https://github.com/amboar/fpos',
        packages=['fpos'],
        package_dir={'' : 'lib'},
        package_data={'fpos' : [ 'propernames' ]},
        scripts=['bin/fpos'],
        ext_modules = [pylcs, pystrgrp],
        license='GPLv3')
