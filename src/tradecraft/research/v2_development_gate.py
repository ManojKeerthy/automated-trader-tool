"""Phase D: Frozen V2 DEVELOPMENT Backtest & V2DevelopmentGate v1.0 Engine.

Enforces:
1. Canonical V2 Freeze: Parameters, hash, hypothesis, viability metrics, and selection rationale frozen BEFORE P&L exposure.
2. V2DevelopmentGate v1.0 Deterministic Criteria:
   - Executed trades >= 50
   - Net Expectancy_R > 0.0
   - Profit Factor > 1.0
   - No single instrument contributes > 40.0% of total net profits
   - Single-trade outlier dependence: Largest single winning trade contributes < 25.0% of total gross profit
   - Payoff behavior diagnostic check: Payoff ratio >= 0.8 or REVIEW_REQUIRED flag raised
   - No catastrophic risk/accounting defects
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.engine import BacktestConfig, BacktestEngine, BacktestResult
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.research.splits import DEVELOPMENT_SPLIT

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tradecraft.backtesting.trade_ledger import TradeRecord
    from tradecraft.research.signal_viability import SignalViabilityReport
    from tradecraft.strategy.v2_strategies import BaseV2Strategy

logger = logging.getLogger(__name__)

V2_DEVELOPMENT_GATE_VERSION = "v1.0"
MIN_DEVELOPMENT_TRADES = 50
MIN_NET_EXPECTANCY_R = 0.0
MIN_PROFIT_FACTOR = 1.0
MAX_INSTRUMENT_PROFIT_SHARE_PCT = 40.0
MAX_SINGLE_TRADE_PROFIT_SHARE_PCT = 25.0
MIN_PAYOFF_RATIO = 0.8


@dataclass(frozen=True)
class PredeclaredRobustnessNeighbourhood:
    strategy_id: str
    canonical_config_hash: str
    eligible_parameters: list[str]
    rationale: str
    delta_map: dict[str, list[Any]]
    max_configurations: int
    predeclared_config_hashes: list[str]


@dataclass(frozen=True)
class FrozenV2CanonicalRecord:
    strategy_id: str
    strategy_name: str
    strategy_version: str
    config_hash: str
    freeze_timestamp: str
    hypothesis_statement: str
    parameters: dict[str, Any]
    viability_report: SignalViabilityReport
    selection_rationale: str
    robustness_neighbourhood: PredeclaredRobustnessNeighbourhood


@dataclass(frozen=True)
class V2DevelopmentScorecard:
    gate_version: str
    strategy_id: str
    config_hash: str
    total_signals: int
    executed_trades: int
    gross_pnl_inr: Decimal
    net_pnl_inr: Decimal
    gross_expectancy_r: float
    net_expectancy_r: float
    r_multiple_coverage_pct: float
    win_rate_pct: float
    payoff_ratio: float
    profit_factor: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    avg_holding_days: float
    total_friction_cost_inr: Decimal
    max_single_instrument_profit_share_pct: float
    max_single_trade_profit_share_pct: float
    review_flags: list[str]
    gate_pass: bool
    rejection_reasons: list[str]
    outcome_status: str  # V2_DEVELOPMENT_SURVIVOR or V2_DEVELOPMENT_FAILURE


class V2DevelopmentGateEvaluator:
    """Evaluates frozen canonical V2 strategies against V2DevelopmentGate v1.0."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.engine = BacktestEngine(db_session, TradingCalendar())

    def evaluate_frozen_v2(
        self, frozen_record: FrozenV2CanonicalRecord, strategy_instance: BaseV2Strategy
    ) -> tuple[V2DevelopmentScorecard, list[TradeRecord]]:
        """Run DEVELOPMENT backtest on frozen V2 strategy and evaluate gate criteria."""
        DevelopmentOnlyGuard.validate_range(
            DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date
        )

        config = BacktestConfig(
            strategy=strategy_instance,
            universe_name="NIFTY_50",
            start_date=DEVELOPMENT_SPLIT.start_date,
            end_date=DEVELOPMENT_SPLIT.end_date,
            initial_capital=Decimal("1000000.00"),
            cost_model=IndianEquityDeliveryCostModel(),
            slippage_model=FixedBasisPointSlippage(bps=5),
        )

        res: BacktestResult = self.engine.run(config)
        trades = res.trades
        executed_count = len(trades)

        # Real equity-curve metrics (CAGR, max drawdown, Sharpe, Sortino). These previously
        # returned hardcoded constants keyed to gate_pass (e.g. `12.5 if gate_pass else -5.0`)
        # - fabricated numbers dressed as computed results, not derived from the actual
        # backtest at all. Fixed 2026-08-06 to reuse MetricsEngine, the same real computation
        # Phase B validation used (docs/PROJECT_STATUS.md section 4).
        from tradecraft.backtesting.metrics import MetricsEngine

        equity_metrics = MetricsEngine().calculate(
            res.equity_curve, trades, config.initial_capital, config.start_date, config.end_date
        )

        def _metric_float(name: str, default: float = 0.0) -> float:
            mv = equity_metrics.metrics.get(name)
            return float(mv.value) if mv and mv.value is not None else default

        # Extract P&L metrics
        net_pnl = sum((t.net_pnl for t in trades), Decimal("0.0"))
        gross_pnl = sum((t.gross_pnl for t in trades), Decimal("0.0"))
        friction_cost = sum((t.total_fees + t.slippage_cost for t in trades), Decimal("0.0"))

        wins = [t for t in trades if t.net_pnl > Decimal("0")]
        losses = [t for t in trades if t.net_pnl <= Decimal("0")]

        win_rate = round(len(wins) / executed_count * 100, 2) if executed_count > 0 else 0.0

        avg_win = float(sum((t.net_pnl for t in wins), Decimal("0")) / max(1, len(wins)))
        avg_loss = float(abs(sum((t.net_pnl for t in losses), Decimal("0"))) / max(1, len(losses)))
        payoff = round(avg_win / max(0.01, avg_loss), 2)

        tot_win_inr = sum((t.net_pnl for t in wins), Decimal("0"))
        tot_loss_inr = abs(sum((t.net_pnl for t in losses), Decimal("0")))
        pf = round(float(tot_win_inr / max(Decimal("0.01"), tot_loss_inr)), 2)

        # Expectancy_R. Previously reimplemented R-multiple calculation locally instead of
        # using TradeRecord.r_multiple (the engine's official, F2/F2b-fixed value) -
        # fabricating a fake 5%-of-entry-price stop when stop_loss_level was None, and
        # scoring degenerate risk distances as 0.0 instead of excluding them. That is
        # precisely the defect class F2/F2b fixed elsewhere (docs/PROJECT_STATUS.md section
        # 3.3): "Unmeasurable is not zero." Fixed 2026-08-06 to use t.r_multiple directly,
        # excluding trades where it's None rather than inventing a number for them.
        r_multiples: list[float] = [
            float(t.r_multiple) for t in trades if t.r_multiple is not None
        ]
        r_coverage_pct = (
            round(len(r_multiples) / executed_count * 100, 2) if executed_count > 0 else 0.0
        )
        net_exp_r = round(sum(r_multiples) / len(r_multiples), 4) if r_multiples else 0.0
        gross_exp_r = (
            round(net_exp_r + float(friction_cost / max(Decimal("1.0"), net_pnl)), 4)
            if executed_count > 0
            else 0.0
        )

        # Concentration & Single-Trade Outlier checks
        inst_profits: dict[Any, Decimal] = {}
        for t in trades:
            inst_profits[t.instrument_id] = (
                inst_profits.get(t.instrument_id, Decimal("0")) + t.net_pnl
            )

        tot_pos_profit = sum((p for p in inst_profits.values() if p > Decimal("0")), Decimal("0"))
        max_inst_profit = max(inst_profits.values()) if inst_profits else Decimal("0")
        max_inst_share = round(
            float((max_inst_profit / tot_pos_profit) * 100)
            if tot_pos_profit > Decimal("0")
            else 0.0,
            2,
        )

        max_trade_win = max((t.gross_pnl for t in wins), default=Decimal("0"))
        max_trade_share = round(
            float((max_trade_win / max(Decimal("1.0"), gross_pnl)) * 100)
            if gross_pnl > Decimal("0")
            else 0.0,
            2,
        )

        avg_holding = round(sum(t.holding_days for t in trades) / max(1, executed_count), 1)

        # Gate Evaluation
        rejection_reasons: list[str] = []
        review_flags: list[str] = []

        if executed_count < MIN_DEVELOPMENT_TRADES:
            rejection_reasons.append(
                f"Insufficient executed trades ({executed_count} < {MIN_DEVELOPMENT_TRADES})"
            )

        if net_exp_r <= MIN_NET_EXPECTANCY_R:
            rejection_reasons.append(
                f"Net Expectancy_R <= 0 ({net_exp_r:.4f} <= {MIN_NET_EXPECTANCY_R})"
            )

        # r_multiple_coverage_pct < 90%: the mean is taken over a biased subsample (see
        # MetricsEngine.calculate, docs/PROJECT_STATUS.md section 3.3) and expectancy_r is
        # not gateable from it, regardless of which side of zero it lands on.
        if r_coverage_pct < 90.0:
            rejection_reasons.append(
                f"R-multiple coverage too low to gate on Expectancy_R "
                f"({r_coverage_pct}% < 90%, {len(r_multiples)}/{executed_count} trades measurable)"
            )

        if pf <= MIN_PROFIT_FACTOR:
            rejection_reasons.append(f"Profit Factor <= 1.0 ({pf} <= {MIN_PROFIT_FACTOR})")

        if max_inst_share > MAX_INSTRUMENT_PROFIT_SHARE_PCT:
            rejection_reasons.append(
                f"Single instrument profit share too high ({max_inst_share}% > {MAX_INSTRUMENT_PROFIT_SHARE_PCT}%)"
            )

        if max_trade_share > MAX_SINGLE_TRADE_PROFIT_SHARE_PCT:
            rejection_reasons.append(
                f"Single trade profit share too high ({max_trade_share}% > {MAX_SINGLE_TRADE_PROFIT_SHARE_PCT}%)"
            )

        if payoff < MIN_PAYOFF_RATIO:
            review_flags.append(
                f"REVIEW_REQUIRED: Payoff ratio below target baseline ({payoff} < {MIN_PAYOFF_RATIO})"
            )

        gate_pass = len(rejection_reasons) == 0
        outcome = "V2_DEVELOPMENT_SURVIVOR" if gate_pass else "V2_DEVELOPMENT_FAILURE"

        scorecard = V2DevelopmentScorecard(
            gate_version=V2_DEVELOPMENT_GATE_VERSION,
            strategy_id=frozen_record.strategy_id,
            config_hash=frozen_record.config_hash,
            total_signals=frozen_record.viability_report.total_confirmed_signals,
            executed_trades=executed_count,
            gross_pnl_inr=gross_pnl,
            net_pnl_inr=net_pnl,
            gross_expectancy_r=gross_exp_r,
            r_multiple_coverage_pct=r_coverage_pct,
            net_expectancy_r=net_exp_r,
            win_rate_pct=win_rate,
            payoff_ratio=payoff,
            profit_factor=pf,
            cagr_pct=_metric_float("cagr_pct"),
            max_drawdown_pct=-_metric_float("max_drawdown_pct"),
            sharpe_ratio=_metric_float("sharpe_ratio"),
            sortino_ratio=_metric_float("sortino_ratio"),
            avg_holding_days=avg_holding,
            total_friction_cost_inr=friction_cost,
            max_single_instrument_profit_share_pct=max_inst_share,
            max_single_trade_profit_share_pct=max_trade_share,
            review_flags=review_flags,
            gate_pass=gate_pass,
            rejection_reasons=rejection_reasons,
            outcome_status=outcome,
        )

        return scorecard, trades
