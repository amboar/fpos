#!/usr/bin/python3
#
#    Transforms a transaction document into budget IR
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
from datetime import datetime
import dateutil.parser as dp
from .core import money
from .core import date_fmt
from itertools import chain
import re

transform_choices = sorted([ "auto", "anz", "commbank", "stgeorge", "nab", "nab-2018", "bankwest", "woolworths" ])
cmd_description = \
        """Not all bank CSV exports are equal. fpos defines an intermediate
        representation (IR) which each of the tools expect as input to eventually
        generate spending graphs. The job of the transform subcommand is to
        take each bank's CSV transaction schema and convert it to fpos' IR.
        Typically transform is the first command used in the fpos chain."""
cmd_help = \
        """Transform a transaction CSV document into fpos intermediate
        representation"""

def _take_three_anz(src):
    def _gen():
        for l in src:
            yield [ l[0], money(float(l[1])), l[2] ]
    return _gen()

def _take_three_commbank(src):
    def _gen():
        for l in src:
            # At some point Commbank started putting spaces before the sign.
            # Not sure what motivated the change, but remove the space if it's
            # present so float() can interpret the string.
            amount = float(l[1].replace(" ", ""))
            yield [ l[0], money(amount), l[2] ]
    return _gen()

_EMPTY = "empty"
_DATE = "date"
_NUMBER = "number"
_STRING = "string"

sense = {}
sense[(_DATE, _NUMBER, _STRING, _NUMBER)] = "commbank"

sense[(_DATE, _NUMBER, _STRING)] = "anz"

sense[(_DATE, _STRING, _EMPTY, _NUMBER, _NUMBER)] = "stgeorge"
sense[(_DATE, _STRING, _NUMBER, _EMPTY, _NUMBER)] = "stgeorge"

sense[(_DATE, _NUMBER, _NUMBER, _EMPTY, _STRING, _STRING, _NUMBER)] = "nab"
sense[(_DATE, _NUMBER, _EMPTY, _EMPTY, _STRING, _EMPTY, _NUMBER)] = "nab"
sense[(_DATE, _NUMBER, _EMPTY, _EMPTY, _STRING, _EMPTY, _NUMBER)] = "nab"
sense[(_DATE, _NUMBER, _EMPTY, _EMPTY, _STRING, _STRING, _NUMBER)] = "nab"
sense[(_DATE, _NUMBER, _NUMBER, _EMPTY, _STRING, _STRING, _NUMBER, _EMPTY)] = "nab"
sense[(_DATE, _NUMBER, _EMPTY, _EMPTY, _STRING, _STRING, _NUMBER, _EMPTY)] = "nab"
sense[(_DATE, _NUMBER, _EMPTY, _EMPTY, _STRING, _EMPTY, _NUMBER, _EMPTY)] = "nab"

sense[(_DATE, _STRING, _EMPTY, _EMPTY, _STRING, _STRING, _STRING)] = "nab-2018"

sense[(_EMPTY, _NUMBER, _DATE, _STRING, _NUMBER, _EMPTY, _EMPTY, _NUMBER, _STRING)] = "bankwest"
sense[(_EMPTY, _NUMBER, _DATE, _STRING, _EMPTY, _NUMBER, _EMPTY, _NUMBER, _STRING)] = "bankwest"
sense[(_EMPTY, _NUMBER, _DATE, _STRING, _EMPTY, _EMPTY, _NUMBER, _NUMBER, _STRING)] = "bankwest"

sense[(_DATE, _STRING, _EMPTY, _NUMBER, _NUMBER, _STRING, _STRING, _EMPTY)] = "woolworths"
sense[(_DATE, _STRING, _NUMBER, _EMPTY, _NUMBER, _STRING, _STRING, _EMPTY)] = "woolworths"
sense[(_DATE, _STRING, _NUMBER, _EMPTY, _EMPTY, _STRING, _STRING, _EMPTY)] = "woolworths"

def _is_empty(x):
    return x is None or "" == x

def _is_date(x):
    try:
        dp.parse(x)
        return True
    except ValueError:
        pass
    return False

def _is_number(x):
    try:
        float(x)
        return True
    except ValueError:
        pass
    return False

def _compute_cell_type(x):
    if _is_empty(x):
        return _EMPTY
    elif _is_number(x):
        return _NUMBER
    elif _is_date(x):
        return _DATE
    else:
        if x is None:
            raise ValueError("Parameter is None when it should not be")
        return _STRING

def _compute_type_tuple(row):
    return tuple(_compute_cell_type(x) for x in row)

def _sense_form(row, debug=False):
    if debug:
        print(row)
    tt = _compute_type_tuple(row)
    if debug:
        print(tt)
    return sense[tt]

def _acquire_form(row):
    guess = None
    try:
        guess = _sense_form(row)
    except KeyError:
        pass
    need = True
    form = None
    while need:
        raw = input("Input type [{}]: ".format(guess if guess else "?")).strip()
        if "" == raw:
            need = None is guess
            form = guess
        elif "?" == raw:
            print()
            print(*transform_choices, sep="\n")
            print()
        elif raw in transform_choices:
            return raw
    return form

def transform_auto(csv, confirm):
    first = next(csv)
    form = _acquire_form(first, confirm) if confirm else _sense_form(first)
    return transform(form, chain([first], csv))

def transform_commbank(csv, args=None):
    # Commbank format:
    #
    # Date,Amount,Description,Balance
    return _take_three_commbank(csv)

def transform_anz(csv, args=None):
    # Identity transform, ANZ's format meets IR:
    #
    # Date,Amount,Description
    return _take_three_anz(csv)

def transform_stgeorge(csv, args=None):
    # St George Bank, first row is header
    #
    # Date,Description,Debit,Credit,Balance
    def _gen():
        for l in csv:
            yield [ l[0], money((-1.0 * float(l[2])) if l[2] else float(l[3])), l[1] ]
    return _gen()

_nab_date_fmt = "%d-%b-%y"

def transform_nab(csv, args=None):
    # NAB format:
    #
    # Date, Amount, Ref #,, Description, Merchant, Remaining Balance
    # 28-Apr-14,-64.67,071644731756,,CREDIT CARD PURCHASE,BP CRAFERS 9125 CRAFERS,-169.28,
    def _gen():
        for l in csv:
            if l:
                ir_date = datetime.strptime(l[0], _nab_date_fmt).strftime(date_fmt)
                ir_amount = money(float(l[1]))
                ir_description = " ".join(e for e in l[4:6] if (e is not None and "" != e ))
                yield [ ir_date, ir_amount, ir_description ]
    return _gen()


_nab_2018_date_fmt = "%d %b %y"

def transform_nab_2018(csv, args=None):
    # NAB 2018 format:
    #
    # Date, Amount,,,Transfer Type, Description, Remaining Balance
    # "07 Feb 18","-12.00",,,"TRANSFER DEBIT","INTERNET TRANSFER   Lunch","+500.00"
    #
    # The date format is different to 2018, and there's one less column. Also
    # flips the bird to data types, everything is a string. And now
    # currency-style value formatting means locale-specific separators such as
    # ',' get in the way of parsing the transaction value.
    def _gen():
        for l in csv:
            if l:
                ir_date = datetime.strptime(l[0], _nab_2018_date_fmt).strftime(date_fmt)
                # Deal with currency-style strings by cutting out everything
                # except the sign, digits the decimal point
                ir_amount = money(float(re.sub(r'[^\d.+-]', '', l[1])))
                ir_description = " ".join(e for e in l[4:6] if (e is not None and "" != e ))
                yield [ ir_date, ir_amount, ir_description ]
    return _gen()

def transform_bankwest(csv, args=None):
    # Bankwest format:
    #
    # BSB Number,Account Number,Transaction Date,Narration,Cheque,Debit,Credit,Balance,Transaction Type
    # ,5229 8079 0109 8683,27/10/2014,"CALTRAIN TVM             SAN CARLOS   CA85450784297436040013768           5.25US",,6.00,,116.32,WDL
    def _gen():
        for l in csv:
            yield [l[2], money((-1.0 * float(l[5])) if l[5] else float(l[6])), l[3][1:-1]]
    return _gen()

def transform_woolworths(csv, args=None):
    # Woolworths Money format:
    #
    # Transaction Date,Description,Debit,Credit,Balance,Category,Subcategory,Notes
    # 20 Mar 2016,WOOLWORTHS 5518 TORRENSVILLE,46.4,,,Food & Drink,Groceries,
    # 19 Mar 2016,WOOLWORTHS 5518 TORRENSVILLE,6.15,,NaN,Food & Drink,Groceries,
    _woolies_date_fmt = "%d %b %Y"

    def _gen():
        for line in csv:
            if len(line[2]) > 0:
                # Debit
                amount = money(-float(line[2]))
            else:
                # Credit
                amount = money(float(line[3]))
            date = datetime.strptime(line[0], _woolies_date_fmt).strftime(date_fmt)
            yield [date, amount, line[1]]
    return _gen()

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    parser.add_argument("--form", metavar="FORM", choices=transform_choices, default="auto",
            help="The CSV schema used by the input file, named after associated banks")
    parser.add_argument("--confirm", default=False, action="store_true",
            help="In auto mode, prompt to confirm the selected transformation")
    parser.add_argument("infile", metavar="INPUT", type=argparse.FileType('r'), default=sys.stdin,
            help="The source file whose contents should be transformed to fpos IR")
    parser.add_argument("outfile", metavar="OUTPUT", type=argparse.FileType('w'), default=sys.stdout,
            help="The destination file to which the IR will be written")
    return [ parser ] if subparser else parser.parse_args()

def transform(form, source, confirm=False):
    assert form in transform_choices, "form {} not in {}".format(form, transform_choices)
    t = globals()["transform_{}".format(form.replace("-", "_"))]
    g = (e for e in source if len(e) > 0 and not e[0].startswith("#"))
    if "auto" == form:
        return t(g, confirm)
    return t(g)

def main(args=None):
    if args is None:
        args = parse_args()
    try:
        csv.writer(args.outfile).writerows(
                transform(args.form, csv.reader(args.infile), args.confirm))
    finally:
        args.infile.close()
        args.outfile.close()

if __name__ == "__main__":
    main()
