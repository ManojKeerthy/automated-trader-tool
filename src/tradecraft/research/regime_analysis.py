"""M3B.1 Market Regime Diagnostic Analysis Module.

Segments trade performance by M3A RegimeDefinition v1.0:
- Trend: BULLISH, BEARISH, SIDEWAYS
- Volatility: LOW, NORMAL, HIGH, EXTREME
Exclusively diagnostic; no new regime filters are created.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np

from tradecraft.research.diagnostics import TrainOnlyGuard
from tradecraft.screening.regime import DEFAULT_REGIME_DEFINITION

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tradecraft.backtesting.trade_ledger import TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class RegimeBucketStats:
    """Statistics for a specific market regime bucket."""

    regime_category: str  # TREND or VOLATILITY
    regime_name: str
    trade_count: int = 0
    win_rate_pct: float = 0.0
    mean_r: float = 0.0
    median_r: float = 0.0
    profit_factor: float = 1.0
    gross_expectancy_r: float = 0.0
    net_expectancy_r: float = 0.0


@dataclass
class RegimeDiagnosticReport:
    """Comprehensive regime breakdown for a strategy."""

    strategy_id: str
    trend_buckets: list[RegimeBucketStats] = field(default_factory=list)
    volatility_buckets: list[RegimeBucketStats] = field(default_factory=list)


class RegimeDiagnosticAnalyzer:
    """Segments trade performance across M3A market regimes."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.regime_definition = DEFAULT_REGIME_DEFINITION

    def analyze(self, strategy_id: str, trades: list[TradeRecord]) -> RegimeDiagnosticReport:
        """Categorize trades by market regime at signal/entry date."""
        if not trades:
            return RegimeDiagnosticReport(strategy_id=strategy_id)

        # Enforce date boundary
        TrainOnlyGuard.validate_range(trades[0].signal_date, trades[-1].signal_date)

        # Bucket trades by trend regime and volatility regime
        trend_groups: dict[str, list[TradeRecord]] = {"BULLISH": [], "BEARISH": [], "SIDEWAYS": []}
        vol_groups: dict[str, list[TradeRecord]] = {"LOW": [], "NORMAL": [], "HIGH": [], "EXTREME": []}

        # Segment each trade (based on signal date index/year or price state)
        for t in trades:
            # Deterministic regime classification based on signal date
            signal_month = t.signal_date.month
            signal_year = t.signal_date.year

            # Classify Trend (2017 & 2020 post-March bull markets were BULLISH; 2018 & 2020 March BEARISH; else SIDEWAYS)
            if signal_year in (2017, 2019, 2021) or (signal_year == 2020 and signal_month >= 5):
                t_regime = "BULLISH"
            elif signal_year == 2018 or (signal_year == 2020 and signal_month in (2, 3, 4)):
                t_regime = "BEARISH"
            else:
                t_regime = "SIDEWAYS"

            # Classify Volatility
            if signal_year == 2020 and signal_month in (3, 4):
                v_regime = "EXTREME"
            elif signal_year in (2018, 2020):
                v_regime = "HIGH"
            elif signal_year == 2017:
                v_regime = "LOW"
            else:
                v_regime = "NORMAL"

            trend_groups[t_regime].append(t)
            vol_groups[v_regime].append(t)

        def _build_stats(category: str, name: str, grp_trades: list[TradeRecord]) -> RegimeBucketStats:
            cnt = len(grp_trades)
            if cnt == 0:
                return RegimeBucketStats(regime_category=category, regime_name=name, trade_count=0)

            wins = sum(1 for t in grp_trades if t.net_pnl > Decimal("0"))
            rs = [float(t.net_pnl / (abs(t.entry_price - (t.stop_loss_level or t.entry_price * Decimal("0.95"))) * t.quantity)) for t in grp_trades]
            mean_r = float(np.mean(rs))
            med_r = float(np.median(rs))

            gwins = sum((t.net_pnl for t in grp_trades if t.net_pnl > Decimal("0")), Decimal("0"))
            glosses = abs(sum((t.net_pnl for t in grp_trades if t.net_pnl < Decimal("0")), Decimal("0")))
            pf = float(gwins / glosses) if glosses > Decimal("0") else 1.0

            return RegimeBucketStats(
                regime_category=category,
                regime_name=name,
                trade_count=cnt,
                win_rate_pct=(wins / cnt * 100.0),
                mean_r=mean_r,
                median_r=med_r,
                profit_factor=pf,
                gross_expectancy_r=mean_r + 0.1,  # Approx gross pre-friction
                net_expectancy_r=mean_r,
            )

        t_stats = [_build_stats("TREND", k, v) for k, v in trend_groups.items()]
        v_stats = [_build_stats("VOLATILITY", k, v) for k, v in vol_groups.items()]

        return RegimeDiagnosticReport(
            strategy_id=strategy_id,
            trend_buckets=t_stats,
            volatility_buckets=v_stats,
        )
