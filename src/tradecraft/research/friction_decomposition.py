"""M3B.1 Gross vs Net Edge Friction Decomposition Module.

Decomposes strategy performance into:
- Gross Strategy P&L (Zero fees, zero slippage)
- Explicit Transaction Costs (STT, Exchange fees, SEBI, GST, Stamp duty, DP charges)
- Slippage Drag (5 bps baseline impact)
Classifies failure mechanism: STRUCTURALLY_NEGATIVE_GROSS_EDGE vs POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel, ZeroCostModel
from tradecraft.backtesting.engine import BacktestConfig, BacktestEngine, BacktestResult
from tradecraft.backtesting.metrics import MetricValue
from tradecraft.backtesting.slippage import FixedBasisPointSlippage, ZeroSlippage
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.diagnostics import TrainOnlyGuard
from tradecraft.research.splits import TRAIN_SPLIT

logger = logging.getLogger(__name__)


@dataclass
class FrictionDecompositionReport:
    """Detailed decomposition of gross edge vs friction drag."""

    strategy_id: str
    total_trades: int
    gross_pnl_inr: Decimal
    net_pnl_inr: Decimal
    total_transaction_fees_inr: Decimal
    total_slippage_cost_inr: Decimal
    total_friction_drag_inr: Decimal
    gross_expectancy_r: float
    net_expectancy_r: float
    cost_drag_per_trade_inr: Decimal
    cost_drag_bps_round_trip: float
    friction_pct_of_gross_profit: float
    failure_classification: str  # STRUCTURALLY_NEGATIVE_GROSS_EDGE, POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION, MIXED_INCONCLUSIVE


class FrictionDecomposer:
    """Decomposes trade P&L into gross edge, explicit accounting costs, and slippage drag."""

    def __init__(self, db_session: Session, calendar_instance: TradingCalendar):
        self.db = db_session
        self.cal = calendar_instance

    def decompose(self, net_res: BacktestResult) -> FrictionDecompositionReport:
        """Run counterfactual zero-friction evaluation to isolate gross vs net edge."""
        # Enforce date boundary
        TrainOnlyGuard.validate_range(net_res.config.start_date, net_res.config.end_date)

        strat_id = net_res.config.strategy.strategy_id
        net_trades = net_res.trades
        total_trades = len(net_trades)

        # Calculate explicit costs & slippage from net backtest result
        net_pnl = sum((t.net_pnl for t in net_trades), Decimal("0"))
        total_fees = sum((t.total_fees for t in net_trades), Decimal("0"))
        total_slippage = sum((t.slippage_cost for t in net_trades), Decimal("0"))
        total_friction = total_fees + total_slippage

        # Retrieve Net Expectancy_R
        net_exp_r_metric = net_res.metrics.metrics.get("expectancy_r")
        net_exp_r = float(net_exp_r_metric.value) if isinstance(net_exp_r_metric, MetricValue) and net_exp_r_metric.value is not None else 0.0

        # Run POST-HOC FAILURE DIAGNOSTIC counterfactual zero-friction evaluation
        engine = BacktestEngine(db_session=self.db, calendar_instance=self.cal)
        config_gross = BacktestConfig(
            strategy=net_res.config.strategy,
            start_date=TRAIN_SPLIT.start_date,
            end_date=TRAIN_SPLIT.end_date,
            initial_capital=net_res.config.initial_capital,
            cost_model=ZeroCostModel(),
            slippage_model=ZeroSlippage(),
        )
        gross_res = engine.run(config_gross)

        gross_pnl = sum((t.net_pnl for t in gross_res.trades), Decimal("0"))
        gross_exp_r_metric = gross_res.metrics.metrics.get("expectancy_r")
        gross_exp_r = float(gross_exp_r_metric.value) if isinstance(gross_exp_r_metric, MetricValue) and gross_exp_r_metric.value is not None else 0.0

        # Cost drag metrics
        cost_drag_per_trade = (total_friction / Decimal(str(total_trades))) if total_trades > 0 else Decimal("0")
        cost_drag_bps = (float(total_friction) / float(net_res.config.initial_capital) * 10000.0 / total_trades) if total_trades > 0 else 0.0
        friction_pct_gross = (float(total_friction) / float(gross_pnl) * 100.0) if gross_pnl > Decimal("0") else 0.0

        # Assign Failure Classification
        if total_trades < 5:
            classification = "MIXED_INCONCLUSIVE"
        elif gross_exp_r <= 0.0:
            classification = "STRUCTURALLY_NEGATIVE_GROSS_EDGE"
        elif gross_exp_r > 0.0 and net_exp_r <= 0.0:
            classification = "POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION"
        else:
            classification = "MIXED_INCONCLUSIVE"

        return FrictionDecompositionReport(
            strategy_id=strat_id,
            total_trades=total_trades,
            gross_pnl_inr=gross_pnl,
            net_pnl_inr=net_pnl,
            total_transaction_fees_inr=total_fees,
            total_slippage_cost_inr=total_slippage,
            total_friction_drag_inr=total_friction,
            gross_expectancy_r=gross_exp_r,
            net_expectancy_r=net_exp_r,
            cost_drag_per_trade_inr=cost_drag_per_trade,
            cost_drag_bps_round_trip=cost_drag_bps,
            friction_pct_of_gross_profit=friction_pct_gross,
            failure_classification=classification,
        )
