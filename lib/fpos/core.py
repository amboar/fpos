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
import importlib

categories = [ "Cash", "Commitment", "Dining", "Education", "Entertainment",
"Health", "Home", "Income", "Internal", "Shopping", "Transport", "Utilities" ]

flexible = [ "Cash", "Dining", "Entertainment" ]
fixed = [ x for x in categories if x not in flexible ]

date_fmt = "%d/%m/%Y"
month_fmt = "%m/%Y"

def money(value):
    return "{:.2f}".format(value)

def global_module(env, module, package=None, name=None):
    env[module if name is None else name] = importlib.import_module(module, package)

def global_symbol(env, module, symbol, package=None, name=None):
    p = importlib.import_module(module, package)
    env[symbol if name is None else name] = getattr(p, symbol)

def lcs(a, b):
    assert isinstance(a, str)
    assert isinstance(b, str)
    la = len(a)
    lb = len(b)
    lookup = [ [ 0 ] * (lb + 1) ] * (la + 1)
    for ia in range(la - 1, -1, -1):
        for ib in range(lb - 1, -1, -1):
            if a[ia] == b[ib]:
                lookup[ia][ib] = 1 + lookup[ia + 1][ib + 1]
            else:
                lookup[ia][ib] = max(lookup[ia + 1][ib], lookup[ia][ib + 1])
    return lookup[0][0]
