#!/usr/bin/python3
#
#    Coalesces transaction descriptions based on similarity
#    Copyright (C) 2015  Andrew Jeffery <andrew@aj.id.au>
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

from .ann import CognitiveGroups, DynamicGroups
import csv
import argparse

cmd_description = \
        """Coalesce transaction descriptions"""

cmd_help = cmd_description

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    parser.add_argument('infile', metavar="INPUT", type=argparse.FileType('r'),
            help="The IR document containing un-categorised transactions")
    return [ parser ] if subparser else parser.parse_args()

import re

def cdesc(reader):
    with DynamicGroups() as grouper:
        for r in reader:
            grouper.add(re.sub(r"\s{2,}", " ", row[2]), r)
        return [ [ x.value() for x in g ] for g in grouper ]

def main(args=None):
    if args is None:
        args = parse_args()
    reader = csv.reader(args.infile, dialect='excel')
    cdesc(reader)

if __name__ == "__main__":
    main()
