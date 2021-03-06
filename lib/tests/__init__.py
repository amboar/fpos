#!/usr/bin/python3
#
#    Tests functionality in user scripts
#    Copyright (C) 2014,2015  Andrew Jeffery <andrew@aj.id.au>
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

import matplotlib
matplotlib.use('Agg')
from datetime import datetime as dt
from datetime import timedelta as td
from itertools import islice, cycle
import unittest
from fpos import annotate, combine, core, transform, visualise, window, predict, db, psave, groups, generate
import types

money = visualise.money

class TagInjector(object):
    def __init__(self, responses, confirms=None):
        self.responses = iter(list(responses))
        self.confirms = iter(list(confirms)) if confirms is not None else None

    def banner(self, entry):
        pass

    def resolve(self, guess):
        return next(self.responses)

    def confirm(self, category):
        return next(self.confirms) if self.confirms else "y"

    def help(self):
        pass

    def warn(self, message):
        pass

class AnnotateTest(unittest.TestCase):
    def test_find_category_no_match(self):
        invalid = "foo"
        self.assertTrue(invalid not in annotate.categories)
        with self.assertRaises(ValueError):
            annotate._Tagger.find_category(invalid, annotate.categories)

    def test_find_category_multiple_matches(self):
        self.assertTrue(set(["Income", "Internal"]).issubset(annotate.categories))
        prefix = "In"
        with self.assertRaises(ValueError):
            annotate._Tagger.find_category(prefix, annotate.categories)

    def test_find_category_single_match(self):
        test = "Income"
        self.assertTrue(test in annotate.categories)
        needle = "inc"
        self.assertEqual(test, annotate._Tagger.find_category(needle, annotate.categories))

    def test_category_list(self):
        expected = set([ "Cash", "Commitment", "Dining", "Education", "Entertainment",
            "Health", "Home", "Income", "Internal", "Shopping", "Transport", "Utilities" ])
        self.assertEqual(expected, set(annotate.categories))

    def test_resolve_category_index(self):
        self.assertEqual(annotate.categories[0], annotate._Tagger.resolve_category(0))

    def test_resolve_category_needle(self):
        self.assertEqual(annotate.categories[0], annotate._Tagger.resolve_category(annotate.categories[0]))

    def test_categorize_no_group(self):
        cc = annotate.categories[0]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            with annotate._Tagger(grouper=dg, io=TagInjector([ cc ])) as t:
                e = annotate.Entry("01/01/2019", "-12.34", "Test description")
                c = t.categorize(e, None)
                self.assertEqual(cc, c)

    def test_categorize_group_single_entry(self):
        cc = annotate.categories[0]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc, size=0)
            with annotate._Tagger(grouper=dg, io=TagInjector([ cc ])) as t:
                e1 = annotate.Entry("01/01/2019", "-12.34", "Test description 0")
                t.insert(e1, cc)
                e2 = annotate.Entry("02/01/2019", "-56.78", "Test description 1")
                g = t.find_group(e2.description)
                c = t.categorize(e2, g)
                self.assertEqual(cc, c)

    def test_categorize_empty_response(self):
        cc = annotate.categories[0]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            with annotate._Tagger(grouper=dg, io=TagInjector([ "", cc ])) as t:
                e = annotate.Entry("02/01/2019", "-56.78", "Test description 1")
                c = t.categorize(e, None)
                self.assertEqual(cc, c)

    def test_categorize_help_response(self):
        cc = annotate.categories[0]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            with annotate._Tagger(grouper=dg, io=TagInjector([ "?", cc ])) as t:
                e = annotate.Entry("02/01/2019", "-56.78", "Test description 1")
                c = t.categorize(e, None)
                self.assertEqual(cc, c)

    def test_categorize_garbled_response(self):
        cc = annotate.categories[0]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            garbled = "".join(annotate.categories)
            with annotate._Tagger(grouper=dg, io=TagInjector([ garbled, cc ])) as t:
                e = annotate.Entry("02/01/2019", "-56.78", "Test description 1")
                c = t.categorize(e, None)
                self.assertEqual(cc, c)

    def test_categorize_with_positive_confirm(self):
        cc = annotate.categories[0]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            with annotate._Tagger(grouper=dg, io=TagInjector([ cc ])) as t:
                e = annotate.Entry("02/01/2019", "-56.78", "Test description 1")
                c = t.categorize(e, None, True)
                self.assertEqual(cc, c)

    def test_categorize_with_negative_confirm(self):
        bc = annotate.categories[1]
        cc = annotate.categories[0]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            with annotate._Tagger(grouper=dg, io=TagInjector([ bc, cc ], [ "n", "y" ])) as t:
                e = annotate.Entry("02/01/2019", "-56.78", "Test description 1")
                c = t.categorize(e, None, True)
                self.assertEqual(cc, c)

    def test_annotate_empty_source(self):
        src = []
        res = []
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            t = annotate._Tagger(grouper=dg, io=TagInjector([]))
            self.assertEqual(res, annotate.annotate(src, False, t))

    def test_annotate_empty_line(self):
        src = [ [] ]
        res = []
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            t = annotate._Tagger(grouper=dg, io=TagInjector([]))
            self.assertEqual(res, annotate.annotate(src, False, t))

    def test_annotate_one_no_category(self):
        cc = annotate.categories[0]
        row = [ "02/01/2019", "-56.78", "Test description 1" ]
        src = [ row ]
        res = [ [ row[0], row[1], row[2], cc ] ]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            t = annotate._Tagger(grouper=dg, io=TagInjector([ cc ]))
            self.assertEqual(res, annotate.annotate(src, False, t))

    def test_annotate_one_with_valid_category(self):
        cc = annotate.categories[0]
        row = [ "02/01/2019", "-56.78", "Test description 1", cc ]
        src = [ row ]
        res = [ row ]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            t = annotate._Tagger(grouper=dg, io=TagInjector([]))
            self.assertEqual(res, annotate.annotate(src, False, t))

    def test_annotate_one_with_invalid_category(self):
        cc = annotate.categories[0]
        garbled = "".join(annotate.categories)
        row = [ "02/01/2019", "-56.78", "Test description 1", garbled ]
        src = [ row ]
        res = [ [ row[0], row[1], row[2], cc ] ]
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            dg = groups.DynamicGroups(backend=gc)
            t = annotate._Tagger(grouper=dg, io=TagInjector([ cc ]))
            self.assertEqual(res, annotate.annotate(src, False, t))

class TransformTest(unittest.TestCase):
    expected = [ [ "01/01/2014", "1.00", "Positive" ],
            [ "01/01/2014", "-1.00", "Negative" ] ]

    def test_transform_commbank(self):
        commbank = [ [ "01/01/2014", "1.0", "Positive", "1.0" ],
                [ "01/01/2014", "-1.0", "Negative", "0.0" ] ]
        self.assertEqual(self.expected, list(transform.transform("commbank", commbank)))

    def test_transform_anz(self):
        anz = self.expected
        self.assertEqual(self.expected, list(transform.transform("anz", anz)))

    def test_transform_stgeorge(self):
        stgeorge = iter([ [ "#Date", "Description", "Debit", "Credit", "Balance" ],
                [ "01/01/2014", "Positive", None, "1.0", "1.0" ],
                [ "01/01/2014", "Negative", "1.0", None, "0.0" ] ])
        self.assertEqual(self.expected, list(transform.transform("stgeorge", stgeorge)))

    def test_transform_nab(self):
        nab = iter([ [ "01-Jan-14", "1.00", "1", None, None, "Positive", "1.00", None ],
            [ "01-Jan-14", "-1.00", "2", None, None, "Negative", "0.00", None ] ])
        self.assertEqual(self.expected, list(transform.transform("nab", nab)))

    def test_transform_woolworths(self):
        woolies = iter([
            ["01 Jan 2014", "Positive", "", "1.00", "NaN", "String", "String", None],
            ["01 Jan 2014", "Negative", "1.00", "", "NaN", "String", "String", None],
            ])
        self.assertEqual(self.expected, list(transform.transform("woolworths", woolies)))


    def test__is_empty_None(self):
        self.assertTrue(transform._is_empty(None))

    def test__is_empty_empty(self):
        self.assertTrue(transform._is_empty(None))

    def test__is_date_mdY(self):
        self.assertTrue(transform._is_date("01/01/2014"))

    def test__is_date_dby(self):
        self.assertTrue(transform._is_date("28-Apr-14"))

    def test__is_date_fail(self):
        self.assertFalse(transform._is_date("not a date"))

    def test__is_number_int(self):
        self.assertTrue(transform._is_number(1))

    def test__is_number_float(self):
        self.assertTrue(transform._is_number(1.0))

    def test__is_number_neg_float(self):
        self.assertTrue(transform._is_number(-1.0))

    def test__is_number_fail(self):
        self.assertFalse(transform._is_number("not a number"))

    def test__compute_cell_type__EMPTY(self):
        self.assertEqual(transform._EMPTY, transform._compute_cell_type(None))

    def test__compute_cell_type__DATE(self):
        self.assertEqual(transform._DATE, transform._compute_cell_type("01/01/2014"))

    def test__compute_cell_type__NUMBER(self):
        self.assertEqual(transform._NUMBER, transform._compute_cell_type("-12.34"))

    def test__compute_cell_type__STRING(self):
        self.assertEqual(transform._STRING, transform._compute_cell_type("neither"))

    def test__sense_form_commbank(self):
        self.assertEqual("commbank", transform._sense_form(["01/01/2014", "-1.0", "description", "-1.0"]))

    def test__sense_form_anz(self):
        self.assertEqual("anz", transform._sense_form(["01/01/2014", "-1.0", "description"]))

    def test__sense_form_stgeorge_debit(self):
        self.assertEqual("stgeorge", transform._sense_form(["01/01/2014",  "description", "1.0", "", "-1.0"]))

    def test__sense_form_stgeorge_credit(self):
        self.assertEqual("stgeorge", transform._sense_form(["01/01/2014",  "description", "", "1.0", "1.0"]))

    def test__sense_form_nab(self):
        self.assertEqual("nab", transform._sense_form(["01/01/2014", "-1.0", "12345", "", "description", "my merchant", "1.0"]))

    def test__sense_form_nab_gh_issue23_0(self):
        self.assertEqual("nab", transform._sense_form("01-May-16,-70.33,071555684686,,CREDIT CARD PURCHASE,FREWVILLE FOODLAND       FREWVILLE,-131.26,".split(',')))

    def test__sense_form_nab_gh_issue23_1(self):
        self.assertEqual("nab", transform._sense_form("29-Mar-16,5.30,000125555398,,MISCELLANEOUS CREDIT,CASHBACK,-60.93,".split(',')))

    def test__sense_form_nab_gh_issue23_2(self):
        self.assertEqual("nab", transform._sense_form("20-Mar-16,-66.23,,,CREDIT CARD PURCHASE,PASADENA FOODLAND,-66.23,".split(',')))

    def test__sense_form_bankwest_cheque(self):
        self.assertEqual("bankwest", transform._sense_form(["", 12345, "01/01/2014", "description", "-1.0", "", "", "-1.0", "cheque"]))

    def test__sense_form_bankwest_debit(self):
        self.assertEqual("bankwest", transform._sense_form(["", 12345, "01/01/2014", "description", "", "1.0", "", "1.0", "debit"]))

    def test__sense_form_bankwest_credit(self):
        self.assertEqual("bankwest", transform._sense_form(["", 12345, "01/01/2014", "description", "", "", "-1.0", "-1.0", "credit"]))

    def test__sense_form_woolworths_debit(self):
        self.assertEqual("woolworths", transform._sense_form("20 Mar 2016,Pie,3.14,,,Food & Drink,Groceries,".split(',')))

    def test__sense_form_woolworths_debit_nan(self):
        self.assertEqual("woolworths", transform._sense_form("19 Mar 2016,Natural log,2.71,,NaN,Food & Drink,Groceries,".split(',')))

    def test__sense_form_woolworths_credit(self):
        self.assertEqual("woolworths", transform._sense_form("01 Mar 2016,Avogadros number - space -,,60221409,NaN,Financial,BPAY Payments,".split(',')))

    def test_transform_auto_empty(self):
        self.assertEqual([], transform.transform_auto(iter([]), False))

class WindowTest(unittest.TestCase):
    def test_gen_span_oracle_date_in_default(self):
        d = dt.strptime("01/01/2014", window.date_fmt)
        self.assertTrue(window.gen_span_oracle(None, None)(d))

    def test_gen_span_oracle_date_in_start(self):
        d = dt.strptime("02/01/2014", window.date_fmt)
        self.assertTrue(window.gen_span_oracle("01/2014", None)(d))

    def test_gen_span_oracle_date_in_end(self):
        d = dt.strptime("31/01/2014", window.date_fmt)
        self.assertTrue(window.gen_span_oracle(None, "02/2014")(d))

    def test_gen_span_oracle_date_on_end(self):
        d = dt.strptime("01/02/2014", window.date_fmt)
        self.assertFalse(window.gen_span_oracle(None, "02/2014")(d))

    def test_gen_span_oracle_date_on_start(self):
        d = dt.strptime("01/01/2014", window.date_fmt)
        self.assertFalse(window.gen_span_oracle("02/2014", None)(d))

    def test_unbounded_start_unbounded_end(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        self.assertEqual(ir, list(window.window(ir, None, None)))

    def test_bounded_start_unbounded_end(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[1] ]
        self.assertEqual(expected, list(window.window(ir, "02/2014", None)))

    def test_unbounded_start_bounded_end(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[0] ]
        self.assertEqual(expected, list(window.window(ir, None, "02/2014")))

    def test_bounded_start_bounded_end(self):
        ir =  [ [ "31/12/2013", "-1.00", "Description" ],
                [ "31/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[1] ]
        self.assertEqual(expected, list(window.window(ir, "01/2014", "02/2014")))

    def test_span_1(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[1] ]
        self.assertEqual(expected, list(window.window(ir, relspan=1)))

    def test_span_2(self):
        ir =  [ [ "31/12/2013", "-1.00", "Description" ],
                [ "31/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = ir[1:]
        self.assertEqual(expected, list(window.window(ir, relspan=2)))

class VisualiseTest(unittest.TestCase):
    def test_group_period_empty(self):
        pg = visualise.PeriodGroup()
        self.assertEqual([], pg.groups())

    def test_group_period_extract_month(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "09/01/2014", "-2.00", "Bar" ]
        months = [ first, second ]
        expected = { "01/2014" : months }
        pg = visualise.PeriodGroup(visualise.extract_month)
        pg.add_all(months)
        result = pg.groups()
        self.assertEqual(1, len(result))
        self.assertEqual(expected, result[0])

    def test_group_period_extract_week(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "09/01/2014", "-2.00", "Bar" ]
        weeks = [ first, second ]
        expected = { "2014:00" : [ first ], "2014:01" : [ second ] }
        pg = visualise.PeriodGroup(visualise.extract_week)
        pg.add_all(weeks)
        result = pg.groups()
        self.assertEqual(1, len(result))
        self.assertEqual(expected, result[0])

    def test_group_period_extract_both(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "02/01/2014", "-2.00", "Foo" ]
        transactions = [ first, second ]
        expected = [ { "01/2014" : [ first, second ] }, { "2014:00" : [ first, second ] } ]
        pg = visualise.PeriodGroup(visualise.extract_month, visualise.extract_week)
        pg.add_all(transactions)
        result = pg.groups()
        self.assertEqual(2, len(result))
        self.assertEqual(expected, result)

    def test_sum_categories_single_spend_multiple_categories(self):
        spent = -1.00
        sspent = money(spent)
        data = []
        for entry in visualise.whitelist:
            data.append([ "01/01/2014", sspent, entry, entry ])
        sc = visualise.sum_categories(data)
        for entry in visualise.whitelist:
            self.assertEqual(sc[entry], spent)

    def test_sum_categories_multiple_spend_single_category(self):
        cat = visualise.whitelist[0]
        spent = -1.00
        data = [ [ "01/01/2014", money(spent), "Foo", cat ] ] * 2
        self.assertEqual(len(data) * spent, visualise.sum_categories(data)[cat])

    def test_income_only_two_months(self):
        month = [ "01/2014", "02/2014" ]
        amount = 1.00
        data = { month[0] : { "Income" : amount },
                 month[1] : { "Income" : amount } }
        expected = { month[0] : amount, month[1] : amount }
        self.assertEqual(expected, visualise.income(data))

    def test_income_mix(self):
        month = "01/2014"
        amount = 1.00
        data = { month : { visualise.whitelist[0] : "0.00", "Income" : amount } }
        expected = { month : amount }
        self.assertEqual(expected, visualise.income(data))

    def test_invert_multiple_categories(self):
        month = "01/2014"
        amount = -1.00
        data = { month : {} }
        expected = { }
        for entry in visualise.whitelist:
            data[month][entry] = amount
            if entry not in expected:
                expected[entry] = {}
            expected[entry][month] = amount
        self.assertEqual(expected, visualise.invert(data, visualise.whitelist))

    def test_invert_single_category(self):
        """Ensures unlisted categories are initialised to zero"""
        month = "01/2014"
        amount = -1.00
        single = "Cash"
        data = { month : { single : amount } }
        expected = dict((entry, { month : 0 }) for entry in visualise.whitelist)
        expected[single][month] = amount;
        self.assertEqual(expected, visualise.invert(data, visualise.whitelist))


    def test_category_sum_matrix(self):
        month = [ "01/2014", "02/2014" ]
        amount = -1.00
        summed = { month[0] : { visualise.whitelist[0] : amount },
                   month[1] : { visualise.whitelist[0] : amount } }
        inverted = visualise.invert(summed, visualise.whitelist)
        expected = [ [ amount, amount ] ]
        expected.extend([ [ 0 ] * 2 ] * (len(visualise.whitelist) - 1))
        self.assertEqual(expected, visualise.category_sum_matrix(inverted))

    def test_ignore_one(self):
        month = "01/2014"
        amount = -1.00
        single = "Cash"
        data = { month : { single : amount } }
        expected = { month : {} }
        self.assertEqual(expected, visualise.ignore(data, single))

    def test_ignore_several(self):
        month = "01/2014"
        amount = -1.00
        ignore = [ "Cash", "Dining" ]
        data = { month : dict((i, amount) for i in ignore) }
        expected = { month : {} }
        self.assertEqual(expected, visualise.ignore(data, *ignore))

    def test_surplus(self):
        month = "01/2014"
        amount = -1.00
        expenses = { month : { "Cash" : amount } }
        income = { month : amount * amount }
        self.assertEqual(0.0, visualise.surplus(expenses, income)[month])

    def test_money_zero(self):
        self.assertEqual("0.00", visualise.money(0.0))

    def test_money_one(self):
        self.assertEqual("1.00", visualise.money(1.0))

    def test_money_neg_one(self):
        self.assertEqual("-1.00", visualise.money(-1.0))

    def test_money_one_and_a_bit(self):
        self.assertEqual("-1.00", visualise.money(-1.001))

class CombineTest(unittest.TestCase):
    def test_combine_one_empty(self):
        self.assertEqual([], list(combine.combine([ [] ])))

    def test_combine_invalid_ir(self):
        # Missing the (required) description
        sources = [ [ [ "01/01/2014", -1.00 ] ] ]
        self.assertEqual([], list(combine.combine(sources)))

    def test_combine_3tuple(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ] ] ]
        expected = sources[0]
        self.assertEqual(expected, list(combine.combine(sources)))

    def test_combine_4tuple(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description", "Cash" ] ] ]
        expected = sources[0]
        self.assertEqual(expected, list(combine.combine(sources)))

    def test_combine_two_first_empty(self):
        sources = [ [],
                    [ [ "01/01/2014", -1.00, "Description" ] ] ]
        expected = sources[1]
        self.assertEqual(expected, list(combine.combine(sources)))

    def test_combine_two_distinct(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ] ],
                    [ [ "02/01/2014", -1.00, "Description" ] ] ]
        expected = [ sources[0][0], sources[1][0] ]
        self.assertEqual(expected, list(combine.combine(sources)))

    def test_combine_two_equal(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ] ],
                    [ [ "01/01/2014", -1.00, "Description" ] ] ]
        expected = sources[0]
        self.assertEqual(expected, list(combine.combine(sources)))

    def test_combine_two_superset(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ],
                      [ "02/01/2014", -1.00, "Description" ] ],
                    [ [ "02/01/2014", -1.00, "Description" ] ] ]
        expected = [ sources[0][0], sources[1][0] ]
        self.assertEqual(expected, list(combine.combine(sources)))

    def test_combine_prefer_last(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ],
                      [ "02/01/2014", -1.00, "Description" ] ],
                    [ [ "02/01/2014", -1.00, "Description", "Cash" ] ] ]
        expected = [ sources[0][0], sources[1][0] ]
        self.assertEqual(expected, list(combine.combine(sources)))

class CoreTest(unittest.TestCase):
    def test_lcs_empty(self):
        self.assertEqual(0, core.lcs("", ""))

    def test_lcs_a_empty(self):
        self.assertEqual(0, core.lcs("", "a"))

    def test_lcs_b_empty(self):
        self.assertEqual(0, core.lcs("a", ""))

    def test_lcs_equal_single(self):
        self.assertEqual(1, core.lcs("a", "a"))

    def test_lcs_different_single(self):
        self.assertEqual(0, core.lcs("a", "b"))

    def test_lcs_equal_double(self):
        self.assertEqual(2, core.lcs("ab", "ab"))

    def test_lcs_different_double(self):
        self.assertEqual(1, core.lcs("ab", "ba"))

    def test_lcs_different_lengths_a_short(self):
        self.assertEqual(1, core.lcs("abc", "dcba"))

    def test_lcs_different_lengths_b_short(self):
        self.assertEqual(1, core.lcs("dcba", "abc"))

    def test_lcs_similar(self):
        self.assertEqual(1, core.lcs("abbb", "aaaa"))

class PredictTest(unittest.TestCase):
    def test_group_deltas_empty(self):
        data = []
        expected = []
        self.assertSequenceEqual(expected, predict.group_deltas(data))

    def test_group_deltas_one(self):
        data = [["01/01/2015"]]
        expected = []
        self.assertSequenceEqual(expected, predict.group_deltas(data))

    def test_group_deltas_two(self):
        data = [["01/01/2015"], ["02/01/2015"]]
        expected = [1]
        self.assertSequenceEqual(expected, predict.group_deltas(data))

    def test_group_deltas_three(self):
        data = [["01/01/2015"], ["02/01/2015"], ["04/01/2015"]]
        expected = [1, 2]
        self.assertSequenceEqual(expected, predict.group_deltas(data))

    def test_group_delta_bins_one(self):
        data = [1]
        expected = [1]
        self.assertSequenceEqual(expected, predict.group_delta_bins(data))

    def test_group_delta_bins_two(self):
        data = [1, 2]
        expected = [1, 1]
        self.assertSequenceEqual(expected, list(predict.group_delta_bins(data)))

    def test_period_empty(self):
        self.assertRaises(ValueError, predict.period, [])

    def test_period_single(self):
        self.assertEqual(1, predict.period([1]))

    def test_period_spurious(self):
        self.assertEqual(1, predict.period([1, 0]))

    def test_period_multiple(self):
        self.assertEqual(2, predict.period([1, 1]))

    def test_pmf_empty(self):
        self.assertSequenceEqual([], predict.pmf([]))

    def test_pmf_one_bin(self):
        self.assertSequenceEqual([1], predict.pmf([1]))

    def test_pmf_two_bins_balanced(self):
        self.assertSequenceEqual([0.5, 0.5], predict.pmf([1, 1]))

    def test_pmf_two_bins_unbalanced(self):
        self.assertSequenceEqual([0.25, 0.75], predict.pmf([1, 3]))

    def test_pmf_two_bins_first_zero(self):
        self.assertSequenceEqual([0.0, 1.0], predict.pmf([0, 1]))

    def test_pmf_two_bins_second_zero(self):
        self.assertSequenceEqual([1.0, 0.0], predict.pmf([1, 0]))

    def test_probable_spend_emtpy(self):
        self.assertSequenceEqual([], predict.probable_spend([], 0.0))

    def test_probable_spend_one(self):
        self.assertSequenceEqual([2], predict.probable_spend([1], 2.0))

    def test_probable_spend_two_balanced(self):
        self.assertSequenceEqual([1.0, 1.0], predict.probable_spend([0.5, 0.5], 2.0))

    def test_probable_spend_two_unbalanced(self):
        self.assertSequenceEqual([0.5, 1.5], predict.probable_spend([0.25, 0.75], 2.0))

    def test_probable_spend_sum_is_mean(self):
        mean = 2.0
        mf = [ 0.25, 0.75 ]
        self.assertEqual(mean, sum(predict.probable_spend(mf, mean)))

    def test_last_empty(self):
        self.assertRaises(ValueError, predict.last, [])

    def test_last_one(self):
        ds = "01/01/2015"
        self.assertEqual(dt.strptime(ds, "%d/%m/%Y"), predict.last([[ds]]))

    def test_last_two(self):
        first = "01/01/2015"
        last = "02/01/2015"
        self.assertEqual(dt.strptime(last, "%d/%m/%Y"), predict.last([[first], [last]]))

    def test_align_zero_delta(self):
        bins = [ 0.5, 0.5 ]
        self.assertSequenceEqual(bins, predict.align(bins, 0))

    def test_align_one_delta(self):
        bins = [ 0.5, 0.5 ]
        self.assertSequenceEqual([1.0], predict.align(bins, 1))

    def test_align_one_delta_zero_bin(self):
        bins = [ 0.5, 0.0, 0.5 ]
        self.assertSequenceEqual([0.0, 1.0], predict.align(bins, 1))

    def test_align_zero_negative(self):
        bins = [ -0.5, 0.0, -0.5 ]
        self.assertSequenceEqual([-0.5, 0.0, -0.5], predict.align(bins, 0))

    def test_align_overlong_sequence(self):
        bins = [ 0.0 ]
        self.assertSequenceEqual([0.0], predict.align(bins, 0))

    def test_group_forecast_zero_members(self):
        self.assertRaises(ValueError, predict.group_forecast, [], dt(2015, 2, 1))

    def test_group_forecast_same_day_members(self):
        members = [[ "01/01/2015", -100.0 ], [ "01/01/2015", -100.0 ]]
        fc = predict.group_forecast(members, dt(2015, 1, 1))
        self.assertSequenceEqual([], fc)

    def test_group_forecast_two_members(self):
        members = [[ "01/01/2015", -100.0 ], [ "01/02/2015", -100.0 ]]
        fc = predict.group_forecast(members, dt(2015, 2, 1))
        expected = ([ 0 ] * 30) + [ -100.0 ]
        self.assertSequenceEqual(expected, list(islice(fc, 31)))

    def test_group_forecast_drop(self):
        members = [[ "01/01/2015", -100.0 ], [ "01/02/2015", -100.0 ]]
        fc = predict.group_forecast(members, dt(2015, 4, 1))
        self.assertSequenceEqual([], fc)

    def test_group_forecast_cycle(self):
        members = [[ "01/01/2015", -100.0 ], [ "01/02/2015", -100.0 ]]
        length = 62
        fc = list(islice(predict.group_forecast(members, dt(2015, 2, 1)), length))
        expected = list(islice(cycle(([ 0 ] * 30) + [ -100 ]), length))
        self.assertSequenceEqual(expected, fc)

    def test_forecast_single_expense_group(self):
        # The expense period is 31 days, so given the lengths of the months
        # involved the last payment should be on the 04/03/2015
        groups = [[
            [ "01/01/2015", -100.0 ],
            [ "01/02/2015", -100.0 ],
            [ "04/03/2015", -100.0]
        ]]
        length = 31
        expenses, income = predict.forecast(groups,
                [ dt(2015, 1, 1), dt(2015, 2, 1) ],
                length)
        expected = ([ 0 ] * 30) + [ -100.0 ]
        self.assertSequenceEqual(expected, expenses)
        self.assertSequenceEqual([ 0 ] * length, income)

    def test_forecast_single_income_group(self):
        # The income period is 31 days, so given the lengths of the months
        # involved the last payment should be on the 04/03/2015
        groups = [[
            [ "01/01/2015", 100.0 ],
            [ "01/02/2015", 100.0 ],
            [ "04/03/2015", 100.0]
        ]]
        length = 31
        expenses, income = predict.forecast(groups,
                [ dt(2015, 1, 1), dt(2015, 2, 1) ],
                length)
        expected = ([ 0 ] * 30) + [ 100.0 ]
        self.assertSequenceEqual([ 0 ] * length, expenses)
        self.assertSequenceEqual(expected, income)

    def test_forecast_expenses_income(self):
        groups = [
            [[ "01/01/2015", -100.0 ], [ "01/02/2015", -100.0 ], [ "04/03/2015", -100.0]],
            [[ "15/01/2015", 100.0 ], [ "15/02/2015", 100.0 ], [ "18/03/2015", 100.0]]
        ]
        length = 31
        fc_expenses, fc_income = predict.forecast(groups,
                [ dt(2015, 1, 1), dt(2015, 2, 15) ],
                length)
        ex_expenses = ([ 0 ] * 16) + [ -100.0 ] + ([ 0 ] * 14)
        ex_income = ([ 0 ] * 30) + [ 100.0 ]
        self.assertSequenceEqual(ex_expenses, fc_expenses)
        self.assertSequenceEqual(ex_income, fc_income)

    def test_forecast_expense_noise(self):
        groups = [[[ "01/01/2015", -31.0 ]], [[ "15/01/2015", -31.0 ]]]
        length = 31
        fc_expenses, fc_income = predict.forecast(groups,
                [ dt(2015, 1, 1), dt(2015, 2, 1)],
                length)
        self.assertSequenceEqual([ -2.0 ] * length, fc_expenses)
        self.assertSequenceEqual([ 0 ] * length, fc_income)

    def test_bottoms_zero(self):
        self.assertRaises(ValueError, predict.bottoms, [])

    def test_bottoms_one(self):
        self.assertSequenceEqual([ 0 ], predict.bottoms([ -10 ]))

    def test_bottoms_two(self):
        self.assertSequenceEqual([ 0, -10 ], predict.bottoms([ -10, -20 ]))

import tempfile
import toml
import configparser
import os

class AsTomlTest(unittest.TestCase):
    def test_no_upgrade(self):
        data = { "a" : 0, "b" : { "c" : 1, "d" : { "e" : 2 } } }
        tf = tempfile.NamedTemporaryFile("w", delete=False)
        loaded = None
        try:
            toml.dump(data, tf)
            tf.close()
            loaded = db.as_toml(tf.name)
        finally:
            os.remove(tf.name)
        self.assertEqual(data, loaded)

    def test_do_upgrade(self):
        data = { "a" : { "b" : 0 } }
        tf = tempfile.NamedTemporaryFile("w", delete=False)
        loaded = None
        try:
            cp = configparser.ConfigParser()
            cp.read_dict(data)
            cp.write(tf)
            tf.close()
            loaded = db.as_toml(tf.name)
        finally:
            os.remove(tf.name)
        self.assertEqual(data, loaded)

    def test_fail_upgrade(self):
        tf = tempfile.NamedTemporaryFile("w", delete=False)
        try:
            tf.write("Not valid INI\n")
            tf.close()
            self.assertRaises(TypeError, db.as_toml, [ tf.name ])
        finally:
            os.remove(tf.name)

    def test_fail_open(self):
        tf = tempfile.NamedTemporaryFile("w", delete=False)
        os.remove(tf.name)
        self.assertRaises(TypeError, db.as_toml, [ tf.name ])
        tf.close()

class DbTest(unittest.TestCase):
    def test_db_init_absent(self):
        with tempfile.TemporaryDirectory() as test_dir:
            with tempfile.NamedTemporaryFile("r+") as dbf:
                args = types.SimpleNamespace()
                setattr(args, "nickname", "test")
                setattr(args, "path", dbf.name)
                db.db_init(args, test_dir)

    def test_db_init_present(self):
        with tempfile.TemporaryDirectory() as test_dir:
            with tempfile.NamedTemporaryFile("r+") as dbf1:
                test1 = types.SimpleNamespace()
                setattr(test1, "nickname", "test1")
                setattr(test1, "path", dbf1.name)
                db.db_init(test1, test_dir)
            with tempfile.NamedTemporaryFile("r+") as dbf2:
                test2 = types.SimpleNamespace()
                setattr(test2, "nickname", "test2")
                setattr(test2, "path", dbf2.name)
                db.db_init(test2, test_dir)

    def test_db_init_db_exists(self):
        with tempfile.TemporaryDirectory() as test_dir:
            with tempfile.NamedTemporaryFile("r+") as dbf:
                args = types.SimpleNamespace()
                setattr(args, "nickname", "test")
                setattr(args, "path", dbf.name)
                db.db_init(args, test_dir)
                with self.assertRaises(ValueError):
                    db.db_init(args, test_dir)

    def test_db_update_one_empty(self):
        with tempfile.TemporaryDirectory() as test_dir:
            with tempfile.NamedTemporaryFile("r+") as dbf:
                with tempfile.NamedTemporaryFile("r") as data:
                    args = types.SimpleNamespace()
                    setattr(args, "nickname", "test")
                    setattr(args, "path", dbf.name)
                    db.db_init(args, test_dir)
                    setattr(args, "updates", [ data ])
                    db.db_update(args, test_dir)
                    data.seek(0)
                    self.assertEqual([ ], data.readlines())

    def test_db_update_one_known(self):
        with tempfile.TemporaryDirectory() as test_dir:
            with tempfile.NamedTemporaryFile("r+", delete=False) as dbf:
                with tempfile.NamedTemporaryFile("r+") as data:
                    try:
                        cc = annotate.categories[0]
                        record = "01/01/2019,-12.34,Test Description\n"
                        data.write(record)
                        data.flush()
                        data.seek(0)
                        args = types.SimpleNamespace()
                        setattr(args, "nickname", "test")
                        setattr(args, "path", dbf.name)
                        db.db_init(args, test_dir)
                        setattr(args, "updates", [ data ])
                        t = annotate._Tagger(io=TagInjector([ cc ]))
                        db.db_update(args, test_dir, tagger=t)
                        with open(dbf.name, "r") as newdbf:
                            self.assertEqual([ record[:-1] + "," + cc + "\n" ],
                                             newdbf.readlines())
                    finally:
                        os.remove(dbf.name)


    def test_db_update_one_unknown(self):
        with tempfile.TemporaryDirectory() as test_dir:
            with tempfile.NamedTemporaryFile("r+") as dbf:
                with tempfile.NamedTemporaryFile("r+") as data:
                    data.write(",,\n")
                    data.flush()
                    data.seek(0)
                    args = types.SimpleNamespace()
                    setattr(args, "nickname", "test")
                    setattr(args, "path", dbf.name)
                    db.db_init(args, test_dir)
                    setattr(args, "updates", [ data ])
                    t = annotate._Tagger(io=TagInjector([annotate.categories[0]]))
                    with self.assertRaises(KeyError):
                        db.db_update(args, test_dir, tagger=t)

    def test_db_update_unknown_db(self):
        with tempfile.TemporaryDirectory() as test_dir:
            with tempfile.NamedTemporaryFile("r+") as dbf:
                with tempfile.NamedTemporaryFile("r+") as data:
                    args = types.SimpleNamespace()
                    setattr(args, "nickname", "test")
                    setattr(args, "path", dbf.name)
                    db.db_init(args, test_dir)
                    setattr(args, "nickname", "test1")
                    setattr(args, "updates", [ data ])
                    with self.assertRaises(ValueError):
                        db.db_update(args, test_dir)

class GenerateTest(unittest.TestCase):
    def test_generate(self):
        args = generate.parse_args()
        raw = generate.create_document(args)
        # Check that the document is valid
        cooked = list(combine.combine([ raw ]))
        self.assertEqual(len(raw), len(cooked))
        self.assertTrue(all(x in raw for x in cooked))

class PsaveTest(unittest.TestCase):
    def test_save_from_month_one_month(self):
        then = dt.strptime("01/07/2016", core.date_fmt).date()
        b = psave.Balance(then, 200, -100)
        now = dt.strptime("01/08/2016", core.date_fmt).date()
        h = psave.History(now, { b.month : b } )

        self.assertEqual(100,
                psave.save_from_month(h, {}, then, 100))

    def test_save_from_month_one_month_zero_balance(self):
        then = dt.strptime("01/07/2016", core.date_fmt).date()
        b = psave.Balance(then, 200, -200)
        now = dt.strptime("01/08/2016", core.date_fmt).date()
        h = psave.History(now, { b.month : b } )

        self.assertEqual(0,
                psave.save_from_month(h, {}, then, 100))

    def test_save_from_month_one_month_negative_balance(self):
        then = dt.strptime("01/07/2016", core.date_fmt).date()
        b = psave.Balance(then, 200, -300)
        now = dt.strptime("01/08/2016", core.date_fmt).date()
        h = psave.History(now, { b.month : b } )

        self.assertEqual(0,
                psave.save_from_month(h, {}, then, 100))

    def test_save_from_month_overspent_one_commitment(self):
        then = dt.strptime("01/07/2016", core.date_fmt).date()
        b = psave.Balance(then, 200, -150)
        now = dt.strptime("01/08/2016", core.date_fmt).date()
        h = psave.History(now, { b.month : b } )

        self.assertEqual(50,
                psave.save_from_month(h, {}, then, 100))

    def test_save_from_month_overspent_two_commitments(self):
        then = dt.strptime("01/07/2016", core.date_fmt).date()
        b = psave.Balance(then, 200, -50)
        now = dt.strptime("01/08/2016", core.date_fmt).date()
        h = psave.History(now, { b.month : b } )
        s = {}
        self.assertEqual(100,
                psave.save_from_month(h, s, then, 100))
        self.assertEqual(50,
                psave.save_from_month(h, s, then, 100))

    def test_save_from_month_two_months(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 200, -100)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 200, -100)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        h = psave.History(now, { b1.month : b1, b2.month : b2 } )

        s = {}
        self.assertEqual(50,
                psave.save_from_month(h, s, then1, 50))
        self.assertEqual(50,
                psave.save_from_month(h, s, then2, 50))

    def test_calculate_position_exact(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 200, -151)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 200, -150)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        b3 = psave.Balance(now, 0, 0)
        h = psave.History(now, { b1.month : b1, b2.month : b2,
            b3.month : b3 } )

        tr = psave.Transaction(then1, -100.0, "Test description",
                "test")
        g = psave.Group("Test description", [ tr ])
        c = psave.Commitment(g, g.transactions[-1].value,
                g.transactions[-1].date, td(62, 0, 0))
        ta = psave.Target(c, c.last + c.period)
        s = {}
        self.assertEqual(50,
                psave.calculate_position(h, ta, s).saved)

    def test_calculate_position_overspent(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 200, -151)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 200, -151)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        b3 = psave.Balance(now, 0, 0)
        h = psave.History(now, { b1.month : b1, b2.month : b2,
            b3.month : b3 } )

        tr = psave.Transaction(then1, -100.0, "Test description",
                "test")
        g = psave.Group("Test description", [ tr ])
        c = psave.Commitment(g, g.transactions[-1].value,
                g.transactions[-1].date, td(62, 0, 0))
        ta = psave.Target(c, c.last + c.period)
        s = {}
        self.assertEqual(49,
                psave.calculate_position(h, ta, s).saved)

    def test_calculate_position_underspent(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 200, -149)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 200, -150)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        b3 = psave.Balance(now, 0, 0)
        h = psave.History(now, { b1.month : b1, b2.month : b2,
            b3.month : b3 } )

        tr = psave.Transaction(then1, -100.0, "Test description",
                "test")
        g = psave.Group("Test description", [ tr ])
        c = psave.Commitment(g, g.transactions[-1].value,
                g.transactions[-1].date, td(62, 0, 0))
        ta = psave.Target(c, c.last + c.period)
        s = {}
        self.assertEqual(50,
                psave.calculate_position(h, ta, s).saved)

    def test_calculate_positions_exact(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 200, -100)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 200, -100)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        b3 = psave.Balance(now, 0, 0)
        h = psave.History(now, { b1.month : b1, b2.month : b2,
            b3.month : b3 } )

        tr = psave.Transaction(then1, -100.0, "Test description",
                "test")
        g = psave.Group("Test description", [ tr ])
        c = psave.Commitment(g, g.transactions[-1].value,
                g.transactions[-1].date, td(62, 0, 0))
        ta = psave.Target(c, c.last + c.period)
        p1, p2 = list(psave.calculate_positions(h, [ ta, ta ]))
        self.assertEqual(50, p1[0].saved)
        self.assertEqual(50, p1[1].saved)

    def test_calculate_positions_overspent(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 200, -100)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 200, -101)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        b3 = psave.Balance(now, 0, 0)
        h = psave.History(now, { b1.month : b1, b2.month : b2,
            b3.month : b3 } )

        tr = psave.Transaction(then1, -100.0, "Test description",
                "test")
        g = psave.Group("Test description", [ tr ])
        c = psave.Commitment(g, g.transactions[-1].value,
                g.transactions[-1].date, td(62, 0, 0))
        ta = psave.Target(c, c.last + c.period)
        p1, p2 = list(psave.calculate_positions(h, [ ta, ta ]))
        self.assertEqual(50, p1[0].saved)
        self.assertEqual(49, p1[1].saved)

    def test_calculate_positions_underspent(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 200, -100)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 200, -99)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        b3 = psave.Balance(now, 0, 0)
        h = psave.History(now, { b1.month : b1, b2.month : b2,
            b3.month : b3 } )

        tr = psave.Transaction(then1, -100.0, "Test description",
                "test")
        g = psave.Group("Test description", [ tr ])
        c = psave.Commitment(g, g.transactions[-1].value,
                g.transactions[-1].date, td(62, 0, 0))
        ta = psave.Target(c, c.last + c.period)
        p1, p2 = list(psave.calculate_positions(h, [ ta, ta ]))
        self.assertEqual(50, p1[0].saved)
        self.assertEqual(50, p1[1].saved)

    def test_balance_history_none(self):
        self.assertEqual({},
                psave.balance_history(None, td(1, 0, 0)))

    def test_balance_history_empty(self):
        now = dt.strptime("01/08/2016", core.date_fmt).date()
        h = psave.History(now, {})
        self.assertEqual({},
                psave.balance_history(h, td(1, 0, 0)))

    def test_balance_history_one_positive(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 1, 0)
        now = dt.strptime("01/08/2016", core.date_fmt).date()
        h = psave.History(now, { b1.month : b1 })
        state = psave.balance_history(h, td(1, 0, 0))
        expected = { }
        self.assertEqual(expected, state)

    def test_balance_history_one_negative(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 0, -1)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 0, -1)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        h = psave.History(now, { b1.month : b1, b2.month : b2 })
        with self.assertRaises(ValueError):
            self.assertNotEquals({}, psave.balance_history(h, td(1, 0, 0)))

    def test_balance_history_two_equal(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 1, 0)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 0, -1)
        now = dt.strptime("01/09/2016", core.date_fmt).date()
        h = psave.History(now, { b1.month : b1, b2.month : b2 })
        state = psave.balance_history(h, td(31, 0, 0))
        expected = { then1 : psave.Balance(then1, 0, -1),
                then2 : psave.Balance(then2, 1, 0)}
        self.assertEqual(expected, state)

    def test_balance_history_three(self):
        then1 = dt.strptime("01/07/2016", core.date_fmt).date()
        b1 = psave.Balance(then1, 2, 0)
        then2 = dt.strptime("01/08/2016", core.date_fmt).date()
        b2 = psave.Balance(then2, 0, -1)
        then3 = dt.strptime("01/09/2016", core.date_fmt).date()
        b3 = psave.Balance(then3, 0, -1)
        now = dt.strptime("01/10/2016", core.date_fmt).date()
        h = psave.History(now, { b1.month : b1, b2.month : b2, b3.month : b3 })
        state = psave.balance_history(h, td(31, 0, 0))
        expected = { then1 : psave.Balance(then1, 0, -2),
                then2 : psave.Balance(then2, 1, 0),
                then3 : psave.Balance(then3, 1, 0)}
        self.assertEqual(expected, state)

import tempfile

class SqlGroupCollectionTest(unittest.TestCase):
    def contain(self, func):
        with tempfile.TemporaryDirectory() as test_dir:
            with groups.SqlGroupCollection(test_dir) as sgc:
                func(self, sgc)

    def test_associate_identity(self):
        def test(tc, gc):
            cdid = groups.gen_id("foo", groups.salt)
            gc.associate(cdid, cdid)
        self.contain(test)

    def test_associate_distinct(self):
        def test(tc, gc):
            cdid = groups.gen_id("foo", groups.salt)
            adid = groups.gen_id("bar", groups.salt)
            gc.associate(cdid, adid)
        self.contain(test)

    def test_have_association_identity(self):
        def test(tc, gc):
            cdid = groups.gen_id("foo", groups.salt)
            gc.associate(cdid, cdid)
            self.assertTrue(gc.have_association(cdid))
        self.contain(test)

    def test_have_association_distinct(self):
        def test(tc, gc):
            cdid = groups.gen_id("foo", groups.salt)
            adid = groups.gen_id("bar", groups.salt)
            gc.associate(cdid, adid)
            self.assertTrue(gc.have_association(adid))
        self.contain(test)

    def test_get_canonical_identity(self):
        def test(tc, gc):
            cdid = groups.gen_id("foo", groups.salt)
            gc.associate(cdid, cdid)
            self.assertEqual(cdid, gc.get_canonical(cdid))
        self.contain(test)

    def test_get_canonical_distinct(self):
        def test(tc, gc):
            cdid = groups.gen_id("foo", groups.salt)
            adid = groups.gen_id("bar", groups.salt)
            gc.associate(cdid, adid)
            self.assertEqual(cdid, gc.get_canonical(adid))
        self.contain(test)

class DynamicGroupsTest(unittest.TestCase):
    def contain(self, func, threshold=0.85, size=4):
        with tempfile.TemporaryDirectory() as test_dir:
            gc = groups.SqlGroupCollection(test_dir)
            with groups.DynamicGroups(threshold, size, gc) as dg:
                func(self, dg)

    def test_find_group_empty(self):
        def test(tc, dg):
            self.assertIsNone(dg.find_group("foo"))
        self.contain(test)

    def test_insert_group_one(self):
        def test(tc, dg):
            dg.insert("a" * 10, 'a')
        self.contain(test)

    def test_find_group_empty(self):
        def test(tc, dg):
            self.assertIsNone(dg.find_group("a" * 10))
        self.contain(test)

    def test_find_group_static_exact(self):
        def test(tc, dg):
            inserted = dg.insert("a" * 10, 'a')
            self.assertIsNotNone(inserted)
            found = dg.find_group("a" * 10)
            self.assertIsNotNone(found)
            self.assertEqual(inserted.key(), found.key())
        self.contain(test, size=3)

    def test_find_group_static_fuzzy(self):
        def test(tc, dg):
            inserted = dg.insert("a" * 10, 'a')
            self.assertIsNotNone(inserted)
            found = dg.find_group("a" * 9 + "b")
            self.assertIsNotNone(found)
            self.assertEqual(inserted.key(), found.key())
        self.contain(test, size=0)

    def test_find_group_static_fuzzy_old(self):
        def test(tc, dg):
            one = dg.insert("a" * 10, 'a')
            self.assertIsNotNone(one)
            two = dg.insert("a" * 9 + "b", 'b', one)
            self.assertIsNotNone(two)
            found = dg.find_group("a" * 9 + "b")
            self.assertEqual(one.key(), found.key())
        self.contain(test, size=3)

    def test_find_group_dynamic_exact(self):
        def test(tc, dg):
            inserted = dg.insert("a" * 10, 'a')
            self.assertTrue(inserted == dg.insert("a" * 9 + "b", 'b', inserted))
            found = dg.find_group("a" * 10)
            self.assertIsNotNone(found)
            self.assertEqual(inserted.key(), found.key())
        self.contain(test, size=2)

    def test_find_group_dynamic_fuzzy(self):
        def test(tc, dg):
            inserted = dg.insert("a" * 10, 'a')
            self.assertIsNotNone(inserted)
            self.assertTrue(inserted == dg.insert("a" * 9 + "b", 'b', inserted))
            found = dg.find_group("a" * 9 + "c")
            self.assertIsNotNone(found)
            self.assertEqual(inserted.key(), found.key())
        self.contain(test, size=2)

    def test_find_group_dynamic_fuzzy_multi(self):
        def test(tc, dg):
            inserted = dg.insert("b" * 10, 'b')
            self.assertIsNotNone(inserted)
            inserted = dg.insert("a" * 10, 'a')
            self.assertIsNotNone(inserted)
            self.assertTrue(inserted == dg.insert("a" * 9 + "b", 'b', inserted))
            found = dg.find_group("a" * 9 + "c")
            self.assertIsNotNone(found)
            self.assertEqual(inserted.key(), found.key())
        self.contain(test, size=2)

    def test_add_non_canonical_no_group(self):
        def test(tc, dg):
            inserted = dg.insert("a" * 10, 'a')
            self.assertIsNotNone(inserted)
            one = dg.insert("a" * 9 + "b", 'b', inserted)
            self.assertIsNotNone(one)
            two = dg.insert("a" * 9 + "b", 'b', None)
            self.assertIsNotNone(two)
            self.assertEqual(inserted.key(), one.key())
            self.assertEqual(one.key(), two.key())
            pass
        self.contain(test, size=1)

if __name__ == '__main__':
    unittest.main()
