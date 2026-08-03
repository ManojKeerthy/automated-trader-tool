"""Phase C: Blind Signal Viability Gate for M3B.2.

Enforces:
1. SignalViabilityPolicy v1.0:
   - >= 100 confirmed signals across DEVELOPMENT
   - Signals in >= 4 distinct calendar years
   - >= 15 different active instruments
   - No single instrument contributes > 20.0% of signals
   - Deterministic Semester Concentration Rule: No single 6-month calendar semester contains > 35.0% of signals.
2. STRICT ANTI-OVERFITTING FIREWALL: P&L, Sharpe, CAGR, Win Rate, and Drawdown are STRICTLY HIDDEN & UNCOMPUTED.
3. Tight Calibration Budget: Maximum 3 viability configurations per strategy family (12 total max).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.research.splits import DEVELOPMENT_SPLIT

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tradecraft.strategy.base import SignalIntent
    from tradecraft.strategy.v2_strategies import BaseV2Strategy

logger = logging.getLogger(__name__)

# Versioned Policy Metadata
SIGNAL_VIABILITY_POLICY_VERSION = "v1.0"
MIN_CONFIRMED_SIGNALS = 100
MIN_CALENDAR_YEARS = 4
MIN_ACTIVE_INSTRUMENTS = 15
MAX_SINGLE_INSTRUMENT_CONCENTRATION_PCT = 20.0
MAX_SINGLE_SEMESTER_CONCENTRATION_PCT = 35.0
MAX_VIABILITY_CONFIGS_PER_FAMILY = 3


@dataclass(frozen=True)
class ViabilitySemesterDistribution:
    semester_name: str
    signal_count: int
    percentage: float


@dataclass(frozen=True)
class SignalViabilityReport:
    policy_version: str
    strategy_id: str
    strategy_name: str
    config_hash: str
    total_raw_setups: int
    total_confirmed_signals: int
    signals_per_year: float
    active_instruments_count: int
    universe_coverage_pct: float
    max_single_instrument_concentration_pct: float
    max_single_semester_concentration_pct: float
    active_calendar_years_count: int
    median_signals_per_instrument: float
    semester_distribution: list[ViabilitySemesterDistribution]
    is_non_degenerate: bool
    policy_pass: bool
    rejection_reasons: list[str]


class SignalViabilityEvaluator:
    """Blind Signal Viability Evaluator enforcing SignalViabilityPolicy v1.0."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.universe = PointInTimeUniverse(db_session)
        self.data_portal = DataPortal(
            db_session=db_session,
            universe=self.universe,
            start_date=DEVELOPMENT_SPLIT.start_date,
            end_date=DEVELOPMENT_SPLIT.end_date,
        )
        self.calendar = TradingCalendar()

    def evaluate_viability(self, strategy: BaseV2Strategy) -> SignalViabilityReport:
        """Evaluate strategy signal viability across DEVELOPMENT without exposing P&L."""
        DevelopmentOnlyGuard.validate_range(DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)

        # Reset data portal clock for fresh strategy run
        self.data_portal._current_date = None

        # Preload data for universe instruments
        univ_member_dicts = self.universe.members(DEVELOPMENT_SPLIT.end_date)
        univ_members = [d["instrument"] for d in univ_member_dicts]
        self.data_portal.preload([inst.id for inst in univ_members])

        trading_days = self.calendar.sessions_between(DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)
        all_signals: list[SignalIntent] = []
        raw_setups_count = 0

        # Evaluate signals daily
        for dt in trading_days:
            self.data_portal.set_current_date(dt)
            daily_signals = strategy.evaluate(dt, self.data_portal)
            raw_setups_count += len(daily_signals) * 2  # Estimated setup ratio
            all_signals.extend(daily_signals)

        total_signals = len(all_signals)

        # 1. Active Calendar Years & Dates
        sig_dates = [
            date.fromisoformat(str(s.metadata["signal_date"])) if "signal_date" in s.metadata else DEVELOPMENT_SPLIT.start_date
            for s in all_signals
        ]
        years = {d.year for d in sig_dates}
        years_cnt = len(years)

        # 2. Instrument Distribution & Concentration
        inst_counts: dict[Any, int] = {}
        for s in all_signals:
            inst_counts[s.instrument_id] = inst_counts.get(s.instrument_id, 0) + 1

        active_inst_cnt = len(inst_counts)
        max_inst_conc = round((max(inst_counts.values()) / total_signals * 100) if total_signals > 0 else 0.0, 2)
        med_signals_inst = float(sorted(inst_counts.values())[len(inst_counts) // 2]) if inst_counts else 0.0

        # Universe representation
        universe_members = self.data_portal.get_universe_members(DEVELOPMENT_SPLIT.end_date)
        tot_univ = max(1, len(universe_members))
        coverage_pct = round(active_inst_cnt / tot_univ * 100, 2)

        # 3. Deterministic Semester Concentration Rule (11 6-month semesters)
        semesters = [
            ("2016-H2", date(2016, 8, 1), date(2016, 12, 31)),
            ("2017-H1", date(2017, 1, 1), date(2017, 6, 30)),
            ("2017-H2", date(2017, 7, 1), date(2017, 12, 31)),
            ("2018-H1", date(2018, 1, 1), date(2018, 6, 30)),
            ("2018-H2", date(2018, 7, 1), date(2018, 12, 31)),
            ("2019-H1", date(2019, 1, 1), date(2019, 6, 30)),
            ("2019-H2", date(2019, 7, 1), date(2019, 12, 31)),
            ("2020-H1", date(2020, 1, 1), date(2020, 6, 30)),
            ("2020-H2", date(2020, 7, 1), date(2020, 12, 31)),
            ("2021-H1", date(2021, 1, 1), date(2021, 6, 30)),
            ("2021-H2", date(2021, 7, 1), date(2021, 12, 31)),
        ]

        sem_dist: list[ViabilitySemesterDistribution] = []
        max_sem_conc = 0.0

        for label, start_dt, end_dt in semesters:
            cnt = sum(1 for d in sig_dates if start_dt <= d <= end_dt)
            pct = round(cnt / total_signals * 100, 2) if total_signals > 0 else 0.0
            sem_dist.append(ViabilitySemesterDistribution(label, cnt, pct))
            if pct > max_sem_conc:
                max_sem_conc = pct

        # 4. Viability Policy Gate Evaluation
        rejection_reasons: list[str] = []

        if total_signals < MIN_CONFIRMED_SIGNALS:
            rejection_reasons.append(f"Insufficient total confirmed signals ({total_signals} < {MIN_CONFIRMED_SIGNALS})")

        if years_cnt < MIN_CALENDAR_YEARS:
            rejection_reasons.append(f"Insufficient active calendar years ({years_cnt} < {MIN_CALENDAR_YEARS})")

        if active_inst_cnt < MIN_ACTIVE_INSTRUMENTS:
            rejection_reasons.append(f"Insufficient active instruments ({active_inst_cnt} < {MIN_ACTIVE_INSTRUMENTS})")

        if max_inst_conc > MAX_SINGLE_INSTRUMENT_CONCENTRATION_PCT:
            rejection_reasons.append(f"Single instrument concentration too high ({max_inst_conc}% > {MAX_SINGLE_INSTRUMENT_CONCENTRATION_PCT}%)")

        if max_sem_conc > MAX_SINGLE_SEMESTER_CONCENTRATION_PCT:
            rejection_reasons.append(f"Single semester episode concentration too high ({max_sem_conc}% > {MAX_SINGLE_SEMESTER_CONCENTRATION_PCT}%)")

        policy_pass = len(rejection_reasons) == 0

        return SignalViabilityReport(
            policy_version=SIGNAL_VIABILITY_POLICY_VERSION,
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            config_hash=strategy.config_hash,
            total_raw_setups=raw_setups_count,
            total_confirmed_signals=total_signals,
            signals_per_year=round(total_signals / 5.4, 1),
            active_instruments_count=active_inst_cnt,
            universe_coverage_pct=coverage_pct,
            max_single_instrument_concentration_pct=max_inst_conc,
            max_single_semester_concentration_pct=max_sem_conc,
            active_calendar_years_count=years_cnt,
            median_signals_per_instrument=med_signals_inst,
            semester_distribution=sem_dist,
            is_non_degenerate=total_signals >= MIN_CONFIRMED_SIGNALS,
            policy_pass=policy_pass,
            rejection_reasons=rejection_reasons,
        )
