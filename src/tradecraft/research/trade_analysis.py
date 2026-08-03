"""M3B.1 Trade Distribution, MAE/MFE, Exit-Reason & Holding-Period Diagnostic Module.

Calculates:
1. R-multiple percentiles (10, 25, 50, 75, 90th), mean, median, payoff ratio, win/loss streaks.
2. Daily OHLC MAE_R and MFE_R while position is open.
3. Exit-reason categorization.
4. Holding-period duration bucketing (1-2, 3-5, 6-10, 11-20, >20 sessions).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import and_, select

from tradecraft.core.db_models import MarketBar
from tradecraft.research.diagnostics import TrainOnlyGuard

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date

    from sqlalchemy.orm import Session

    from tradecraft.backtesting.trade_ledger import TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class RMultipleStats:
    """R-multiple summary statistics."""

    mean_r: float = 0.0
    median_r: float = 0.0
    std_r: float = 0.0
    p10_r: float = 0.0
    p25_r: float = 0.0
    p75_r: float = 0.0
    p90_r: float = 0.0
    max_win_r: float = 0.0
    max_loss_r: float = 0.0
    win_rate_pct: float = 0.0
    payoff_ratio: float = 0.0
    profit_factor: float = 0.0
    longest_winning_streak: int = 0
    longest_losing_streak: int = 0


@dataclass
class MAEMFEReport:
    """Maximum Adverse / Favorable Excursion analysis."""

    mean_mae_r: float = 0.0
    median_mae_r: float = 0.0
    mean_mfe_r: float = 0.0
    median_mfe_r: float = 0.0
    mfe_capture_efficiency_pct: float = 0.0
    stopped_out_after_high_mfe_count: int = 0


@dataclass
class ExitReasonGroupStats:
    """Statistics for a specific exit reason."""

    exit_reason: str
    count: int = 0
    percentage: float = 0.0
    mean_r: float = 0.0
    median_r: float = 0.0
    win_rate_pct: float = 0.0


@dataclass
class HoldingPeriodBucketStats:
    """Statistics for a holding period duration bucket."""

    bucket_label: str
    count: int = 0
    mean_r: float = 0.0
    median_r: float = 0.0
    win_rate_pct: float = 0.0
    net_pnl_inr: Decimal = Decimal("0")


@dataclass
class TradeAnalysisReport:
    """Comprehensive diagnostic trade analysis report."""

    strategy_id: str
    total_trades: int
    r_stats: RMultipleStats
    excursion_stats: MAEMFEReport
    exit_reasons: list[ExitReasonGroupStats] = field(default_factory=list)
    holding_buckets: list[HoldingPeriodBucketStats] = field(default_factory=list)


class TradeDistributionAnalyzer:
    """Analyzes trade distributions, MAE/MFE, exit reasons, and holding durations."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def analyze(self, strategy_id: str, trades: list[TradeRecord], start_date: date, end_date: date) -> TradeAnalysisReport:
        """Run comprehensive trade analysis."""
        TrainOnlyGuard.validate_range(start_date, end_date)

        total_trades = len(trades)
        if total_trades == 0:
            return TradeAnalysisReport(
                strategy_id=strategy_id,
                total_trades=0,
                r_stats=RMultipleStats(),
                excursion_stats=MAEMFEReport(),
            )

        # 1. Calculate R-multiples for each trade
        r_multiples: list[float] = []
        winning_rs: list[float] = []
        losing_rs: list[float] = []
        winners_count = 0
        losers_count = 0

        current_win_streak = 0
        max_win_streak = 0
        current_loss_streak = 0
        max_loss_streak = 0

        for t in trades:
            init_risk = abs(t.entry_price - t.stop_loss_level) if t.stop_loss_level else (t.entry_price * Decimal("0.05"))
            r_val = float(t.net_pnl / (init_risk * t.quantity)) if init_risk > Decimal("0") and t.quantity > 0 else 0.0
            r_multiples.append(r_val)

            if t.net_pnl > Decimal("0"):
                winners_count += 1
                winning_rs.append(r_val)
                current_win_streak += 1
                max_win_streak = max(max_win_streak, current_win_streak)
                current_loss_streak = 0
            elif t.net_pnl < Decimal("0"):
                losers_count += 1
                losing_rs.append(r_val)
                current_loss_streak += 1
                max_loss_streak = max(max_loss_streak, current_loss_streak)
                current_win_streak = 0

        r_arr = np.array(r_multiples)
        mean_r = float(np.mean(r_arr))
        median_r = float(np.median(r_arr))
        std_r = float(np.std(r_arr)) if len(r_arr) > 1 else 0.0
        p10 = float(np.percentile(r_arr, 10))
        p25 = float(np.percentile(r_arr, 25))
        p75 = float(np.percentile(r_arr, 75))
        p90 = float(np.percentile(r_arr, 90))

        win_rate = (winners_count / total_trades * 100.0)
        avg_win_r = float(np.mean(winning_rs)) if winning_rs else 0.0
        avg_loss_r = abs(float(np.mean(losing_rs))) if losing_rs else 1.0
        payoff = avg_win_r / avg_loss_r if avg_loss_r > 0 else 0.0

        gross_wins = sum((t.net_pnl for t in trades if t.net_pnl > Decimal("0")), Decimal("0"))
        gross_losses = abs(sum((t.net_pnl for t in trades if t.net_pnl < Decimal("0")), Decimal("0")))
        pf = float(gross_wins / gross_losses) if gross_losses > Decimal("0") else 1.0

        r_stats = RMultipleStats(
            mean_r=mean_r,
            median_r=median_r,
            std_r=std_r,
            p10_r=p10,
            p25_r=p25,
            p75_r=p75,
            p90_r=p90,
            max_win_r=float(np.max(r_arr)),
            max_loss_r=float(np.min(r_arr)),
            win_rate_pct=win_rate,
            payoff_ratio=payoff,
            profit_factor=pf,
            longest_winning_streak=max_win_streak,
            longest_losing_streak=max_loss_streak,
        )

        # 2. MAE / MFE Diagnostics on Daily OHLC
        maes: list[float] = []
        mfes: list[float] = []
        stopped_after_mfe = 0

        for t in trades:
            init_risk_dec = abs(t.entry_price - t.stop_loss_level) if t.stop_loss_level else (t.entry_price * Decimal("0.05"))
            init_risk_flt: float = float(init_risk_dec)
            if init_risk_flt <= 0.0:
                init_risk_flt = float(t.entry_price) * 0.05

            # Fetch daily bars strictly while open (entry_date <= trading_date <= exit_date)
            stmt = (
                select(MarketBar)
                .where(
                    and_(
                        MarketBar.instrument_id == t.instrument_id,
                        MarketBar.is_adjusted == False,  # noqa: E712
                        MarketBar.trading_date >= t.entry_date,
                        MarketBar.trading_date <= t.exit_date,
                    )
                )
                .order_by(MarketBar.trading_date)
            )
            open_bars = list(self.db.scalars(stmt).all())

            if open_bars:
                highest_high = max(float(b.high) for b in open_bars)
                lowest_low = min(float(b.low) for b in open_bars)
                entry_p = float(t.entry_price)

                if t.direction == "BUY":
                    mae_val = (entry_p - lowest_low) / init_risk_flt
                    mfe_val = (highest_high - entry_p) / init_risk_flt
                else:
                    mae_val = (highest_high - entry_p) / init_risk_flt
                    mfe_val = (entry_p - lowest_low) / init_risk_flt

                maes.append(max(0.0, mae_val))
                mfes.append(max(0.0, mfe_val))

                if mfe_val > 1.5 and t.net_pnl < Decimal("0"):
                    stopped_after_mfe += 1
            else:
                maes.append(0.0)
                mfes.append(0.0)

        mean_mae = float(np.mean(maes)) if maes else 0.0
        median_mae = float(np.median(maes)) if maes else 0.0
        mean_mfe = float(np.mean(mfes)) if mfes else 0.0
        median_mfe = float(np.median(mfes)) if mfes else 0.0
        mfe_capture = (mean_r / mean_mfe * 100.0) if mean_mfe > 0 else 0.0

        excursion_stats = MAEMFEReport(
            mean_mae_r=mean_mae,
            median_mae_r=median_mae,
            mean_mfe_r=mean_mfe,
            median_mfe_r=median_mfe,
            mfe_capture_efficiency_pct=mfe_capture,
            stopped_out_after_high_mfe_count=stopped_after_mfe,
        )

        # 3. Exit Reason Analysis
        exit_groups: dict[str, list[TradeRecord]] = {}
        for t in trades:
            reason = t.exit_reason or "UNKNOWN"
            exit_groups.setdefault(reason, []).append(t)

        exit_reports: list[ExitReasonGroupStats] = []
        for reason, grp in exit_groups.items():
            grp_cnt = len(grp)
            grp_pct = (grp_cnt / total_trades * 100.0)
            grp_wins = sum(1 for t in grp if t.net_pnl > Decimal("0"))
            grp_rs = [float(t.net_pnl / (abs(t.entry_price - (t.stop_loss_level or t.entry_price * Decimal("0.95"))) * t.quantity)) for t in grp]
            exit_reports.append(
                ExitReasonGroupStats(
                    exit_reason=reason,
                    count=grp_cnt,
                    percentage=grp_pct,
                    mean_r=float(np.mean(grp_rs)),
                    median_r=float(np.median(grp_rs)),
                    win_rate_pct=(grp_wins / grp_cnt * 100.0),
                )
            )

        # 4. Holding Period Duration Buckets
        bucket_defs: list[tuple[str, Callable[[int], bool]]] = [
            ("1-2 sessions", lambda d: d <= 2),
            ("3-5 sessions", lambda d: 3 <= d <= 5),
            ("6-10 sessions", lambda d: 6 <= d <= 10),
            ("11-20 sessions", lambda d: 11 <= d <= 20),
            (">20 sessions", lambda d: d > 20),
        ]

        holding_reports: list[HoldingPeriodBucketStats] = []
        for label, cond in bucket_defs:
            b_trades = [t for t in trades if cond(t.holding_days)]
            b_cnt = len(b_trades)
            if b_cnt > 0:
                b_wins = sum(1 for t in b_trades if t.net_pnl > Decimal("0"))
                b_rs = [float(t.net_pnl / (abs(t.entry_price - (t.stop_loss_level or t.entry_price * Decimal("0.95"))) * t.quantity)) for t in b_trades]
                b_net_pnl = sum((t.net_pnl for t in b_trades), Decimal("0"))
                holding_reports.append(
                    HoldingPeriodBucketStats(
                        bucket_label=label,
                        count=b_cnt,
                        mean_r=float(np.mean(b_rs)),
                        median_r=float(np.median(b_rs)),
                        win_rate_pct=(b_wins / b_cnt * 100.0),
                        net_pnl_inr=b_net_pnl,
                    )
                )
            else:
                holding_reports.append(HoldingPeriodBucketStats(bucket_label=label, count=0))

        return TradeAnalysisReport(
            strategy_id=strategy_id,
            total_trades=total_trades,
            r_stats=r_stats,
            excursion_stats=excursion_stats,
            exit_reasons=exit_reports,
            holding_buckets=holding_reports,
        )
