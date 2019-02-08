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
import collections
import pkg_resources
import io
from datetime import datetime, timedelta
from .core import categories
from .core import date_fmt, month_fmt
from .core import money

cmd_description = \
        """Generate fake transaction data in a date range, for testing purposes"""

def name():
    return __name__.split('.')[-1]

def parse_args(subparser=None):
    if subparser is None:
        parser = argparse.ArgumentParser(name(), description=cmd_description)
    else:
        parser = subparser.add_parser(name(), description=cmd_description, help=cmd_description)
    aa = parser.add_argument
    aa("--cash-mean", default=60, type=float)
    aa("--cash-noise", default=10, type=float)
    aa("--cash-period", default=3, type=int)
    aa("--commitment-mean", default=1000, type=float)
    aa("--commitment-noise", default=100, type=float)
    aa("--commitment-period", default=14, type=int)
    aa("--dining-mean", default=50, type=float)
    aa("--dining-noise", default=20, type=float)
    aa("--dining-period", default=3, type=int)
    aa("--education-mean", default=100, type=float)
    aa("--education-noise", default=10, type=float)
    aa("--education-period", default=30, type=int)
    aa("--entertainment-mean", default=100, type=float)
    aa("--entertainment-noise", default=50, type=float)
    aa("--entertainment-period", default=5, type=int)
    aa("--health-mean", default=100, type=float)
    aa("--health-noise", default=25, type=float)
    aa("--health-period", default=14, type=int)
    aa("--home-mean", default=200, type=float)
    aa("--home-noise", default=75, type=float)
    aa("--home-period", default=14, type=int)
    aa("--income-mean", default=3000, type=float)
    aa("--income-noise", default=50, type=float)
    aa("--income-period", default=14, type=int)
    aa("--internal-mean", default=0, type=float)
    aa("--internal-noise", default=0, type=float)
    aa("--internal-period", default=0, type=int)
    aa("--shopping-mean", default=200, type=float)
    aa("--shopping-noise", default=50, type=float)
    aa("--shopping-period", default=7, type=int)
    aa("--transport-mean", default=60, type=float)
    aa("--transport-noise", default=10, type=float)
    aa("--transport-period", default=7, type=int)
    aa("--utilities-mean", default=100, type=float)
    aa("--utilities-noise", default=20, type=float)
    aa("--utilities-period", default=14, type=int)
    aa("--start", default="01/2014")
    aa("--end", default="04/2014")
    aa("--no-annotate", default=True, dest="annotate", action="store_false")
    return [ parser ] if subparser else parser.parse_args()

def gen_days(days, period, stdev):
    rand = random.Random()
    day = rand.gauss(period, stdev)
    while day < days:
        yield day
        day += period + round(rand.gauss(1, 1))

# name: Name of trader
# use_sid: True if the trader uses a store ID in descriptions, false otherwise
# sid_pool: The pool of store IDs to use in transaction descriptions
# use_tid: True if the trader uses a transaction ID in descriptions, false otherwise
Trader = collections.namedtuple("Trader", ("name", "category", "use_sid",
"sid_pool", "use_tid"))

Provider = collections.namedtuple("Provider", ("name", "use_prefix",
"prefix_pool", "use_suffix", "suffix_pool"))

savings_provider = Provider("Savings", False, [], False, [])
visa_provider = Provider("Visa", True, ["VISA DEBIT PURCHASE CARD"], False, [])

def gen_trader_lookup(traders):
    lookup = {}
    for trader in traders:
        if trader.category not in lookup:
            lookup[trader.category] = []
        lookup[trader.category].append(trader)
    return lookup

def gen_traders(cat_n, words, r_src=None):
    if r_src is None:
        r_src = random.Random()
    traders = []
    for cat, n in cat_n.items():
        #n = r_src.randint(1, 10)
        n = 1
        n_sids = r_src.randint(0, n)
        n_tids = r_src.randint(0, n)
        traders.extend(gen_category_traders(n, cat, words, n_sids, n_tids))
    return traders

def gen_trader_name(words, n_words, r_src=None):
    if r_src is None:
        r_src = random.Random()
    return " ".join(r_src.sample(words, n_words))[:25]

def gen_category_traders(n, category, words, n_sids, n_tids, r_src=None):
    traders = []
    if r_src is None:
        r_src = random.Random()
    for i in range(n):
        n_words = r_src.randint(3, 6)
        name = gen_trader_name(words, n_words, r_src)
        pool_size = (0 == (i + n_sids) % (n / n_sids)) if n_sids > 0 else False
        sid_pool = r_src.sample(words, pool_size)
        use_tid = (0 == (i + n_tids) % (n / n_tids)) if n_tids > 0 else False
        traders.append(Trader(name, category, (0 < pool_size), sid_pool, use_tid))
    return traders

def gen_tid(tid_src=None):
    if tid_src is None:
        tid_src = random.Random()
    return "[{:08d}]".format(tid_src.randrange(0, 10**8))

def gen_description(trader, provider, r_src=None):
    if r_src is None:
        r_src = random.Random()
    tdesc = []
    if provider.use_prefix:
        tdesc.append(r_src.choice(provider.prefix_pool))
    tdesc.append(trader.name)
    if trader.use_sid:
        tdesc.append(r_src.choice(trader.sid_pool))
    if trader.use_tid:
        tdesc.append(gen_tid(r_src))
    if provider.use_suffix:
        tdesc.append(r_src.choice(provider.suffix_pool))
    return " ".join(tdesc)

def get_words(n, r_src=None):
    if r_src is None:
        r_src = random.Random()
    stream = pkg_resources.resource_stream(__name__, 'propernames')
    with io.TextIOWrapper(stream) as wordio:
        words = wordio.readlines()
    r_src.shuffle(words)
    selected = words[:n]
    stripped = list(x.strip() for x in selected)
    return stripped

def create_document(args):
    r_src = random.Random()
    #cat_n = { c : r_src.randint(0, 10) for c in categories if c not in ( "Income", "Internal" ) }
    cat_n = { c : 1 for c in categories if c not in ( "Income", "Internal" ) }
    words = get_words(5000, r_src)
    traders = gen_traders(cat_n, words)
    traders.append(Trader(gen_trader_name(words, 5), "Income", False, [], False))
    trader_lookup = gen_trader_lookup(traders)
    providers = ( savings_provider, visa_provider )
    start = datetime.strptime(args.start, month_fmt)
    end = datetime.strptime(args.end, month_fmt)
    days = (end - start).days
    document = []
    for cat in trader_lookup.keys():
        mean = getattr(args, "{}_mean".format(cat.lower()))
        noise = getattr(args, "{}_noise".format(cat.lower()))
        period = getattr(args, "{}_period".format(cat.lower()))
        flow = 1 if "Income" == cat else -1
        for day in gen_days(days, period, 2):
            date = (start + timedelta(day)).strftime(date_fmt)
            value = money(flow * mean + noise * r_src.gauss(0, 1))
            trader = r_src.choice(trader_lookup[cat])
            provider = savings_provider if cat in ("Income", "Cash") else r_src.choice(providers)
            row = [date, value, gen_description(trader, provider, r_src)]
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
