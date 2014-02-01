#    Common variables, functions and classes
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

categories = [ "Cash", "Commitment", "Dining", "Education", "Entertainment",
"Health", "Home", "Income", "Internal", "Shopping", "Transport", "Utilities" ]

flexible = [ "Cash", "Dining", "Entertainment" ]
fixed = [ x for x in categories if x not in flexible ]

date_fmt = "%d/%m/%Y"
month_fmt = "%m/%Y"

def money(value):
    return "{:.2f}".format(value)
