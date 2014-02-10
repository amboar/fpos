#!/usr/bin/python3

import csv
import sys
import matplotlib.pyplot as plt
from datetime import datetime as dt
import core

def main():
    blacklist = ("Income", "Internal")
    whitelist = [x for x in core.categories if x not in blacklist]
    r = csv.reader(sys.stdin)
    previous = {}
    deltas = {}
    for row in r:
        date = dt.strptime(row[0], core.date_fmt)
        category = row[3]
        if category in previous:
            if category not in deltas:
                deltas[category] = []
            delta = (date - previous[category]).days
            if 0 < delta:
                deltas[category].append(delta)
        previous[category] = date
    for i, cat in enumerate(x for x in whitelist if x in deltas):
        plt.figure(i)
        plt.title(cat)
        plt.hist(deltas[cat], bins=max(deltas[cat]), align="left")
    plt.show()
    r.close()

if __name__ == "__main__":
    main()
