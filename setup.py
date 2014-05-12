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

lcs = Extension('lcs', sources = ['ext/lcs.c'])
setup(name='fpos',
        version='0.1',
        description='Financial Position',
        author='Andrew Jeffery',
        author_email='andrew@aj.id.au',
        url='https://github.com/amboar/fpos',
        packages=['fpos'],
        package_dir={'' : 'lib'},
        scripts=['bin/fpos'],
        ext_modules = [lcs],
        license='GPLv3')

