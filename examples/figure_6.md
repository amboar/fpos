Current Category Expenditure against Derived Budget
===================================================

![Current Category Expenditure against Derived Budget](figure_6.png)

Figure 6 attempts to derive a budget from your existing spending habits. It's
primary goal is to limit you to spending at most what you earn, but it can also
be tweaked to take into account savings targets.

In order to budget in this way the graph needs an understanding of expected
income: This is (crudely) calculated as the mean of monthly income
transactions. This may not be accurate if your income varies greatly
month-to-month (e.g being paid fortnightly may lead to an extra payment in some
months, being a casual worker with varying hours who is paid fortnightly will
give even greater variance etc.).

Further, this graph splits categories into fixed and flexible sets. These sets
are defined as follows:

* Fixed: Commitment, Education, Health, Home, Shopping, Transport, Utilities
* Flexible: Cash, Dining, Entertainment

That is, the flexible categories are expected to contain 'optional'
transactions - if you were looking to save money, you'd do so by reducing
spending in these categories.

Given that philosophy, the graph develops a budget by using the derived mean
spend in fixed categories as the budget target in that category, and then
redistributes the remaining projected earnings (i.e. project income minus the
sum of means of fixed categories) over the flexible categories by their
relative scale. If a savings target is configured, the target saving amount is
deducted from the remaining projected earnings prior to distributing it across
the flexible categories.

As to the graph itself, each category is dislayed with three bars:

1. A wide, blue bar representing the category's budgeted amount
2. A wide, red bar overlapping the blue, representing the amount currently
   spent in the category for the month
3. An adjacent thin, grey bar representing the mean spend in the category

The red bar overlaps the blue to provide a visual queue around 'filling up' in
a given category. If the red bar exceeds the heigh of the blue then spending
has exceeded the budget in the category for the month (in the example graph,
overspending has occurred in the Education, Home and Health categories).

The values used to derive the bars are displayed in a table below the graph,
with relevant values aligned to their category columns. The 95% confidence
interval row is displayed as whiskers on the mean bar to provide insight on the
mean variability (take with a grain of salt).

NOTE: This graph breaks with fpos custom and represents expenses as positive
values.

[back to README](../README.md)
