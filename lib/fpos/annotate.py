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
from lcs import lcs
import math
from .core import categories
from .core import money

cmd_description = \
        """Annotates transactions in an IR document with category information.
        The output IR is intended for the visualise subcommand. Any
        transactions that are already categorised as used as training to make
        suggestions for those which are not annotated."""
cmd_help = \
        """Associate categories with transactions, so that visualise can graph
        spending"""

def normal_lcs(a, b, la=None, lb=None):
    if not la:
        la = len(a)
    if not lb:
        lb = len(b)
    return 2 * lcs(a, b) / ( la + lb )

def fuzzy_match(a, b, t):
    la = len(a)
    lb = len(b)
    r = la / lb if lb > la else lb / la
    if t <= r:
        return t <= normal_lcs(a, b, la, lb)
    else:
        return False

class _ThresholdGroup(object):
    def __init__(self, threshold, key, tag=None):
        self.threshold = threshold
        self.key = key
        self.count = 1
        self.tagged = {}
        if tag:
            self.tag(key, tag)

    def guess(self, text):
        if fuzzy_match(self.key, text, self.threshold):
            if len(self.tagged) > 0:
                t = max(((v.score(text), k) for k, v in self.tagged.items()), key=lambda x: x[0])
                return t[1]
        return None

    def tag(self, text, tag):
        if tag not in self.tagged:
            self.tagged[tag] = _TaggedList(text, tag)
        else:
            tl = self.tagged[tag]
            tl.add(text)
            self.count += 1

class _TaggedList(object):
    def __init__(self, key, tag=None, debug=False):
        self.key = key
        self.tag = tag
        self._score = 0
        self._sum = 0
        self._count = 1
        self.debug = debug
        if self.debug:
            self.members = [ key ]

    def score(self, text, member=None):
        if not member:
            member = self.key
        return normal_lcs(member, text) * self._score

    def add(self, text):
        self._sum += normal_lcs(text, self.key)
        self._count += 1
        self._score = self._sum / self._count
        if self.debug:
            self.members.append(text)

class _LcsTagger(object):
    def __init__(self, threshold=0.75):
        self._groups = []
        self._pending = None
        self._threshold = threshold

    def _sort(self):
        self._groups.sort(key=lambda x: x.count, reverse=True)

    def _find_group_guess(self, text):
        for group in self._groups:
            guess = group.guess(text)
            if guess:
                return group, guess
        return None, None

    def classify(self, text, tag=None):
        group, guess = self._find_group_guess(text)
        if guess:
            if tag:
                group.tag(text, tag)
                self._sort()
            else :
                self._pending = (text, group)
            return guess
        tg = _ThresholdGroup(self._threshold, text, tag)
        self._groups.append(tg)
        return None

    def pending(self):
        return self._pending is not None

    def tag(self, tag):
        if self._pending:
            self._pending[1].tag(self._pending[0], tag)
            self._pending = None
            self._sort()

class _Tagger(object):
    def __init__(self, fuzzer=None):
        self._learnt = {}
        self._fuzzer = fuzzer

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

    def categorize(self, date, amount, description, confirm=False):
        need = True
        category = None
        fmtargs = ("Spent" if 0 > float(amount) else "Earnt",
                money(abs(float(amount))),
                date,
                description)
        print("{} ${!s} on {!s}: {!s}".format(*fmtargs))
        while need:
            guess = None
            if description in self._learnt:
                guess = self._learnt[description]
            if guess is None and self._fuzzer:
                guess = self._fuzzer.classify(description)
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
        if category is not None:
            self._learnt[description] = category
            if self._fuzzer.pending():
                self._fuzzer.tag(category)
        return category

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
    parser.add_argument('--fuzzy', default=False, action="store_true",
            help="Do fuzzy matching of descriptions to help classification")
    return None if subparser else parser.parse_args()

def main(args=None):
    if args is None:
        args = parse_args()
    try:
        r = csv.reader(args.infile, dialect='excel')
        w = csv.writer(args.outfile, dialect='excel')
        # The fuzzy matcher is always created, but only used against the
        # classified entries if --fuzzy is specified. Otherwise, it's only used
        # against entries that aren't explicitly classified.
        f = _LcsTagger()
        t = _Tagger(f)
        for entry in r:
            if 0 == len(entry):
                # Skip empty lines
                continue
            output = []
            if 4 == len(entry):
                # Fourth column is category, check that it's known
                try:
                    t.resolve_category(entry[3])
                    if args.fuzzy:
                        f.classify(entry[2], entry[3])
                    output.extend(entry)
                except ValueError:
                    # Category isn't known, output remains empty to
                    # trigger user input
                    pass
            if 0 == len(output):
                # Haven't yet determined the category, require user input
                output.extend(entry)
                output.append(t.categorize(*entry, confirm=args.confirm))
                print()
            w.writerow(output)
    finally:
        args.infile.close()
        args.outfile.close()

if __name__ == "__main__":
    main()
