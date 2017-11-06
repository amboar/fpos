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
from pystrgrp import Strgrp
import math
from .core import categories
from .core import money
from .ann import DescriptionAnn

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
    def __init__(self, fuzzer=None):
        self._strgrp = Strgrp()
        self._grpanns = {}

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

    def _request_match(self, description, haystack):
        index = None
        need = True

        nota = len(haystack)
        print("Which description best matches '{}'?".format(description))
        print()
        for i, needle in enumerate(haystack):
            print("({})\t{}".format(i, needle.key()))
        print("({})\tNone of the above".format(nota))
        print()

        while need:
            result = input("Select: ")
            try:
                index = int(result)
                need = not (0 <= index <= nota)
                if need:
                    print("Invalid value: {}".format(index))
            except ValueError:
                print("Not a number: '{}'".format(result))
                need = True

        if index == nota:
            return None

        return haystack[index]

    def _split_heap(self, heap):
        i = None
        for i, grpbin in enumerate(heap):
            if grpbin.is_acceptible(self._strgrp):
                if grpbin not in self._grpanns:
                    self._grpanns[grpbin] = DescriptionAnn.load(grpbin.key())
            else:
                break
        return heap[:i], heap[i:]

    def train(self, description, needle, needles, hay):
        # Black magic follows: Hacky attempt at training NNs.
        for straw in hay: 
            if needle.ready['reject']:
                break
            needle.reject(straw)
            needle.accept(description)

        while not needle.ready['accept']:
            needle.accept(description)
            needle.accept(needle.description)

        for ann in needles:
            if ann != needle:
                # For the unlucky needles, use the description for negative
                # training
                while not ann.is_ready():
                    ann.reject(description)
                    # Also train on the initial description
                    ann.accept(ann.description)

    def find_group(self, description):
        # Check for an exact match, don't need fuzzy behaviour if we have one 
        grpbin = self._strgrp.grp_exact(description)
        if grpbin is not None:
            print("Got exact match for '{}'".format(description))
            return grpbin

        # Use a binary output NN trained for each group to determine
        # membership. Leverage the groups generated with strgrp as training
        # sets, with user feedback to break ambiguity

        # needles is the set of groups breaking the strgrp fuzz threshold.
        # These are the candidates groups for the current description.
        needles, hay = self._split_heap(self._strgrp.grps_for(description))
        if len(needles) == 0:
            print("Found no needles for '{}' in the haystack!".format(description))
            return None

        # Score the description using each group's NN, to see if we find a
        # single candidate among the needles. If we do then we assume this is
        # the correct group
        anns = [ self._grpanns[grpbin] for grpbin in needles ]
        scores = [ ann.run(description) for ann in anns ]
        print("Found needles: {}".format(', '.join(x.key() for x in needles)))
        # FIXME: 0.5
        passes = [ x > 0.5 for x in scores ]
        ready = [ ann.is_ready() for ann in anns ]
        if all(ready) and sum(passes) == 1:
            i = passes.index(True)
            self.train(description, anns[i], anns, [grp.key() for grp in hay])
            print("Found one needle '{}' for '{}' in the haystack".format(needles[i].key(), description))
            return needles[i]
        else:
            print("All ready? {}. Passing? {}".format(all(ready), sum(passes)))

        # Otherwise get user input
        match = self._request_match(description, needles)

        # None means no group was matched an a new one should be created
        if match is None:
            return None

        # Otherwise, if the user confirmed membership of the description to a
        # candidate group, if the NN correctly predicted the membership then
        # mark it as ready to use
        i = needles.index(match)
        self.train(description, anns[i], anns, [grp.key() for grp in hay])

        # FIXME: Maybe iterate the group and accept() on some good descriptions
        # to keep the training balance? Otherwise reject()s will dominate.

        # FIXME: Also call reject() for some of the remaining chaff values
        return match

    def classify(self, description):
        return self._tag_for(self.find_group(description))

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

    def add(self, entry, category, group=None):
        te = TaggedEntry(entry, category)
        if group is None:
            self._strgrp.grp_new(entry.description, te)
        else:
            group.add(entry.description, te)

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
                t.add(entry, category, group)
            except ValueError:
                # Category isn't known, output remains empty to
                # trigger user input
                pass
        if category is None:
            # Haven't yet determined the category, require user input
            group = t.find_group(entry.description)
            category = t.categorize(entry, group, confirm)
            assert None is not category
            t.add(entry, category, group)
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
