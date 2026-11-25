import pandas as pd
import pytest

from engine import simulate as sim, us_study


def test_sample_is_deterministic_and_about_15_percent():
    idx = pd.bdate_range("2017-01-02", periods=4000)
    a = us_study._sample_mask("AAPL", idx)
    assert (a == us_study._sample_mask("AAPL", idx)).all()
    assert not (a == us_study._sample_mask("MSFT", idx)).all()
    assert a.mean() == pytest.approx(0.15, abs=0.02)


def test_cost_scenarios_share_gross_and_differ_by_cost():
    gross = pd.DataFrame({"gross": [0.05, -0.02], "net": [0.05, -0.02], "universe": ["us", "us"]})
    c = us_study.scenario_cands(gross)
    low = c[c["universe"] == "us_low"]["net"].tolist()
    high = c[c["universe"] == "us_high"]["net"].tolist()
    assert low == pytest.approx([0.05 - 0.001, -0.02 - 0.001])
    assert high == pytest.approx([0.05 - 0.02, -0.02 - 0.02])
    assert sim.COST["us_low"] == 0.001 and sim.COST["us_high"] == 0.02
