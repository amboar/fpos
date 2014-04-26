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
import sys
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

def find_category(needle):
    candidates = []
    for element in categories:
        if needle.lower() in element.lower():
            candidates.append(element)
    n = len(candidates)
    if 0 == n:
        raise ValueError("Couldn't match {!s} with any categories".format(needle))
    elif 1 == n:
        return candidates[0]
    else:
        raise ValueError("%s matched multiple candidates: {!s}".format(candidates))

def resolve_category(needle):
    try:
        index = int(needle)
        return categories[index]
    except ValueError:
        return find_category(needle)

def categorize(date, amount, description, learnt=None, confirm=False):
    if learnt is None:
        learnt = {}
    need = True
    category = None
    fmtargs = ("Spent" if 0 > float(amount) else "Earnt",
            money(abs(float(amount))),
            date,
            description)
    print("{} ${!s} on {!s}: {!s}".format(*fmtargs))
    while need:
        guess = learnt[description] if description in learnt else None
        prompt = "Category [{!s}]: ".format("?" if guess is None else guess)
        raw = input(prompt).strip()
        if "" == raw:
            need = None is guess
            category = guess
            if not need:
                assert description in learnt
        elif "?" == raw:
            print()
            print(*categories, sep='\n')
            print()
        else:
            try:
                category = resolve_category(raw)
                need = False
            except ValueError:
                print("Couldn't determine category from {}".format(raw))
        if not need and confirm:
            assert category is not None
            confirmation = input("Confirm {} [y/N]: ".format(category)).strip()
            need = "y" != confirmation.lower()
    if category is not None:
        learnt[description] = category
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
        for entry in r:
            if 0 == len(entry):
                # Skip empty lines
                continue
            output = []
            if 4 == len(entry):
                # Fourth column is category, check that it's known
                try:
                    learnt[entry[2]] = resolve_category(entry[3])
                    output.extend(entry)
                except ValueError:
                    # Category isn't known, output remains empty to
                    # trigger user input
                    pass
            if 0 == len(output):
                # Haven't yet determined the category, require user input
                output.extend(entry)
                output.append(categorize(*entry, learnt=learnt, confirm=args.confirm))
            w.writerow(output)
            print()
    finally:
        args.infile.close()
        args.outfile.close()

if __name__ == "__main__":
    main()
