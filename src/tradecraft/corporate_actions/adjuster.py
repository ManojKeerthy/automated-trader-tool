"""Back-adjustment of historical prices for corporate actions.

THE CONVENTION
==============
Raw bars are **immutable**. They are stored with `is_adjusted=False` and are never
rewritten — they are the record of what actually printed on the exchange, and they are what
execution logic must reference when reasoning about real order prices.

Adjusted bars are **derived**. They are written as separate rows with `is_adjusted=True`,
which the `uq_instrument_date_adj` unique constraint already permits, and they are what
research consumes. Regenerating them is always safe: the adjuster deletes and rebuilds the
adjusted series rather than mutating it in place.

This separation matters because the two questions differ. "What would my stop have been hit
at?" is a raw-price question. "What was the return series?" is an adjusted-price question.
Conflating them is how backtests silently diverge from reality.

BACK-ADJUSTMENT DIRECTION
=========================
Standard convention: the most recent price is left untouched and history is scaled, so the
current series matches what a person sees on a chart today.

For an action with price multiplier m effective on ex_date, every bar STRICTLY BEFORE
ex_date is multiplied by m. Multiple actions compound:

    adjusted_price(t) = raw_price(t) * PRODUCT( m_k  for all ex_date_k > t )

Volume moves inversely — a 1:1 bonus halves the price and doubles the share count, so
historical volumes are divided by m to express them in current-share terms. Traded value is
therefore preserved, which is what makes liquidity filters comparable across a split.

ONLY VERIFIED ACTIONS ARE APPLIED
=================================
Actions with `verified=False` (including everything the detector infers) are **skipped by
default**. An inferred action is a lead to check, not a fact. Applying unverified inferences
would replace one silent data corruption with another — and this project has already lost
two research cycles to exactly that class of error.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from fractions import Fraction
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("tradecraft.ca_adjuster")

ADJUSTMENT_VERSION = "1.0.0"
TRANSFORMATION_TAG = f"CA_BACK_ADJUSTED_v{ADJUSTMENT_VERSION}"

# Actions that change the share count and therefore require a price adjustment.
PRICE_AFFECTING = {"SPLIT", "BONUS", "CONSOLIDATION"}


@dataclass
class AdjustmentPlan:
    """What would change for one instrument, before anything is written."""

    symbol: str
    instrument_id: Any
    actions_applied: list[tuple[date, str, float]] = field(default_factory=list)
    bars_affected: int = 0
    total_bars: int = 0
    earliest_factor: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "actions_applied": [
                {"ex_date": d.isoformat(), "type": t, "multiplier": m}
                for d, t, m in self.actions_applied
            ],
            "bars_affected": self.bars_affected,
            "total_bars": self.total_bars,
            "earliest_cumulative_factor": self.earliest_factor,
        }


@dataclass
class AdjustmentReport:
    version: str = ADJUSTMENT_VERSION
    dry_run: bool = True
    include_unverified: bool = False
    plans: list[AdjustmentPlan] = field(default_factory=list)
    rows_written: int = 0
    rows_deleted: int = 0
    skipped_unverified: int = 0

    def render(self) -> str:
        out: list[str] = []
        out.append("=" * 78)
        mode = "DRY RUN — nothing written" if self.dry_run else "APPLIED"
        out.append(f"  CORPORATE ACTION ADJUSTMENT  ({mode})")
        out.append("=" * 78)
        out.append(f"  adjuster version : {self.version}")
        out.append(f"  unverified       : {'INCLUDED' if self.include_unverified else 'skipped'}")
        if self.skipped_unverified:
            out.append(
                f"  {self.skipped_unverified} unverified action(s) skipped. Verify them "
                "against NSE circulars and re-import with verified=true."
            )
        out.append("-" * 78)

        if not self.plans:
            out.append("\n  No price-affecting corporate actions to apply.")
        for p in self.plans:
            out.append(
                f"\n  {p.symbol}  ({p.bars_affected}/{p.total_bars} bars adjusted, "
                f"earliest factor x{p.earliest_factor:.6f})"
            )
            for d, t, m in p.actions_applied:
                out.append(f"      {d}  {t:<14} price x{m:.6f}")

        out.append("\n" + "-" * 78)
        if not self.dry_run:
            out.append(f"  adjusted rows written: {self.rows_written}")
            out.append(f"  stale rows replaced  : {self.rows_deleted}")
            out.append("  Raw bars (is_adjusted=false) were NOT modified.")
        else:
            out.append("  Re-run with --apply to write the adjusted series.")
        out.append("=" * 78)
        return "\n".join(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "dry_run": self.dry_run,
            "include_unverified": self.include_unverified,
            "rows_written": self.rows_written,
            "rows_deleted": self.rows_deleted,
            "skipped_unverified": self.skipped_unverified,
            "plans": [p.to_dict() for p in self.plans],
        }


def multiplier_from_action(
    action_type: str, ratio_from: int | None, ratio_to: int | None
) -> float | None:
    """Derive the price multiplier for a corporate action.

    Interpretation of the stored ratio columns:

      BONUS         ratio_from:ratio_to = a:b, a new shares for every b held
                    -> price multiplier b / (a + b)
      SPLIT         ratio_from -> ratio_to face value
                    -> price multiplier ratio_to / ratio_from
      CONSOLIDATION ratio_from -> ratio_to face value (rising price)
                    -> price multiplier ratio_to / ratio_from
    """
    if ratio_from is None or ratio_to is None or ratio_from <= 0 or ratio_to <= 0:
        return None

    t = action_type.upper()
    if t == "BONUS":
        return float(Fraction(ratio_to, ratio_from + ratio_to))
    if t in ("SPLIT", "CONSOLIDATION"):
        return float(Fraction(ratio_to, ratio_from))
    return None


class CorporateActionAdjuster:
    """Builds the adjusted price series from raw bars plus corporate actions."""

    def __init__(self, include_unverified: bool = False) -> None:
        self.include_unverified = include_unverified

    def _load_actions(self, session: Session) -> dict[Any, list[dict[str, Any]]]:
        rows = session.execute(
            text(
                """
                SELECT ca.instrument_id AS iid, i.symbol AS symbol,
                       ca.action_type AS action_type, ca.ex_date AS ex_date,
                       ca.ratio_from AS ratio_from, ca.ratio_to AS ratio_to,
                       ca.verified AS verified
                FROM corporate_actions ca
                JOIN instruments i ON i.id = ca.instrument_id
                ORDER BY ca.ex_date
                """
            )
        ).mappings()

        out: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            if r["action_type"].upper() not in PRICE_AFFECTING:
                continue
            ed = r["ex_date"]
            if isinstance(ed, str):
                ed = date.fromisoformat(ed[:10])
            out[r["iid"]].append(
                {
                    "symbol": r["symbol"],
                    "action_type": r["action_type"].upper(),
                    "ex_date": ed,
                    "ratio_from": r["ratio_from"],
                    "ratio_to": r["ratio_to"],
                    "verified": bool(r["verified"]),
                }
            )
        return dict(out)

    def run(self, session: Session, dry_run: bool = True) -> AdjustmentReport:
        report = AdjustmentReport(dry_run=dry_run, include_unverified=self.include_unverified)
        actions_by_inst = self._load_actions(session)

        for iid, actions in actions_by_inst.items():
            usable: list[tuple[date, str, float]] = []
            for a in actions:
                if not a["verified"] and not self.include_unverified:
                    report.skipped_unverified += 1
                    continue
                m = multiplier_from_action(a["action_type"], a["ratio_from"], a["ratio_to"])
                if m is None or m <= 0:
                    logger.warning(
                        "%s %s on %s has an uninterpretable ratio (%s:%s); skipped.",
                        a["symbol"], a["action_type"], a["ex_date"],
                        a["ratio_from"], a["ratio_to"],
                    )
                    continue
                usable.append((a["ex_date"], a["action_type"], m))

            if not usable:
                continue
            usable.sort()

            bars = session.execute(
                text(
                    """
                    SELECT trading_date, open, high, low, close, volume, source
                    FROM market_bars
                    WHERE instrument_id = :iid AND is_adjusted = false
                    ORDER BY trading_date
                    """
                ),
                {"iid": iid},
            ).mappings().all()

            if not bars:
                continue

            symbol = actions[0]["symbol"]
            plan = AdjustmentPlan(symbol=symbol, instrument_id=iid, total_bars=len(bars))
            plan.actions_applied = usable

            adjusted_rows: list[dict[str, Any]] = []
            for b in bars:
                td = b["trading_date"]
                if isinstance(td, str):
                    td = date.fromisoformat(td[:10])

                # Compound every action whose ex-date is strictly after this bar.
                factor = 1.0
                for ex_date, _t, m in usable:
                    if ex_date > td:
                        factor *= m

                if abs(factor - 1.0) > 1e-12:
                    plan.bars_affected += 1
                    plan.earliest_factor = min(plan.earliest_factor, factor)

                f = Decimal(str(factor))
                adjusted_rows.append(
                    {
                        "iid": iid,
                        "d": td,
                        "o": Decimal(str(b["open"])) * f,
                        "h": Decimal(str(b["high"])) * f,
                        "l": Decimal(str(b["low"])) * f,
                        "c": Decimal(str(b["close"])) * f,
                        # Inverse on volume so traded value is preserved.
                        "v": int(round(int(b["volume"] or 0) / factor)) if factor > 0 else 0,
                        "src": b["source"],
                        "af": f,
                    }
                )

            report.plans.append(plan)

            if dry_run:
                continue

            deleted = session.execute(
                text(
                    "DELETE FROM market_bars "
                    "WHERE instrument_id = :iid AND is_adjusted = true"
                ),
                {"iid": iid},
            ).rowcount
            report.rows_deleted += deleted or 0

            now = datetime.now(timezone.utc)
            for r in adjusted_rows:
                session.execute(
                    text(
                        """
                        INSERT INTO market_bars
                            (id, instrument_id, trading_date, open, high, low, close,
                             volume, source, retrieved_at, is_adjusted, adjustment_factor,
                             transformation_version)
                        VALUES
                            (gen_random_uuid(), :iid, :d, :o, :h, :l, :c,
                             :v, :src, :ts, true, :af, :tv)
                        """
                    ),
                    {**r, "ts": now, "tv": TRANSFORMATION_TAG},
                )
                report.rows_written += 1

            session.commit()
            logger.info(
                "%s: wrote %d adjusted bars (%d affected by %d action(s))",
                symbol, len(adjusted_rows), plan.bars_affected, len(usable),
            )

        return report
