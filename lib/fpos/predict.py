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
import numpy as np
from datetime import datetime, timedelta
from itertools import chain, cycle, islice
from .core import money
import matplotlib.pyplot as plt

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

def icmf(bins, threshold=0.75):
    """Inverse cumulative probability mass function"""
    s = 0
    for i, v in enumerate(pmf(bins)):
        s += v
        if s > threshold:
            return i
    raise ValueError("Whut?")

def probable_spend(mf, mean):
    """ probable_spend(mf, mean) -> list(float)

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

def align(bins, delta):
    """ align(bins, delta) -> list(float)

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
    r = len([x for x in bins[delta:] if x != 0])
    if 0 == r:
        return [ 0 ] * (len(bins) - delta)
    m = (s / r)
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
    if not members:
        raise ValueError("Requires at least one member in members list")
    bins = group_delta_bins(group_deltas(members))
    mean = sum(float(e[1]) for e in members) / (sum(bins) + 1)
    d = (date - last(members)).days
    if 0 == len(bins):
        return []
    else:
        p = period(bins)
        if p < d:
            if debug:
                fmt = "Dropped mean={} as \"{}\": p={}, d={}"
                msg = fmt.format(mean, members[0][2], p, d)
                print(msg)
            return []
    # Estimate the periodicity using icmf.
    #
    # The goal is to estimate cashflow for around the next 30 days. Some
    # spending patterns are going to have periods of less than 30 days, so we
    # need to cycle our the observed pattern to meet the projection length.
    #
    # A property of using icmf is that the estimated periodicity will likely
    # be less than the full period of the PMF. To account for this  we merge
    # the following cycle of the probability distribution into the current from
    # the index of icmf's periodicity estimate. To paint a picture, imagine
    # the bin distribution is such:
    #
    #    *
    #    *
    #    *
    # ** * *   *
    # ----------
    # 0123456789
    #
    # Giving a PMF of:
    #
    # 00   0   0
    # ..   .   .
    # 11 0 1   1
    # 22 . 2   2
    # 55 5 5   5
    # ----------
    # 0123456789
    #
    # icmf estimates the periodicity as 4, and the code below overlaps the
    # PMF on-top of itself such that each PMF is repeated from bin 4 of the
    # previous:
    #
    # 00  0
    # ..  .0   0
    # 11 01. 0 .
    # 22 .22 . 2
    # 55 555 5 5
    # ----------
    # 0123456789
    mass = pmf(bins)
    interval = icmf(mass)
    overlap = period(mass) - (interval + 1)
    merged_mass = mass[:]
    for i in range(overlap):
        merged_mass[interval + 1 + i] += mass[i]
    ps = probable_spend(merged_mass, mean)
    aps = align(ps, d)
    return chain(aps, cycle(ps[overlap:]))

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    parser.add_argument('infile', metavar="INPUT", type=argparse.FileType('r'),
            help="The IR document containing un-categorised transactions")
    return [ parser ] if subparser else parser.parse_args()

def bottoms(data):
    if not data:
        raise ValueError("Must be at least one element in data")
    bots = [ 0 ]
    for v in data[:-1]:
        bots.append(bots[-1] + v)
    return bots

def forecast(groups, dates, length=32):
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
    # noise values
    nv = [ float(b[0][1]) for b in groups if len(b) <= 2 ]
    ns, ni = 0, 0
    span = (dates[1] - dates[0]).days
    if nv and span:
        ns = sum(v for v in nv if v < 0) / span
        ni = sum(v for v in nv if v > 0) / span
    for g in ( g for g in groups if len(g) > 2 ):
        for k, v in enumerate(islice(group_forecast(g, dates[1]), length)):
            d = spend if v < 0 else income
            d[k] += v
    return [ (v + ns) for v in spend ], [ (v + ni) for v in income ]

def graph_bar_cashflow(groups, dates):
    fl = 31 # forecast length
    gl = fl + 2 # graph length
    ey, iy = forecast(groups, dates, fl)
    bs = bottoms(list(chain(*zip(ey, iy))))
    ex = [ x + 0.1 for x in range(1, len(ey) + 1)]
    be = plt.bar(ex, ey, bottom=bs[::2], color="r", width=0.3)
    ix = [ x + 0.6 for x in range(1, len(iy) + 1)]
    bi = plt.bar(ix, iy, bottom=bs[1::2], color="b", width=0.3)
    plt.axhline(0, color="black")
    majors = list(range(1, gl, 7))
    labels = [ (dates[1] + timedelta(i)).strftime("%d/%m/%y") for i in majors ]
    plt.xticks(majors, labels, rotation=33)
    plt.xlim(0, gl)
    plt.grid(axis="x", which="both")
    plt.grid(axis="y", which="major")
    plt.title("Cashflow Forecast")
    plt.legend((be, bi), ("Forecast Expenditure", "Forecast Income"))
    plt.show()

def print_periodic_expenses(groups, date):
    required_group_size = ( g for g in groups if len(g) > 2 )
    group_bins = ( (g, group_delta_bins(group_deltas(g)))
            for g in required_group_size )
    required_bins_size = ( gb for gb in group_bins
            if 0 < len(gb[1]) )
    keep = ( gb for gb in required_bins_size
            if period(gb[1]) > (date - last(gb[0])).days )
    table = ( (gb[0][0][2],
        len(gb[0]),
        #period(gb[1]),
        icmf(gb[1]),
        sum(float(e[1]) for e in gb[0]) / (sum(gb[1]) + 1))
            for gb in keep )
    ordered = sorted(list(table), key=lambda x: (365 / x[2]) * x[3])
    print("Description | N | Period | Mean Value | Annual Value | Monthly Value")
    for row in ordered:
        annual = (365 / row[2]) * row[3]
        print("{} | {} | {} | {} | {} | {}".format(row[0], row[1], row[2],
            money(row[3]), money(annual), money(annual / 12)))

def main(args=None):
    if args is None:
        args = parse_args()
    grouper = pystrgrp.Strgrp()
    reader = csv.reader(args.infile, dialect='excel')
    dates = [ None, None ]
    for r in reader:
        if len(r) >= 4 and not "Internal" == r[3]:
            grouper.add(r[2], r)
            dates[0] = pd(r[0]) if not dates[0] else min(pd(r[0]), dates[0])
            dates[1] = pd(r[0]) if not dates[1] else max(pd(r[0]), dates[1])
    graph_bar_cashflow([ list(i.data() for i in g) for g in grouper ], dates, 32)
