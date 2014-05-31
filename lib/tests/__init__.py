#!/usr/bin/python3
#
#    Tests functionality in user scripts
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

from datetime import datetime as dt
import unittest
from fpos import annotate, combine, core, transform, visualise, window

_LcsTagger = annotate._LcsTagger
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

class LcsTaggerTest(unittest.TestCase):
    def test_lcs_match_none(self):
        tagger = _LcsTagger()
        self.assertEquals(None, tagger.classify("foo"))

    def test_lcs_match_one_exact(self):
        tagger = _LcsTagger()
        text = "foo"
        tag = "bar"
        self.assertEquals(None, tagger.classify(text))
        self.assertTrue(tagger.pending())
        tagger.tag(tag)
        self.assertEquals(tag, tagger.classify(text))

    def test_lcs_match_one_fuzzy(self):
        tagger = _LcsTagger()
        a_text = "foo0"
        b_text = "foo1"
        tag = "bar"
        tagger.classify(a_text, tag)
        self.assertEquals(tag, tagger.classify(b_text))

    def test_lcs_miss_one(self):
        tagger = _LcsTagger()
        a_text = "aaaa"
        b_text = "bbaa"
        tag = "bar"
        tagger.classify(a_text, tag)
        self.assertEquals(None, tagger.classify(b_text))

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
        stgeorge = iter([ [ "Date", "Description", "Debit", "Credit", "Balance" ],
                [ "01/01/2014", "Positive", None, "1.0", "1.0" ],
                [ "01/01/2014", "Negative", "1.0", None, "0.0" ] ])
        self.assertEquals(self.expected, list(transform.transform("stgeorge", stgeorge)))

    def test_transform_nab(self):
        nab = iter([ [ "01-Jan-14", "1.00", "1", None, None, "Positive", "1.00", None ],
            [ "01-Jan-14", "-1.00", "2", None, None, "Negative", "0.00", None ] ])
        self.assertEquals(self.expected, list(transform.transform("nab", nab)))

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
        self.assertEquals(ir, list(window.window(None, None, ir)))

    def test_bounded_start_unbounded_end(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[1] ]
        self.assertEquals(expected, list(window.window("02/2014", None, ir)))

    def test_unbounded_start_bounded_end(self):
        ir =  [ [ "01/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[0] ]
        self.assertEquals(expected, list(window.window(None, "02/2014", ir)))

    def test_bounded_start_bounded_end(self):
        ir =  [ [ "31/12/2013", "-1.00", "Description" ],
                [ "31/01/2014", "-1.00", "Description" ],
                [ "01/02/2014", "-1.00", "Description" ] ]
        expected = [ ir[1] ]
        self.assertEquals(expected, list(window.window("01/2014", "02/2014", ir)))

class VisualiseTest(unittest.TestCase):
    def test_group_period_empty(self):
        self.assertEquals({}, visualise.group_period([])[0])

    def test_group_period_extract_month(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "09/01/2014", "-2.00", "Bar" ]
        month = [ first, second ]
        expected = { "01/2014" : month }
        result = visualise.group_period(month, [ visualise.extract_month ])
        self.assertEquals(1, len(result))
        self.assertEquals(expected, result[0])

    def test_group_period_extract_week(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "09/01/2014", "-2.00", "Bar" ]
        week = [ first, second ]
        expected = { "2014:00" : [ first ], "2014:01" : [ second ] }
        result = visualise.group_period(week, [ visualise.extract_week ])
        self.assertEquals(1, len(result))
        self.assertEquals(expected, result[0])

    def test_group_period_extract_both(self):
        first = [ "01/01/2014", "-1.00", "Foo" ]
        second = [ "02/01/2014", "-2.00", "Foo" ]
        transactions = [ first, second ]
        expected = [ { "01/2014" : [ first, second ] }, { "2014:00" : [ first, second ] } ]
        result = visualise.group_period(transactions, [ visualise.extract_month, visualise.extract_week ])
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
