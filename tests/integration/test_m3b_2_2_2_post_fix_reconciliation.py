"""Integration tests for M3B.2.2.2 post-fix accounting and temporal reconciliation on PostgreSQL."""
from decimal import Decimal
import pytest
from tradecraft.core.db import SessionLocal
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.backtesting.engine import BacktestEngine, BacktestConfig, EndOfBacktestPolicy
from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.research.splits import DEVELOPMENT_SPLIT
from tradecraft.strategy.v2_strategies import (
    TrendPullbackV2Strategy,
    BreakoutConfirmV2Strategy,
    MomentumRSV2Strategy,
    MeanReversionV2Strategy,
)

@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def calendar():
    return TradingCalendar()

@pytest.mark.parametrize(
    "strategy_cls",
    [
        TrendPullbackV2Strategy,
        BreakoutConfirmV2Strategy,
        MomentumRSV2Strategy,
        MeanReversionV2Strategy,
    ],
)
def test_post_fix_accounting_and_temporal_invariants(db_session, calendar, strategy_cls):
    """Verify 0.0000 INR cash residual and 0 temporal violations across all strategies under FORCE_CLOSE."""
    strat = strategy_cls()
    config = BacktestConfig(
        strategy=strat,
        universe_name="NIFTY_50",
        start_date=DEVELOPMENT_SPLIT.start_date,
        end_date=DEVELOPMENT_SPLIT.end_date,
        initial_capital=Decimal("1000000.00"),
        cost_model=IndianEquityDeliveryCostModel(),
        slippage_model=FixedBasisPointSlippage(bps=5),
        end_of_backtest_policy=EndOfBacktestPolicy.FORCE_CLOSE,
    )

    engine = BacktestEngine(db_session, calendar)
    res = engine.run(config)
    trades = res.trades

    # Invariant 1: 0 open positions remaining under FORCE_CLOSE
    final_snapshot = res.equity_curve[-1]
    assert final_snapshot.open_positions == 0

    # Invariant 2: Temporal Execution Invariant signal_date < entry_date <= exit_date
    temporal_violations = [
        t for t in trades if not (t.signal_date < t.entry_date <= t.exit_date)
    ]
    assert len(temporal_violations) == 0

    # Invariant 3: Accounting Discrepancy == 0.0000 INR
    final_equity = final_snapshot.total_equity
    equity_diff = final_equity - config.initial_capital
    sum_trade_net_pnl = sum((t.net_pnl for t in trades), Decimal("0"))
    res_diff = abs(equity_diff - sum_trade_net_pnl)

    assert abs(res_diff) < Decimal("0.0001")
