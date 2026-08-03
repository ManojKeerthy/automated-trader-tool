"""Unit tests for EarningsDriftV1Strategy."""

from decimal import Decimal

from tradecraft.strategy.earnings_drift_v1 import EarningsDriftV1Config, EarningsDriftV1Strategy


def test_earnings_drift_v1_initialization():
    strat = EarningsDriftV1Strategy()
    assert strat.strategy_id == "strat_earnings_drift_v1"
    assert strat.version == "1.0.0"
    assert strat.hypothesis_uuid == "hypo-cycle2-alpha013-v1"
    assert strat.config.holding_period_max_sessions == 30
    assert strat.config.atr_stop_multiplier == Decimal("2.0")


def test_earnings_drift_v1_config_customization():
    cfg = EarningsDriftV1Config(
        holding_period_max_sessions=45,
        atr_stop_multiplier=Decimal("2.5"),
    )
    strat = EarningsDriftV1Strategy(config=cfg)
    assert strat.config.holding_period_max_sessions == 45
    assert strat.config.atr_stop_multiplier == Decimal("2.5")
