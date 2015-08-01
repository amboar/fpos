#!/usr/bin/python3
#
#    Applies a time window to a budget IR document
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
from datetime import datetime as dt
from collections import defaultdict
from .core import date_fmt, month_fmt

cmd_description = \
        """Outputs an IR document containing only transactions inside a
        specified date range. The range is specified through the --start and
        --end options, and takes a date specification of the form "mm/yyyy".
        The date range is half open to the right, that is, the --start value is
        inclusive and the --end value is exclusive. Neither option need be
        specified, in which case there is no bound"""

cmd_help = \
        """Output transactions between specified months from a given IR document"""

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    parser.add_argument("infile", metavar="INPUT", type=argparse.FileType('r'),
            help="The document to window")
    parser.add_argument("outfile", metavar="OUTPUT", type=argparse.FileType('w'),
            help="The file to write the windowed transactions")
    parser.add_argument("--start", metavar="DATE", type=str,
            help="The start month and year, in the form 'mm/yyyy'")
    parser.add_argument("--end", metavar="DATE", type=str,
            help="The end month and year (exclusive), in the form 'mm/yyyy'")
    # parser.add_argument("--length", type=int)
    return [ parser ] if subparser else parser.parse_args()

def gen_span_oracle(start, end):
    o_true = lambda x: True
    oracle = defaultdict(lambda : o_true)
    if None is start and None is end:
        return o_true
    if None is not start:
        oracle["start"] = lambda x: x >= dt.strptime(start, month_fmt)
    if None is not end:
        oracle["end"] = lambda x: x < dt.strptime(end, month_fmt)
    return lambda x: oracle["start"](x) and oracle["end"](x)

def window(start, end, source):
    in_span = gen_span_oracle(start, end)
    def _gen():
        for e in source:
            if in_span(dt.strptime(e[0], date_fmt)):
                yield e
    return _gen()

def main(args=None):
    if args is None:
        args = parse_args()
    try:
        r = csv.reader(args.infile)
        w = csv.writer(args.outfile)
        w.writerows(window(args.start, args.end, r))
    finally:
        args.outfile.close()

if __name__ == "__main__":
    main()
