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
from .core import categories
from .core import money
from .core import lcs

cmd_description = \
        """Annotates transactions in an IR document with category information.
        The output IR is intended for the visualise subcommand. Any
        transactions that are already categorised as used as training to make
        suggestions for those which are not annotated."""
cmd_help = \
        """Associate categories with transactions, so that visualise can graph
        spending"""

class _TaggedList(object):
    def __init__(self, tag):
        self.tag = tag
        self.members = []

class _LcsTagger(object):
    def __init__(self, threshold=0.75):
        self._groups = []
        self._lookup = {}
        self._threshold = threshold

    @staticmethod
    def normal_lcs(a, b):
        return ( 2 * lcs(a, b) / ( len(a) + len(b) ) )

    def classify(self, text, tag=None):
        for e in self._groups:
            # Just test the first member element of e, as all the members'
            # normalised LCS is greater than the threshold
            nlcs = self.normal_lcs(text, e.members[0])
            if nlcs >= self._threshold:
                e.members.append(text)
                return e.tag
        tl = _TaggedList(tag)
        tl.members.append(text)
        if tl.tag is None:
            self._lookup[text] = tl
        self._groups.append(tl)
        return tl.tag

    def need_tag_for(self, text):
        return text in self._lookup

    def tag(self, text, tag):
        self._lookup[text].tag = tag
        del self._lookup[text]

class _Tagger(object):
    def __init__(self, fuzzer=None):
        self._learnt = {}
        self._fuzzer = fuzzer if fuzzer else _LcsTagger()

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
            if guess is None:
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
            if self._fuzzer.need_tag_for(description):
                self._fuzzer.tag(description, category)
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
    return None if subparser else parser.parse_args()

def main(args=None):
    if args is None:
        args = parse_args()
    learnt = {}
    try:
        r = csv.reader(args.infile, dialect='excel')
        w = csv.writer(args.outfile, dialect='excel')
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
            w.writerow(output)
            print()
    finally:
        args.infile.close()
        args.outfile.close()

if __name__ == "__main__":
    main()
