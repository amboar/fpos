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
import sys
from datetime import datetime as dt
from collections import defaultdict
from core import date_fmt, month_fmt

def name():
    return __name__.split(".")[-1]

def parse_args(parser=None):
    wasNone = parser is None
    if wasNone:
        parser = argparse.ArgumentParser()
    parser.add_argument("source", metavar="FILE", type=argparse.FileType('r'))
    parser.add_argument("--sink", metavar="FILE", type=argparse.FileType('w'),
            default=sys.stdout)
    parser.add_argument("--start", metavar="DATE", type=str)
    parser.add_argument("--end", metavar="DATE", type=str)
    parser.add_argument("--length", type=int)
    if wasNone:
        return parser.parse_args()
    return None

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
        r = csv.reader(args.source)
        w = csv.writer(args.sink)
        w.writerows(window(args.start, args.end, r))
    finally:
        args.sink.close()

if __name__ == "__main__":
    main()
