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
from .groups import DynamicGroups

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

class TagIO(object):
    def __init__(self, categories):
        self.categories = categories

    def banner(self, entry):
        fmtargs = ("Spent" if 0 > float(entry.amount) else "Earnt",
                money(abs(float(entry.amount))),
                entry.date,
                entry.description)
        print("{} ${!s} on {!s}: {!s}".format(*fmtargs))

    def resolve(self, guess):
        prompt = "Category [{!s}]: ".format("?" if guess is None else guess)
        return input(prompt).strip()

    def confirm(self, category):
        return input("Confirm {} [y/N]: ".format(category)).strip()

    def help(self):
        print()
        print(*self.categories, sep='\n')
        print()

    def warn(self, message):
        print(message)

class _Tagger(object):
    def __init__(self, grouper=None, io=None):
        self.grouper = DynamicGroups() if grouper is None else grouper
        self.io = TagIO(categories) if io is None else io

    def __enter__(self):
        self.grouper.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.grouper.__exit__(exc_type, exc_value, traceback)

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
        self.io.banner(entry)
        while need:
            guess = self._tag_for(group)
            raw = self.io.resolve(guess)
            if "" == raw:
                need = None is guess
                category = guess
            elif "?" == raw:
                self.io.help()
            else:
                try:
                    category = self.resolve_category(raw)
                    need = False
                except ValueError:
                    self.io.warn("Couldn't determine category from {}".format(raw))
            if not need and confirm:
                assert category is not None
                need = "y" != self.io.confirm(category).lower()
        return category

    def insert(self, entry, category, group=None):
        te = TaggedEntry(entry, category)
        self.grouper.insert(entry.description, te, group)

    def dump(self):
        return [ [ g.key(), [ i.value() for i in g ] ] for g in self.grouper ]

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

import re

def annotate(src, confirm=False, tagger=None):
    annotated = []
    if tagger is None:
        tagger = _Tagger()
    with tagger:
        try:
            for row in src:
                if 0 == len(row):
                    # Skip empty lines
                    continue
                cooked = Entry(row[0], row[1], row[2])
                category = None
                if 4 == len(row):
                    # Fourth column is category, check that it's known
                    try:
                        group = tagger.find_group(cooked.description)
                        category = tagger.resolve_category(row[3])
                        tagger.insert(cooked, category, group)
                    except ValueError:
                        # Category isn't known, output remains empty to
                        # trigger user input
                        pass
                if category is None:
                    # Haven't yet determined the category, require user input
                    group = tagger.find_group(cooked.description)
                    category = tagger.categorize(cooked, group, confirm)
                    assert None is not category
                    tagger.insert(cooked, category, group)
                    print()
                output = []
                # Retain the raw description string in the output
                output.extend(row[:3])
                output.append(category)
                annotated.append(output)
        except EOFError:
            pass
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
