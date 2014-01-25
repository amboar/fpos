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

transform_choices = [ "anz", "commbank", "stgeorge" ]

def transform_commbank(csv):
    # Commbank format:
    #
    # Date,Amount,Description,Balance
    def _gen():
        for l in csv:
            yield l[:3]
    return _gen()

def transform_anz(csv):
    # Identity transform, ANZ's format meets IR:
    #
    # Date,Amount,Description
    return csv

def transform_stgeorge(csv):
    # St George Bank, first row is header
    #
    # Date,Description,Debit,Credit,Balance
    #
    # Discard header
    next(csv)
    def _gen():
        for l in csv:
            yield [l[0], (-1 * float(l[2])) if l[2] else l[3] , l[1]]
    return _gen()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("form", metavar="FORM", choices=transform_choices)
    parser.add_argument("--input", metavar="FILE", type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument("--output", metavar="FILE", type=argparse.FileType('w'), default=sys.stdout)
    return parser.parse_args()

def main():
    args = parse_args()
    try:
        assert args.form in transform_choices
        source = globals()["transform_{}".format(args.form)](csv.reader(args.input))
        sink = csv.writer(args.output)
        for row in source:
            sink.writerow(row)
    finally:
        args.input.close()
        args.output.close()

if __name__ == "__main__":
    main()
