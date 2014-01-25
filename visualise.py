#!/usr/bin/python3
#
#    Visualises an annotated budget IR document
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
import copy
import csv
import calendar
from datetime import datetime
import itertools
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import math
from collections import defaultdict
from scipy import polyfit, polyval

categories = [ "Cash", "Commitment", "Dining", "Education", "Entertainment",
"Health", "Home", "Income", "Internal", "Shopping", "Transport", "Utilities" ]

flexible = [ "Cash", "Dining", "Entertainment" ]
fixed = [ x for x in categories if x not in flexible ]

date_fmt = "%d/%m/%Y"
month_fmt = "%m/%Y"

extract_month = lambda x: datetime.strptime(x, date_fmt).strftime("%m/%Y")
extract_week = lambda x: datetime.strptime(x, date_fmt).strftime("%U")
datesort = lambda x : datetime.strptime(x, date_fmt).date()
monthsort = lambda x : datetime.strptime(x, month_fmt).date()
monthname = lambda x : datetime.strptime(x, month_fmt).strftime("%b")

def group_period(reader, extract=extract_month):
    d = defaultdict(list)
    for row in reader:
        d[extract(row[0])].append(row)
    return d

def sum_categories(data):
    summed = dict((x, 0) for x in categories)
    for row in data:
        summed[row[3]] += float(row[1])
    return summed

def sum_expenses(expenses):
    summed = {}
    for m, cs in expenses.items():
        if m not in summed:
            summed[m] = 0
        for v in cs.values():
            summed[m] += v
    return summed

def income(summed):
    d = dict((m, 0) for m in summed.keys())
    d.update(dict((m, c["Income"]) for m, c in summed.items() if "Income" in c))
    return d

def invert(summed, valid):
    d = {}
    ms = []
    for m, v in summed.items():
        ms.append(m)
        for c, s in v.items():
            if c not in d:
                d[c] = {}
            if m not in d[c]:
                d[c][m] = 0
            d[c][m] += s
    for c in valid:
        if c not in d:
            d[c] = dict((m, 0) for m in ms)
    return d

def category_sum_matrix(summed):
    return [ [ summed[k][v] for v in sorted(summed[k], key=monthsort) ] for k in sorted(summed) ]

def ignore(summed, *args):
    d = copy.deepcopy(summed)
    for k in args:
        for m in d.keys():
            del d[m][k]
    return d

def surplus(expenses, income):
    s = {}
    for m, c in expenses.items():
        s[m] = income[m] + sum(c.values())
    return s

def colours(n):
    return plt.cm.BuPu(np.linspace(0, 1.0, n))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", metavar="FILE", type=argparse.FileType('r'))
    parser.add_argument("--save", type=float, default=0)
    return parser.parse_args()

def bar_label(plot, rects, margins):
    for i, rect in enumerate(rects):
        x = rect.get_x() + rect.get_width()/2.
        y = margins[i] + math.copysign(130, margins[i])
        text = '{}'.format(int(margins[i]))
        plot.text(x, y, text, ha='center', va='bottom')

def money(value):
    return "{:.2f}".format(value)

def q1(boxprop):
    return boxprop.get_data()[1][2]

def q3(boxprop):
    return boxprop.get_data()[1][1]

def mean_error(data, level=0.95):
    n, min_max, mean, var, skew, kurt = stats.describe(data)
    dscale = math.sqrt(var) / math.sqrt(len(data))
    R = stats.norm.interval(level, loc=mean, scale=dscale)
    return R[1] - mean

def main():
    args = parse_args()

    # Core data, used across multiple plots

    # summed: Looks like:
    #
    #  { "04/2013" : { "Cash" : -882.50, ... }, ... }
    summed = dict((m, sum_categories(v))
            for m, v in group_period(csv.reader(args.database)).items())
    blacklist = ("Income", "Internal")
    whitelist = [x for x in categories if x not in blacklist]
    n_categories = len(whitelist)

    # expenses: Looks like summed, but without blacklisted keys
    expenses = ignore(summed, *blacklist)

    # months: A list, containing the sorted set of months from expenses
    months = sorted(expenses, key=monthsort)

    # categorized: Looks like:
    #
    #  { "Cash" : { "04/2013" : -882.50, ... }, ... }
    categorized = invert(expenses, whitelist)

    # monthlies: Looks like:
    #
    # [
    #   [ -882.50, ... ], # Cash expenses per month
    #   [ -832.82, ... ], # Commitment expenses per month
    #   ...
    # ]
    monthlies = category_sum_matrix(categorized)
    n_months = len(monthlies[0])

    # m_income: Looks like summed, but contains only income
    m_income = income(summed)

    # m_margin: Looks like:
    #
    # { "04/2013" : 3905.07, ... }
    m_margin = surplus(expenses, m_income)

    remaining = days_remaining()

    # Plot table/bar-graph of expenses
    y_offset = np.array([0.0] * n_months)
    bar_width = 0.4
    cell_text = []
    palette = colours(n_categories)
    # Add colours for metadata rows total, income and surplus
    plt.figure(1)
    for i, row in enumerate(monthlies):
        plt.bar(np.arange(n_months) + 0.3, row, bar_width, bottom=y_offset, color=palette[i])
        y_offset = y_offset + row
        cell_text.append([money(float(x)) for x in row])
    cell_text.append([money(sum(expenses[m].values())) for m in months])
    cell_text.append([money(m_income[k]) for k in months])
    cell_text.append([money(m_margin[k]) for k in months])
    plt.table(cellText=cell_text,
        rowLabels=whitelist + [ "Expenditure", "Income", "Surplus" ],
        # Add white for metadata
        rowColours=[x for x in itertools.chain(palette, [[1] * 4] * 3)],
        colLabels=months,
        loc="bottom")
    plt.ylabel("Dollars ($), spent < 0, earnt > 0")
    plt.subplots_adjust(left=0.15, bottom=0.3)
    plt.xticks([])
    plt.title("Expenditures by Category per Month\n{} Days Remaining".format(remaining))

    # Plot bar graph of margin
    plt.figure(2)
    sorted_margins = [m_margin[k] for k in months]
    mbar = plt.bar(np.arange(n_months) + 0.3, sorted_margins, 0.4, align="center")
    bar_label(plt, mbar, sorted_margins)
    plt.xticks(np.arange(n_months) + 0.3, months)
    plt.axhline(0, color="black")
    plt.xlabel("Months")
    plt.ylabel("Margin ($)")
    plt.title("Remaining Capital after Expenses\n{} Days Remaining".format(remaining))

    # Plot box-and-whisker plot of categories
    plt.figure(3)
    cs = []
    for c in whitelist:
        # Excludes the in-progress month
        cs.append([categorized[c][m] for m in months[:-1]])
    bpvs = plt.boxplot(cs)
    plt.table(cellText=[
        [money(x.get_data()[1][0]) for x in bpvs["medians"]],
        [money(q1(x)) for x in bpvs["boxes"]],
        [money(q3(x)) for x in bpvs["boxes"]],
        [money(max(c)) for c in cs],
        [money(min(c)) for c in cs]],
            rowLabels=["Median", "First Quartile", "Third Quartile", "Minimum", "Maximum"],
            colLabels=[x[:3] for x in whitelist],
            loc="bottom")
    plt.subplots_adjust(left=0.15, bottom=0.2)
    plt.xticks([])
    plt.ylabel("Dollars ($)")
    plt.title("Box-plot of Expenses per Month\nSamples per category: {}".format(len(months) - 1))

    # XY plot of expenditure per category
    f, plts = plt.subplots(2, int(len(categorized) / 2), sharex=True)
    f.suptitle("XY Plot of Monthly Expenditure per Category\n{} Days Remaining".format(remaining))
    monthr = np.arange(len(months))
    monthns = [ monthname(x) for x in months ]
    for p, d in zip(itertools.chain(*plts), categorized.items()):
        v = [ d[1][k] for k in months ]
        # Values
        p.plot(monthr, v, 'o-')
        # Linear regression
        a, b = polyfit(monthr, v, 1)
        l = polyval([a, b], monthr)
        p.plot(monthr, l, 'r.-')
        p.set_title(d[0])
        p.set_xticklabels(monthns, rotation=33)

    # Weekly XY plot with regression
    args.database.seek(0)
    weekly = group_period(csv.reader(args.database), extract=extract_week)
    w_summed = [(i, sum(float(r[1]) for r in weekly[w] if r[3] in whitelist))
            for i,w in enumerate(sorted(weekly.keys()))]
    w_xys = list(zip(*w_summed))
    plt.figure(5)
    plt.plot(w_xys[0], w_xys[1], "bo-")
    a, b = polyfit(w_xys[0], w_xys[1], 1)
    l = polyval([a, b], w_xys[0])
    plt.plot(w_xys[0], l, "r.-")
    plt.title("XY Plot of Weekly Expenditure")
    plt.xlabel("Record Week (Arbitrary)")
    plt.ylabel("Expenditure ($)")

    # Target bar-graph - Current spending per category against mean
    plt.figure(6)
    # Remove the current month from monthlies
    prev_monthlies = [ e[:-1] for e in monthlies ]
    # mean_prev_monthlies = np.mean(prev_monthlies, keepdims=True)
    mean_prev_monthlies = np.mean(prev_monthlies, axis=1)
    # Calculate the means for each category of each complete month
    error_prev_monthlies = [ mean_error(e) for e in prev_monthlies ]
    curr_expenses = expenses[months[-1]]

    ms = dict(zip(whitelist, mean_prev_monthlies))
    # Calculate mean monthly expenditure
    # s = -1 * np.mean([m_income[m] - m_margin[m] for m in months[:-1]])
    # Calculate mean monthly income
    cash = -1 * np.mean([m_income[m] for m in months[:-1]])
    # Calculate category ratios
    rs = dict((k, v / cash) for k, v in ms.items())
    # Subtract fixed costs
    cash -= sum(v for k, v in ms.items() if k in fixed)
    # Subtract saving
    cash -= -1 * args.save
    # Estimate budget: Multiple remaining by flexible ratios
    fs = copy.deepcopy(ms)
    fs.update(dict((k, rs[k] * cash) for k in flexible))
    budget = [ abs(fs[k]) for k in whitelist ]

    r_whitelist = np.arange(len(whitelist))
    plt.bar(r_whitelist + 0.1,
            budget,
            [ 0.6 ] * len(r_whitelist),
            alpha=0.4)
    plt.bar(r_whitelist + 0.1,
            [ abs(curr_expenses[k]) for k in whitelist ],
            [ 0.6 ] * len(r_whitelist),
            color='r', alpha=0.6)
    plt.bar(r_whitelist + 0.8,
            [ abs(v) for v in mean_prev_monthlies ],
            [ 0.1 ] * len(r_whitelist),
            yerr=error_prev_monthlies, color='k', alpha=0.6)
    plt.axhline(0, color="black")
    plt.xticks([])
    plt.ylabel("Position Against Budget / Mean Expense ($)")
    title = "Position for {} ({} days remaining){}"\
            .format(months[-1], remaining,
                    "" if 0 == args.save else
                        "\nSaving ${}".format(money(args.save)))
    plt.title(title)
    plt.legend(("Mean Expenditure", "Budgeted", "Spent"))
    expense_list = [ curr_expenses[c] for c in whitelist ]
    cell_text = []
    cell_text.append([money(abs(b) - abs(x)) for b, x in zip(budget, expense_list)])
    cell_text.append([money(abs(e)) for e in expense_list])
    cell_text.append([money(abs(b)) for b in budget])
    cell_text.append([money(abs(v)) for v in mean_prev_monthlies])
    cell_text.append([money(abs(v)) for v in error_prev_monthlies])
    plt.table(cellText=cell_text,
            rowLabels=[ "Position", "Spent", "Budget", "Mean", "+/- 95% Confidence" ],
            colLabels=[x[:3] for x in whitelist],
            loc="bottom")
    plt.subplots_adjust(left=0.15, bottom=0.2)
    plt.show()

def days_remaining():
    today = datetime.today()
    n_days = calendar.monthrange(today.year, today.month)[1]
    return (datetime(today.year, today.month, n_days) - today).days + 1


if __name__ == "__main__":
    main()
