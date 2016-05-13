#!/usr/bin/python3
#
#    Saving for periodic expenses
#    Copyright (C) 2016  Andrew Jeffery <andrew@aj.id.au>
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

import csv
import sys

from .core import date_fmt, month_fmt, money

from collections import namedtuple
import datetime
import monthdelta

from .visualise import PeriodGroup, extract_month, visualise
from .cdesc import cdesc
from .predict import group_deltas, group_delta_bins, icmf
from .combine import combine

import numpy as np

from random import random

# date is a datetime
Transaction = namedtuple("Transaction", "date value description category")

Balance = namedtuple("Balance", "month income expenses")

# balances is a dict, months as keys, Balances as values
History = namedtuple("History", "now balances")

Group = namedtuple("Group", "name transactions")

# last is a datetime, period is a timedelta
Commitment = namedtuple("Commitment", "group value last period")

# next is a datetime (= commitment.last + commitment.period)
Target = namedtuple("Target", "commitment next")

Position = namedtuple("Position", "target saved")

def amortise_target(target):
    mod = monthdelta.monthmod(target.commitment.last, target.next)
    delta_m = mod[0].months
    return -target.commitment.value / delta_m

def save_from_month(history, state, month, value):
    balance = history.balances[month]
    profit = balance.income + balance.expenses

    held = -state[month].expenses if month in state else 0

    if held > profit:
        return 0

    hold = profit - held
    if held <= (held + value) <= profit:
        hold = value


    state[month] = Balance(month, 0, -(held + hold))

    return hold

def to_month(date):
    return date.replace(day=1)

def balance_history(history, longest):
    state = {}

    if not history or len(history.balances) == 0:
        return state

    first = to_month(next(iter(sorted(history.balances.keys()))))
    current_month = to_month(history.now)
    mod = monthdelta.monthmod(first, current_month - longest)
    delta_m = mod[0].months
    nmonths = monthdelta.monthmod(first, current_month)[0].months + 1

    for i in range(delta_m, (nmonths - 1)):
        month = first + monthdelta.monthdelta(i)
        balance = history.balances[month]
        profit = balance.income + balance.expenses

        if profit < 0:
            saved = 0

            for j in range(i, -1, -1):
                old_month = first + monthdelta.monthdelta(j)
                want = -(profit + saved)
                saved += save_from_month(history, state, old_month,
                        want)

                if (saved + profit) == 0:
                    break

            if (saved + profit) < 0:
                raise ValueError("Spending more than you earn :(")

            state[month] = Balance(month, saved, 0)

    return state

def calculate_position(history, target, state):
    mod = monthdelta.monthmod(to_month(target.commitment.last), to_month(history.now))
    delta_m = mod[0].months
    if delta_m == 0:
        return Position(target, 0)

    value = amortise_target(target)
    saved = 0
    current_month = to_month(history.now)
    for i in range(1, delta_m):
        month = current_month - monthdelta.monthdelta(i)
        saved += save_from_month(history, state, month, value)

    return Position(target, saved)

def filter_targets(history, targets):
    return [ t for t in targets if
            t.next >= history.now and
            t.commitment.period > datetime.timedelta(31, 0, 0) and
            t.commitment.value < 0 ]

def sort_targets(targets):
    return sorted(targets, key=lambda x: x.next)

def calculate_positions(history, targets, state=None):
    longest = max(t.commitment.period for t in targets)
    if not state:
        state = balance_history(history, longest)
    return [ calculate_position(history, t, state) for t in targets ], state

# glue function
def generate_history(transactions):
    period_grouper = PeriodGroup(extract_month)
    for row in transactions:
        period_grouper.add(row)
    last = datetime.datetime.strptime(transactions[-1][0], date_fmt)
    groups, = period_grouper.groups()
    balances = {}
    for s_month in groups.keys():
        d_month = datetime.datetime.strptime(s_month, month_fmt)
        income = 0
        expenses = 0
        for t in groups[s_month]:
            value = float(t[1])
            if value >= 0:
                income += value
            else:
                expenses += value
            balances[d_month] = Balance(d_month, income, expenses)
    return History(last, balances)

# glue function
def generate_groups(transactions):
    legacy = cdesc(t for t in transactions
            if len(t) >= 4 and not t[3] == "Internal")
    groups = []
    for g in legacy:
        if len(g) == 0:
            continue
        name = g[0][2]
        transactions = []
        for t in g:
            date = datetime.datetime.strptime(t[0], date_fmt)
            amount = float(t[1])
            description = t[2]
            category = t[3]
            nt = Transaction(date, amount, description, category)
            transactions.append(nt)
        groups.append(Group(name, transactions))
    return groups

def count_quantized_transactions(group):
    return len(set(t.date for t in group.transactions))

def filter_groups(groups):
    return [ g for g in groups if count_quantized_transactions(g) > 2 ]

def calculate_value(group):
    return np.mean([t.value for t in group.transactions])

def calculate_period(group):
    return datetime.timedelta(icmf(group_delta_bins(group_deltas(group.transactions))), 0, 0)

def calculate_last(group):
    return group.transactions[-1].date

def generate_commitment(group):
    return Commitment(group, calculate_value(group),
            calculate_last(group), calculate_period(group))

def generate_target(commitment):
    return Target(commitment, commitment.last + commitment.period)

def calculate_targets(groups):
    targets = []
    for g in groups:
        try:
            c = generate_commitment(g)
        except ValueError:
            pass
        else:
            targets.append(generate_target(c))
    return targets

def print_positions(positions):
    print("Name | Last | Due | Amount | Saved | Net")
    for p in positions:
        print("{} | {} | {} | {} | {} | {}".format(
            p.target.commitment.group.name,
            datetime.datetime.strftime(p.target.commitment.last, date_fmt),
            datetime.datetime.strftime(p.target.next, date_fmt),
            money(p.target.commitment.value),
            money(p.saved),
            money(p.saved + p.target.commitment.value)))

def calculate_reserved_last(group):
    return group.transactions[-2].date

def calculate_reserved_value(group):
    return group.transactions[-1].value

def calculate_reserved_period(group):
    return group.transactions[-1].date - group.transactions[-2].date

def generate_reserved_commitment(group):
    return Commitment(group, calculate_reserved_value(group),
            calculate_reserved_last(group), calculate_reserved_period(group))

def generate_reserved_target(now, commitment):
    return Target(commitment, now)

def calculate_reserved_targets(now, groups):
    current_month = to_month(now)
    reserved_targets = []
    for g in groups:
        try:
            c = generate_commitment(g)
        except ValueError:
            pass
        else:
            if current_month <= c.last <= now:
                rc = generate_reserved_commitment(g)
                rt = generate_reserved_target(now, rc)
                reserved_targets.append(rt)
    return reserved_targets

def get_reserved_target_paid(target):
    return target.commitment.group.transactions[-1].date

def sort_reserved_targets(targets):
    return sorted(targets, key=lambda x: get_reserved_target_paid(x))

def print_reserved(positions):
    columns = [ "Name", "Last", "Paid", "Amount", "Saved", "Net" ]
    print(" | ".join(columns))
    for p in positions:
        print("{} | {} | {} | {} | {} | {}".format(
            p.target.commitment.group.name,
            datetime.datetime.strftime(p.target.commitment.last, date_fmt),
            datetime.datetime.strftime(get_reserved_target_paid(p.target), date_fmt),
            money(p.target.commitment.value),
            money(p.saved),
            money(p.saved + p.target.commitment.value)))
    print("".join([ "|" ] * (len(columns) - 1)))

def filter_transactions(transactions):
    return [ t for t in transactions if t[3] != "Internal" ]

def synthesise_transactions(transactions, state, positions):
    st = transactions[:]
    for k, v in state.items():
        st.append(Transaction(k.strftime(date_fmt), v.expenses, "Saving-{}".format(random() * 20), "Commitment"))
        st.append(Transaction(k.strftime(date_fmt), v.income, "Balancing-{}".format(random() * 20), "Commitment"))
    for p in positions:
        t = Transaction(
                p.target.next.strftime(date_fmt),
                p.saved,
                p.target.commitment.group.name,
                p.target.commitment.group.transactions[0].category)
        st.append(t)
    return list(combine([st, ]))


def psave(transactions):
    transactions = filter_transactions(transactions)
    history = generate_history(transactions)
    groups = filter_groups(generate_groups(transactions))
    reserved_positions, state = calculate_positions(history,
        sort_reserved_targets(filter_targets(history, calculate_reserved_targets(history.now, groups))))
    print_reserved(reserved_positions)
    current_positions, state = calculate_positions(history,
        sort_targets(filter_targets(history, calculate_targets(groups))), state)
    print_positions(current_positions)
    synthesised = synthesise_transactions(transactions, state, reserved_positions)
    # for t in synthesised:
        # print(",".join(str(f) for f in t))
    visualise(synthesised)


if __name__ == "__main__":
    psave(list(csv.reader(sys.stdin)))
