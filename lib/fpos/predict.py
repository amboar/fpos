#!/usr/bin/python3
#
#    Forecasts future spending based on cycles in historical data
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
import pystrgrp
import csv
from datetime import datetime, timedelta
from matplotlib import pyplot as plt
from itertools import chain, cycle, islice
import numpy as np

cmd_description = \
        """Predict spending based on past habits"""
cmd_help = cmd_description

def pd(datestr):
    return datetime.strptime(datestr, "%d/%m/%Y")

def group_deltas(group):
    """ group_deltas(group) -> list(int)

    Calculate the difference in days between subsequent spend group entries.
    The length of the returned list is one less than the length of the input
    list, or zero length if the input list is zero length. The input member
    list is sorted by ascending date order before the deltas are calculated.
    """
    sm = sorted(group, key=lambda x: pd(x[0]))
    return [ ( pd(e[0]) - pd(sm[p][0]) ).days for p, e in enumerate(sm[1:]) ]

def group_delta_bins(deltas):
    """ group_delta_bins(deltas) -> list(int)

    Takes a value sequence as input and generates a list of length
    max(deltas) - 1, where the value at each index of the list is a count of
    the occurrences of the index value in the deltas input. The zeroth index is
    then discarded as it counts multiple spends for the spend group on a single
    day; this isn't of interest as the minimum resolution of the calculation is
    one day.
    """
    return np.bincount(deltas)[1:] # Discard the zero bin

def period(bins):
    """ period(bins) -> int

    Takes a bincount list as input and returns the last non-zero bin index of
    the spend group.
    """
    if 0 == len(bins):
        raise ValueError("No bins provided")
    for i, e in enumerate(reversed(bins)):
        if e > 0:
            return len(bins) - i

def pmf(bins):
    """ pmf(bins) -> list(float)

    Takes a bincount list as input and returns the associated probability mass
    function. If the returned list is v, then sum(v) == 1.0.
    """
    n = sum(bins)
    return [ (v / n) for v in bins ]

def expected_spend(mf, mean):
    """ expected_spend(mf, mean) -> list(float)

    Given a reified mass function (i.e., the list of bins representing the
    probability mass function), distribute the provided mean across the bins of
    the mass function. If the returned list is v, then sum(v) == mean.
    """
    return [ (v * mean) for v in mf ]

def last(members):
    """ last(members) -> datetime

    Find the most recent date in a spend group.
    """
    return max(pd(x[0]) for x in members)

def align(bins, n, delta):
    """ align(bins, n, delta) -> list(float)

    Redistribute unspent predictions over the remaining predicted bins in the
    spending period.

    Predictions of future spending are anchored in time at the date of the last
    entry in the spend group. The spending prediction is probabilistic, in that
    the mean value of the spend group is distributed across the probability
    mass function of the differences in consecutive, date-sorted spend group
    entries. As time progresses without an expense falling into the spend group,
    we advance through the predicted spending sequence and possibly over some
    bins which predict a spend. As we know an expense hasn't occurred up until
    now for the spend group any predicted spends between the anchor point and
    now have not eventuated, but we still expect to spend the mean value. Thus,
    we redistribute the value in the mis-predicted bins over the remaining
    predicted bins to retain the property that the sum of the predicted values
    is equal to the mean.
    """
    # Value of entries residing in bins less than delta
    s = sum(bins[:delta])
    # Redistribution value, the mean of the ignored bins relative to the
    # remaining bins
    m = (s / (n - s))
    # Recalculate the spend distribution with respect to delta and the
    # redistribution value
    return [ 0 if 0 == e else (e + m) for e in bins[delta:] ]

def group_forecast(members, date, debug=False):
    """ group_forecast(members, date) -> seq(float)

    Predict future spending based on spending groups and the probability mass
    function of the deltas of sorted group member dates. Progression in time is
    accounted for by redistributing mis-predicted spends across the remaining
    predicted spends for the calculated spend period. If no spend occurs in the
    calculated spend period then future predictions are cancelled.
    """
    bins = group_delta_bins(group_deltas(members))
    n = sum(bins)
    m = sum(float(e[1]) for e in members) / (n + 1)
    d = (date - last(members)).days
    if 0 == len(bins):
        return []
    else:
        p = period(bins)
        if p < d:
            if debug:
                fmt = "Dropped m={} as \"{}\": p={}, d={}"
                msg = fmt.format(m, members[0][2], p, d)
                print(msg)
            return []
    dhs = expected_spend(pmf(bins), m)
    adhs = align(dhs, n, d)
    return chain(adhs, cycle(dhs))

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    parser.add_argument('infile', metavar="INPUT", type=argparse.FileType('r'),
            help="The IR document containing un-categorised transactions")
    return None if subparser else parser.parse_args()

def bottoms(data):
    bots = [ 0 ]
    for v in data[:-1]:
        bots.append(bots[-1] + v)
    return bots

def forecast(groups, date, length=32):
    """ forecast(groups, date, length) -> list(float), list(float)

    Predict cashflow in terms of spending (first return value) and income
    (second return value) using the history embodied in the `groups` parameter.
    Each element of the returned lists represents the amount spent or earnt on
    the day relative to the day following the `date` parameter, that is the
    zeroth entry of either list represents the amount spent or earnt on the day
    after `date`. Each returned list has a length governed by the `length`
    parameter.
    """
    spend = [ 0 ] * length
    income = [ 0 ] * length
    noise_values = [ float(b[0][1]) for b in groups if len(b) == 1 ]
    noise = sum(noise_values) / len(noise_values)
    for g in ( g for g in groups if len(g) > 1 ):
        for k, v in enumerate(islice(group_forecast(g, date), length)):
            d = spend if v < 0 else income
            d[k] += v
    return [ (v + noise) for v in spend ], income

def graph_bar_cashflow(groups, last):
    fl = 31 # forecast length
    gl = fl + 2 # graph length
    ey, iy = forecast(groups, last, fl)
    bs = bottoms(list(chain(*zip(ey, iy))))
    ex = [ x + 0.1 for x in range(1, len(ey) + 1)]
    be = plt.bar(ex, ey, bottom=bs[::2], color="r", width=0.3)
    ix = [ x + 0.6 for x in range(1, len(iy) + 1)]
    bi = plt.bar(ix, iy, bottom=bs[1::2], color="b", width=0.3)
    plt.axhline(0, color="black")
    majors = list(range(1, gl, 7))
    labels = [ (last + timedelta(i)).strftime("%d/%m/%y") for i in majors ]
    plt.xticks(majors, labels, rotation=33)
    plt.xlim(0, gl)
    plt.grid(axis="x", which="both")
    plt.grid(axis="y", which="major")
    plt.title("Cashflow Forecast")
    plt.legend((be, bi), ("Forecast Expenditure", "Forecast Income"))
    plt.show()

def main(args=None):
    if args is None:
        args = parse_args()
    grouper = pystrgrp.Strgrp()
    reader = csv.reader(args.infile, dialect='excel')
    current = None
    for r in reader:
        if len(r) >= 4 and not "Internal" == r[3]:
            grouper.add(r[2], r)
            current = pd(r[0]) if not current else max(pd(r[0]), current)
    graph_bar_cashflow([ list(i.data() for i in g) for g in grouper ], current, 32)
