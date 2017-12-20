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

pystrgrp = Extension('pystrgrp',
    include_dirs = ['ext'],
    extra_compile_args = [ '-O2', '-fwrapv', '-Wall', '-Wstrict-prototypes', '-fopenmp', '-march=native' ],
    extra_link_args = [ '-fopenmp' ],
    sources = [
        "ext/ccan/block_pool/block_pool.c",
        "ext/ccan/hash/hash.c",
        "ext/ccan/heap/heap.c",
        "ext/ccan/htable/htable.c",
        "ext/ccan/likely/likely.c",
        "ext/ccan/list/list.c",
        "ext/ccan/str/debug.c",
        "ext/ccan/strgrp/strgrp.c",
        "ext/ccan/stringmap/stringmap.c",
        "ext/ccan/str/str.c",
        "ext/ccan/take/take.c",
        "ext/ccan/talloc/talloc.c",
        "ext/ccan/tal/str/str.c",
        "ext/ccan/tal/tal.c",
        "ext/ccan/tal/talloc/talloc.c",
        "ext/pystrgrp.c"
        ],
    depends = [ 'ext/config.h' ],
    optional = False
    )

setup(name='fpos',
        version='0.2.2',
        description='Financial Position',
        author='Andrew Jeffery',
        author_email='andrew@aj.id.au',
        url='https://github.com/amboar/fpos',
        packages=['fpos'],
        package_dir={'' : 'lib'},
        package_data={'fpos' : [ 'propernames' ]},
        scripts=['bin/fpos'],
        ext_modules = [ pystrgrp ],
        license='GPLv3')
