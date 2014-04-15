#!/usr/bin/python3

from distutils.core import setup

setup(name='fpos',
        version='0.1',
        description='Financial Position',
        author='Andrew Jeffery',
        author_email='andrew@aj.id.au',
        url='https://github.com/amboar/fpos',
        packages=['fpos'],
        package_dir={'' : 'lib'},
        scripts=['bin/fpos'],
        license='GPLv3')

