#!/usr/bin/python3
#
#    Transforms a transaction document into budget IR
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
import sys
from .core import money

transform_choices = [ "anz", "commbank", "stgeorge" ]

def _take_three(src):
    def _gen():
        for l in src:
            yield [ l[0], money(float(l[1])), l[2] ]
    return _gen()

def transform_commbank(csv):
    # Commbank format:
    #
    # Date,Amount,Description,Balance
    return _take_three(csv)

def transform_anz(csv):
    # Identity transform, ANZ's format meets IR:
    #
    # Date,Amount,Description
    return _take_three(csv)

def transform_stgeorge(csv):
    # St George Bank, first row is header
    #
    # Date,Description,Debit,Credit,Balance
    #
    # Discard header
    next(csv)
    def _gen():
        for l in csv:
            yield [l[0], money((-1.0 * float(l[2])) if l[2] else float(l[3])), l[1]]
    return _gen()

def name():
    return __name__.split(".")[-1]

def parse_args(parser=None):
    wasNone = parser is None
    if wasNone:
        parser = argparse.ArgumentParser()
    parser.add_argument("form", metavar="FORM", choices=transform_choices)
    parser.add_argument("--input", metavar="FILE", type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument("--output", metavar="FILE", type=argparse.FileType('w'), default=sys.stdout)
    if wasNone:
        return parser.parse_args()
    return None

def transform(form, source):
    assert form in transform_choices
    return globals()["transform_{}".format(form)](source)

def main(args=None):
    if args is None:
        args = parse_args()
    try:
        csv.writer(args.output).writerows(transform(args.form, csv.reader(args.input)))
    finally:
        args.input.close()
        args.output.close()

if __name__ == "__main__":
    main()
