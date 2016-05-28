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
from itertools import islice, cycle
import unittest
from fpos import annotate, combine, core, transform, visualise, window, predict, db

money = visualise.money

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
        self.assertEquals(test, annotate._Tagger.find_category(needle, annotate.categories))

    def test_category_list(self):
        expected = set([ "Cash", "Commitment", "Dining", "Education", "Entertainment",
            "Health", "Home", "Income", "Internal", "Shopping", "Transport", "Utilities" ])
        self.assertEquals(expected, set(annotate.categories))

    def test_resolve_category_index(self):
        self.assertEquals(annotate.categories[0], annotate._Tagger.resolve_category(0))

    def test_resolve_category_needle(self):
        self.assertEquals(annotate.categories[0], annotate._Tagger.resolve_category(annotate.categories[0]))

class TransformTest(unittest.TestCase):
    expected = [ [ "01/01/2014", "1.00", "Positive" ],
            [ "01/01/2014", "-1.00", "Negative" ] ]

    def test_transform_commbank(self):
        commbank = [ [ "01/01/2014", "1.0", "Positive", "1.0" ],
                [ "01/01/2014", "-1.0", "Negative", "0.0" ] ]
        self.assertEquals(self.expected, list(transform.transform("commbank", commbank)))

    def test_transform_anz(self):
        anz = self.expected
        self.assertEquals(self.expected, list(transform.transform("anz", anz)))

    def test_transform_stgeorge(self):
        stgeorge = iter([ [ "#Date", "Description", "Debit", "Credit", "Balance" ],
                [ "01/01/2014", "Positive", None, "1.0", "1.0" ],
                [ "01/01/2014", "Negative", "1.0", None, "0.0" ] ])
        self.assertEquals(self.expected, list(transform.transform("stgeorge", stgeorge)))

    def test_transform_nab(self):
        nab = iter([ [ "01-Jan-14", "1.00", "1", None, None, "Positive", "1.00", None ],
            [ "01-Jan-14", "-1.00", "2", None, None, "Negative", "0.00", None ] ])
        self.assertEquals(self.expected, list(transform.transform("nab", nab)))

    def test_transform_woolworths(self):
        woolies = iter([
            ["01 Jan 2014", "Positive", "", "1.00", "NaN", "String", "String", None],
            ["01 Jan 2014", "Negative", "1.00", "", "NaN", "String", "String", None],
            ])
        self.assertEquals(self.expected, list(transform.transform("woolworths", woolies)))


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
        self.assertEquals(transform._EMPTY, transform._compute_cell_type(None))

    def test__compute_cell_type__DATE(self):
        self.assertEquals(transform._DATE, transform._compute_cell_type("01/01/2014"))

    def test__compute_cell_type__NUMBER(self):
        self.assertEquals(transform._NUMBER, transform._compute_cell_type("-12.34"))

    def test__compute_cell_type__STRING(self):
        self.assertEquals(transform._STRING, transform._compute_cell_type("neither"))

    def test__sense_form_commbank(self):
        self.assertEquals("commbank", transform._sense_form(["01/01/2014", "-1.0", "description", "-1.0"]))

    def test__sense_form_anz(self):
        self.assertEquals("anz", transform._sense_form(["01/01/2014", "-1.0", "description"]))

    def test__sense_form_stgeorge_debit(self):
        self.assertEquals("stgeorge", transform._sense_form(["01/01/2014",  "description", "1.0", "", "-1.0"]))

    def test__sense_form_stgeorge_credit(self):
        self.assertEquals("stgeorge", transform._sense_form(["01/01/2014",  "description", "", "1.0", "1.0"]))

    def test__sense_form_nab(self):
        self.assertEquals("nab", transform._sense_form(["01/01/2014", "-1.0", "12345", "", "description", "my merchant", "1.0"]))

    def test__sense_form_nab_gh_issue23_0(self):
        self.assertEquals("nab", transform._sense_form("01-May-16,-70.33,071555684686,,CREDIT CARD PURCHASE,FREWVILLE FOODLAND       FREWVILLE,-131.26,".split(',')))

    def test__sense_form_nab_gh_issue23_1(self):
        self.assertEquals("nab", transform._sense_form("29-Mar-16,5.30,000125555398,,MISCELLANEOUS CREDIT,CASHBACK,-60.93,".split(',')))

    def test__sense_form_nab_gh_issue23_2(self):
        self.assertEquals("nab", transform._sense_form("20-Mar-16,-66.23,,,CREDIT CARD PURCHASE,PASADENA FOODLAND,-66.23,".split(',')))

    def test__sense_form_bankwest_cheque(self):
        self.assertEquals("bankwest", transform._sense_form(["", 12345, "01/01/2014", "description", "-1.0", "", "", "-1.0", "cheque"]))

    def test__sense_form_bankwest_debit(self):
        self.assertEquals("bankwest", transform._sense_form(["", 12345, "01/01/2014", "description", "", "1.0", "", "1.0", "debit"]))

    def test__sense_form_bankwest_credit(self):
        self.assertEquals("bankwest", transform._sense_form(["", 12345, "01/01/2014", "description", "", "", "-1.0", "-1.0", "credit"]))

    def test__sense_form_woolworths_debit(self):
        self.assertEquals("woolworths", transform._sense_form("20 Mar 2016,Pie,3.14,,,Food & Drink,Groceries,".split(',')))

    def test__sense_form_woolworths_debit_nan(self):
        self.assertEquals("woolworths", transform._sense_form("19 Mar 2016,Natural log,2.71,,NaN,Food & Drink,Groceries,".split(',')))

    def test__sense_form_woolworths_credit(self):
        self.assertEquals("woolworths", transform._sense_form("01 Mar 2016,Avogadros number - space -,,60221409,NaN,Financial,BPAY Payments,".split(',')))

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
        self.assertEquals(ir, list(window.window(ir, None, None)))

    def test_bounded_start_unbounded_end(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[1] ]
        self.assertEquals(expected, list(window.window(ir, "02/2014", None)))

    def test_unbounded_start_bounded_end(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[0] ]
        self.assertEquals(expected, list(window.window(ir, None, "02/2014")))

    def test_bounded_start_bounded_end(self):
        ir =  [ [ "31/12/2013", "-1.00", "Description" ],
                [ "31/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[1] ]
        self.assertEquals(expected, list(window.window(ir, "01/2014", "02/2014")))

    def test_span_1(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[1] ]
        self.assertEquals(expected, list(window.window(ir, relspan=1)))

    def test_span_2(self):
        ir =  [ [ "31/12/2013", "-1.00", "Description" ],
                [ "31/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = ir[1:]
        self.assertEquals(expected, list(window.window(ir, relspan=2)))

class VisualiseTest(unittest.TestCase):
    def test_group_period_empty(self):
        pg = visualise.PeriodGroup()
        self.assertEquals([], pg.groups())

    def test_group_period_extract_month(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "09/01/2014", "-2.00", "Bar" ]
        months = [ first, second ]
        expected = { "01/2014" : months }
        pg = visualise.PeriodGroup(visualise.extract_month)
        pg.add_all(months)
        result = pg.groups()
        self.assertEquals(1, len(result))
        self.assertEquals(expected, result[0])

    def test_group_period_extract_week(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "09/01/2014", "-2.00", "Bar" ]
        weeks = [ first, second ]
        expected = { "2014:00" : [ first ], "2014:01" : [ second ] }
        pg = visualise.PeriodGroup(visualise.extract_week)
        pg.add_all(weeks)
        result = pg.groups()
        self.assertEquals(1, len(result))
        self.assertEquals(expected, result[0])

    def test_group_period_extract_both(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "02/01/2014", "-2.00", "Foo" ]
        transactions = [ first, second ]
        expected = [ { "01/2014" : [ first, second ] }, { "2014:00" : [ first, second ] } ]
        pg = visualise.PeriodGroup(visualise.extract_month, visualise.extract_week)
        pg.add_all(transactions)
        result = pg.groups()
        self.assertEquals(2, len(result))
        self.assertEquals(expected, result)

    def test_sum_categories_single_spend_multiple_categories(self):
        spent = -1.00
        sspent = money(spent)
        data = []
        for entry in visualise.whitelist:
            data.append([ "01/01/2014", sspent, entry, entry ])
        sc = visualise.sum_categories(data)
        for entry in visualise.whitelist:
            self.assertEquals(sc[entry], spent)

    def test_sum_categories_multiple_spend_single_category(self):
        cat = visualise.whitelist[0]
        spent = -1.00
        data = [ [ "01/01/2014", money(spent), "Foo", cat ] ] * 2
        self.assertEquals(len(data) * spent, visualise.sum_categories(data)[cat])

    def test_income_only_two_months(self):
        month = [ "01/2014", "02/2014" ]
        amount = 1.00
        data = { month[0] : { "Income" : amount },
                 month[1] : { "Income" : amount } }
        expected = { month[0] : amount, month[1] : amount }
        self.assertEquals(expected, visualise.income(data))

    def test_income_mix(self):
        month = "01/2014"
        amount = 1.00
        data = { month : { visualise.whitelist[0] : "0.00", "Income" : amount } }
        expected = { month : amount }
        self.assertEquals(expected, visualise.income(data))

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
        self.assertEquals(expected, visualise.invert(data, visualise.whitelist))

    def test_invert_single_category(self):
        """Ensures unlisted categories are initialised to zero"""
        month = "01/2014"
        amount = -1.00
        single = "Cash"
        data = { month : { single : amount } }
        expected = dict((entry, { month : 0 }) for entry in visualise.whitelist)
        expected[single][month] = amount;
        self.assertEquals(expected, visualise.invert(data, visualise.whitelist))


    def test_category_sum_matrix(self):
        month = [ "01/2014", "02/2014" ]
        amount = -1.00
        summed = { month[0] : { visualise.whitelist[0] : amount },
                   month[1] : { visualise.whitelist[0] : amount } }
        inverted = visualise.invert(summed, visualise.whitelist)
        expected = [ [ amount, amount ] ]
        expected.extend([ [ 0 ] * 2 ] * (len(visualise.whitelist) - 1))
        self.assertEquals(expected, visualise.category_sum_matrix(inverted))

    def test_ignore_one(self):
        month = "01/2014"
        amount = -1.00
        single = "Cash"
        data = { month : { single : amount } }
        expected = { month : {} }
        self.assertEquals(expected, visualise.ignore(data, single))

    def test_ignore_several(self):
        month = "01/2014"
        amount = -1.00
        ignore = [ "Cash", "Dining" ]
        data = { month : dict((i, amount) for i in ignore) }
        expected = { month : {} }
        self.assertEquals(expected, visualise.ignore(data, *ignore))

    def test_surplus(self):
        month = "01/2014"
        amount = -1.00
        expenses = { month : { "Cash" : amount } }
        income = { month : amount * amount }
        self.assertEquals(0.0, visualise.surplus(expenses, income)[month])

    def test_money_zero(self):
        self.assertEquals("0.00", visualise.money(0.0))

    def test_money_one(self):
        self.assertEquals("1.00", visualise.money(1.0))

    def test_money_neg_one(self):
        self.assertEquals("-1.00", visualise.money(-1.0))

    def test_money_one_and_a_bit(self):
        self.assertEquals("-1.00", visualise.money(-1.001))

class CombineTest(unittest.TestCase):
    def test_combine_one_empty(self):
        self.assertEquals([], list(combine.combine([ [] ])))

    def test_combine_invalid_ir(self):
        # Missing the (required) description
        sources = [ [ [ "01/01/2014", -1.00 ] ] ]
        self.assertEquals([], list(combine.combine(sources)))

    def test_combine_3tuple(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ] ] ]
        expected = sources[0]
        self.assertEquals(expected, list(combine.combine(sources)))

    def test_combine_4tuple(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description", "Cash" ] ] ]
        expected = sources[0]
        self.assertEquals(expected, list(combine.combine(sources)))

    def test_combine_two_first_empty(self):
        sources = [ [],
                    [ [ "01/01/2014", -1.00, "Description" ] ] ]
        expected = sources[1]
        self.assertEquals(expected, list(combine.combine(sources)))

    def test_combine_two_distinct(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ] ],
                    [ [ "02/01/2014", -1.00, "Description" ] ] ]
        expected = [ sources[0][0], sources[1][0] ]
        self.assertEquals(expected, list(combine.combine(sources)))

    def test_combine_two_equal(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ] ],
                    [ [ "01/01/2014", -1.00, "Description" ] ] ]
        expected = sources[0]
        self.assertEquals(expected, list(combine.combine(sources)))

    def test_combine_two_superset(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ],
                      [ "02/01/2014", -1.00, "Description" ] ],
                    [ [ "02/01/2014", -1.00, "Description" ] ] ]
        expected = [ sources[0][0], sources[1][0] ]
        self.assertEquals(expected, list(combine.combine(sources)))

    def test_combine_prefer_last(self):
        sources = [ [ [ "01/01/2014", -1.00, "Description" ],
                      [ "02/01/2014", -1.00, "Description" ] ],
                    [ [ "02/01/2014", -1.00, "Description", "Cash" ] ] ]
        expected = [ sources[0][0], sources[1][0] ]
        self.assertEquals(expected, list(combine.combine(sources)))

class CoreTest(unittest.TestCase):
    def test_lcs_empty(self):
        self.assertEquals(0, core.lcs("", ""))

    def test_lcs_a_empty(self):
        self.assertEquals(0, core.lcs("", "a"))

    def test_lcs_b_empty(self):
        self.assertEquals(0, core.lcs("a", ""))

    def test_lcs_equal_single(self):
        self.assertEquals(1, core.lcs("a", "a"))

    def test_lcs_different_single(self):
        self.assertEquals(0, core.lcs("a", "b"))

    def test_lcs_equal_double(self):
        self.assertEquals(2, core.lcs("ab", "ab"))

    def test_lcs_different_double(self):
        self.assertEquals(1, core.lcs("ab", "ba"))

    def test_lcs_different_lengths_a_short(self):
        self.assertEquals(1, core.lcs("abc", "dcba"))

    def test_lcs_different_lengths_b_short(self):
        self.assertEquals(1, core.lcs("dcba", "abc"))

    def test_lcs_similar(self):
        self.assertEquals(1, core.lcs("abbb", "aaaa"))

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
        self.assertEquals(1, predict.period([1]))

    def test_period_spurious(self):
        self.assertEquals(1, predict.period([1, 0]))

    def test_period_multiple(self):
        self.assertEquals(2, predict.period([1, 1]))

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
        self.assertEquals(mean, sum(predict.probable_spend(mf, mean)))

    def test_last_empty(self):
        self.assertRaises(ValueError, predict.last, [])

    def test_last_one(self):
        ds = "01/01/2015"
        self.assertEquals(dt.strptime(ds, "%d/%m/%Y"), predict.last([[ds]]))

    def test_last_two(self):
        first = "01/01/2015"
        last = "02/01/2015"
        self.assertEquals(dt.strptime(last, "%d/%m/%Y"), predict.last([[first], [last]]))

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
