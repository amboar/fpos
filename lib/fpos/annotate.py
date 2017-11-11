#!/usr/bin/python3
#
#    Annotates budget IR with categories
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
import collections
import math
from .core import categories
from .core import money
from .ann import CognitiveStrgrp

cmd_description = \
        """Annotates transactions in an IR document with category information.
        The output IR is intended for the visualise subcommand. Any
        transactions that are already categorised as used as training to make
        suggestions for those which are not annotated."""
cmd_help = \
        """Associate categories with transactions, so that visualise can graph
        spending"""

Entry = collections.namedtuple("Entry", ("date", "amount", "description"))
TaggedEntry = collections.namedtuple("TaggedEntry", ("entry", "tag"))

class _Tagger(object):
    def __init__(self):
        self.grouper = CognitiveStrgrp()

    @staticmethod
    def find_category(needle, haystack):
        candidates = []
        for element in haystack:
            if needle.lower() in element.lower():
                candidates.append(element)
        n = len(candidates)
        if 0 == n:
            raise ValueError("Couldn't match {!s} with any categories".format(needle))
        elif 1 == n:
            return candidates[0]
        else:
            raise ValueError("%s matched multiple candidates: {!s}".format(candidates))

    @staticmethod
    def resolve_category(needle):
        try:
            index = int(needle)
            return categories[index]
        except ValueError:
            return _Tagger.find_category(needle, categories)

    def _bin2hist(self, grpbin):
        return collections.Counter(x.value().tag for x in grpbin)

    def _tag_for(self, grpbin):
        if grpbin is None:
            return None
        return max(self._bin2hist(grpbin).items(), key=lambda x: x[1])[0]

    def classify(self, description):
        return self._tag_for(self.find_group(description))

    def find_group(self, description):
        return self.grouper.find_group(description)

    def categorize(self, entry, group, confirm=False):
        need = True
        category = None
        fmtargs = ("Spent" if 0 > float(entry.amount) else "Earnt",
                money(abs(float(entry.amount))),
                entry.date,
                entry.description)
        print("{} ${!s} on {!s}: {!s}".format(*fmtargs))
        while need:
            guess = None
            guess = self._tag_for(group)
            prompt = "Category [{!s}]: ".format("?" if guess is None else guess)
            raw = input(prompt).strip()
            if "" == raw:
                need = None is guess
                category = guess
            elif "?" == raw:
                print()
                print(*categories, sep='\n')
                print()
            else:
                try:
                    category = self.resolve_category(raw)
                    need = False
                except ValueError:
                    print("Couldn't determine category from {}".format(raw))
            if not need and confirm:
                assert category is not None
                confirmation = input("Confirm {} [y/N]: ".format(category)).strip()
                need = "y" != confirmation.lower()
        return category

    def insert(self, entry, category, group=None):
        te = TaggedEntry(entry, category)
        self.grouper.insert(entry.description, te, group)

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    parser.add_argument('infile', metavar="INPUT", type=argparse.FileType('r'),
            help="The IR document containing un-categorised transactions")
    parser.add_argument('outfile', metavar="OUTPUT", type=argparse.FileType('w'),
            help="The IR document to which to write annotated transactions")
    parser.add_argument('--confirm', default=False, action="store_true",
            help="Prompt for confirmation after each entry has been annotated with a category")
    return [ parser ] if subparser else parser.parse_args()

def annotate(src, confirm=False):
    annotated = []
    t = _Tagger()
    for row in src:
        if 0 == len(row):
            # Skip empty lines
            continue
        entry = Entry(*row[:3])
        category = None
        if 4 == len(row):
            # Fourth column is category, check that it's known
            try:
                category = t.resolve_category(row[3])
                group = t.find_group(entry.description)
                t.insert(entry, category, group)
            except ValueError:
                # Category isn't known, output remains empty to
                # trigger user input
                pass
        if category is None:
            # Haven't yet determined the category, require user input
            group = t.find_group(entry.description)
            category = t.categorize(entry, group, confirm)
            assert None is not category
            t.insert(entry, category, group)
            print()
        output = []
        output.extend(entry)
        output.append(category)
        annotated.append(output)
    return annotated

def main(args=None):
    if args is None:
        args = parse_args()
    try:
        r = csv.reader(args.infile, dialect='excel')
        w = csv.writer(args.outfile, dialect='excel')
        w.writerows(annotate(r, args.confirm))
    finally:
        args.infile.close()
        args.outfile.close()

if __name__ == "__main__":
    main()
