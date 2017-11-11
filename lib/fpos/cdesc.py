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

from .ann import CognitiveStrgrp
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

def sanitise(value, strip=None):
    if strip is None:
        strip = [ "VISA DEBIT PURCHASE CARD", "EFTPOS", "\\" ]
    for phrase in strip:
        value = value.replace(phrase, " ")
    return value


def print_tokens(group):
    tokencount = {}
    for e in group:
        for t in e[0].split():
            if t not in tokencount:
                tokencount[t] = 0 
            tokencount[t] += 1
    print(tokencount)

def retain_common_intra_tokens(group):
    count = {}
    for e in group:
        local = set()
        for t in sanitise(e[0]).split():
            if t not in count:
                count[t] = 0
            if t not in local:
                count[t] += 1
                local.add(t)
    n_common = max(count.values())
    keep = { k for k, v in count.items() if v == n_common }
    common_group = []
    for e in group:
        kept = []
        for t in sanitise(e[0]).split():
            if t in keep:
                kept.append(t)
        kept_str = " ".join(kept) if len(kept) > 1 else group[0][0]
        common_group.append([ kept_str, e[1] ])
    return common_group

def retain_unique_inter_tokens(groups):
    rev_descs = sorted(groups, key=lambda x: x[0][::-1])
    prev = None
    for g in rev_descs:
        if None is prev:
            prev = g[0]
        else:
            if g[0].endswith(prev):
                g[0] = prev
            else:
                prev = g[0]
    return rev_descs

def cdesc(reader):
    grouper = CognitiveStrgrp()
    for r in reader:
        grouper.add(" ".join(sanitise(r[2]).split()).upper(), r)
    groups = [ [ [x.key(), x.value()] for x in g ] for g in grouper ]
    intra_common = []
    for g in groups:
        intra_common.append(retain_common_intra_tokens(g))
    grouper2 = CognitiveStrgrp()
    for g in intra_common:
        for m in g:
            grouper2.add(m[0].upper(), m[1])
    groups2 = [ [ g.key(), [ x.value() for x in g ] ] for g in grouper2 ]
    inter_unique = retain_unique_inter_tokens(groups2)
    grouper3 = CognitiveStrgrp()
    for g in inter_unique:
        for m in g[1]:
            grouper3.add(g[0].upper(), m)
    groups3 = [ [ g.key(), [ x.value() for x in g ] ] for g in grouper3 ]
    return [ x[1] for x in groups3 ]

def main(args=None):
    if args is None:
        args = parse_args()
    reader = csv.reader(args.infile, dialect='excel')
    cdesc(reader)

if __name__ == "__main__":
    main()
