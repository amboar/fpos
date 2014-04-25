#!/usr/bin/python3
#
#    Combines multiple budget IR documents into one
#    Copyright (C) 2013  Andrew Jeffery <andrew@aj.id.au>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import csv
import datetime
import hashlib
import itertools
import sys
from .core import date_fmt

def name():
    return __name__.split(".")[-1]

def parse_args(parser=None):
    wasNone = parser is None
    if wasNone:
        parser = argparse.ArgumentParser()
    parser.add_argument("database", metavar="DATABASE", type=argparse.FileType('r'))
    parser.add_argument("updates", metavar="FILE", type=argparse.FileType('r'), nargs='*')
    parser.add_argument('--out', metavar="FILE", type=argparse.FileType('w'),
            default=sys.stdout)
    if wasNone:
        return parser.parse_args()
    return None

def digest_entry(entry):
    s = hashlib.sha1()
    for element in entry[:3]:
        s.update(str(element).encode("UTF-8"))
    return s.hexdigest()

def combine(sources):
    def _gen():
        entries = dict((digest_entry(x), x)
                for db in sources for x in db if 3 <= len(x))
        datesort = lambda x: datetime.datetime.strptime(x[0], date_fmt).date()
        costsort = lambda x: float(x[1])
        descsort = lambda x: x[2]
        for v in sorted(sorted(sorted(entries.values(), key=descsort), key=costsort), key=datesort):
            yield v
    return _gen()

def main(args=None):
    if args is None:
        args = parse_args()
    try:
        readables = itertools.chain(args.updates, (args.database,))
        csv.writer(args.out).writerows(combine(csv.reader(x) for x in readables))
    finally:
        args.database.close()
        for e in args.updates:
            e.close()
        args.out.close()

if __name__ == "__main__":
    main()
