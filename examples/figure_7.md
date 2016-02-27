Monthly Progressive Mean Daily Spend
====================================

![Monthly Progressive Mean Daily Spend](figure_7.png)

Plots the day of the month against the sum of daily expenses divided by the day
of the month (this type of graph is frequently used in cricket broadcasts). In
a perfect (boring?) world where you spent the same predictable amount every day
this would give a constant line across the graph. Hopefully life isn't boring
(perfect? what kind of hope is that?!), and you get a more interesting graph.

The current month's data-points are highlighted in red, with adjacent days
linked with a red line for traceability through the data set.

Then there's the data-points highlighted in yellow. These represent the
predicted progressive daily mean expense values. The graph exploits periodicity
estimation in transaction description clusters to predict when you'll next
spend money at a given merchant. Summing over the clusters for a given day
gives the estimated expenses for the day, which is then progressively
integrated into the graph.

In addition to daily data-points, two lines are provided which show your
typical and maximum daily spend (hopefully it's the case that the typical daily
spend doesn't exceed the maximum). Ultimately at the end of the month your
progressive daily mean data point should lie around the typical value, and
hopefully below the maximum. The predictive yellow data points give an
indicator of where you're expected to land, and so you can decide early how you
need to manage your spending habits.

[back to README](../README.md)
