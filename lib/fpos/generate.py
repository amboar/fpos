#!/usr/bin/python3
#
#    Generates a fake document for testing purposes
#    Copyright (C) 2014  Andrew Jeffery <andrew@aj.id.au>
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
import random
import csv
import sys
from datetime import datetime, timedelta
from .core import categories
from .core import date_fmt, month_fmt
from .core import money

def name():
    return __name__.split('.')[-1]

def parse_args(parser=None):
    wasNone = parser is None
    if wasNone:
        parser = argparse.ArgumentParser()
    aa = parser.add_argument
    aa("--cash-mean", default=60)
    aa("--cash-stdev", default=10)
    aa("--cash-period", default=3)
    aa("--commitment-mean", default=1000)
    aa("--commitment-stdev", default=100)
    aa("--commitment-period", default=14)
    aa("--dining-mean", default=50)
    aa("--dining-stdev", default=50)
    aa("--dining-period", default=3)
    aa("--education-mean", default=100)
    aa("--education-stdev", default=10)
    aa("--education-period", default=30)
    aa("--entertainment-mean", default=100)
    aa("--entertainment-stdev", default=50)
    aa("--entertainment-period", default=5)
    aa("--health-mean", default=50)
    aa("--health-stdev", default=100)
    aa("--health-period", default=14)
    aa("--home-mean", default=200)
    aa("--home-stdev", default=200)
    aa("--home-period", default=14)
    aa("--income-mean", default=1000)
    aa("--income-stdev", default=10)
    aa("--income-period", default=7)
    aa("--internal-mean", default=0)
    aa("--internal-stdev", default=0)
    aa("--internal-period", default=0)
    aa("--shopping-mean", default=200)
    aa("--shopping-stdev", default=50)
    aa("--shopping-period", default=7)
    aa("--transport-mean", default=60)
    aa("--transport-stdev", default=10)
    aa("--transport-period", default=7)
    aa("--utilities-mean", default=100)
    aa("--utilities-stdev", default=100)
    aa("--utilities-period", default=14)
    aa("--start", default="01/2014")
    aa("--end", default="04/2014")
    aa("--annotate", dest="annotate", action="store_true")
    aa("--no-annotate", dest="annotate", action="store_false")
    if wasNone:
        return parser.parse_args()
    return None

def gen_days(days, period, stdev):
    rand = random.Random()
    day = rand.gauss(period, stdev)
    while day < days:
        yield day
        day += rand.gauss(period, stdev)

def create_document(args):
    start = datetime.strptime(args.start, month_fmt)
    end = datetime.strptime(args.end, month_fmt)
    days = (end - start).days
    rand = random.Random()
    document = []
    for cat in (c for c in categories if "Internal" != c):
        mean = getattr(args, "{}_mean".format(cat.lower()))
        stdev = getattr(args, "{}_stdev".format(cat.lower()))
        period = getattr(args, "{}_period".format(cat.lower()))
        for day in gen_days(days, period, 2):
            date = (start + timedelta(day)).strftime(date_fmt)
            value = money(( 1 if "Income" == cat else -1 ) * rand.gauss(mean, stdev))
            row = [date, value, "{} description".format(cat)]
            if args.annotate:
                row.append(cat)
            document.append(row)
    return document

def main(args=None):
    if args is None:
        args = parse_args()
    csv.writer(sys.stdout).writerows(create_document(args))

if __name__ == "__main__":
    main()
