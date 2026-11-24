import pandas as pd

from engine import news


def frame(rows):
    return pd.DataFrame(rows, columns=["ret_1d", "vol_ratio", "gap_1d", "ret_20d_prior", "earnings",
                                       "earnings_covered"])


def test_news4_and_news6_thresholds():
    c = frame([(0.04, 3.0, 0, 0.1, False, True), (0.0399, 9, 0, 0.1, False, True), (0.05, 2.99, 0, 0.1, False, True),
               (0.06, 5.0, 0, 0.1, False, True), (0.06, 4.9, 0, 0.1, False, True)])
    assert list(news.EVENTS["news4"](c)) == [True, False, False, True, True]
    assert list(news.EVENTS["news6"](c)) == [False, False, False, True, False]


def test_gap_vs_intraday_split_at_half_the_move():
    # +6% day: a 3% gap is a gap event, a 2.9% gap is intraday
    c = frame([(0.06, 4, 0.03, 0.1, False, True), (0.06, 4, 0.029, 0.1, False, True)])
    assert list(news.EVENTS["news4 gap"](c)) == [True, False]
    assert list(news.EVENTS["news4 intraday"](c)) == [False, True]


def test_reversal_vs_continuation():
    c = frame([(0.05, 4, 0, -0.02, False, True), (0.05, 4, 0, 0.02, False, True)])
    assert list(news.EVENTS["news4 reversal"](c)) == [True, False]
    assert list(news.EVENTS["news4 continuation"](c)) == [False, True]


def test_earnings_split_needs_a_covering_calendar():
    c = frame([(0.05, 4, 0, 0, True, True), (0.05, 4, 0, 0, False, True), (0.05, 4, 0, 0, False, False)])
    assert list(news.EVENTS["news4 earnings"](c)) == [True, False, False]
    assert list(news.EVENTS["news4 non-earnings"](c)) == [False, True, False]
