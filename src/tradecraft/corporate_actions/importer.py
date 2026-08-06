"""Import human-verified corporate actions from CSV.

WHY CSV RATHER THAN A SCRAPER
=============================
`NSECorporateActionsProvider.get_corporate_actions()` returns `[]` — the NSE fetch was never
implemented. This module deliberately does NOT invent an endpoint to replace it. The repo's
own agent instructions prohibit inventing API endpoints, and a scraper written against a
guessed URL that silently returns nothing is worse than no scraper at all: it looks like
coverage.

So the authoritative path is explicit. A human reads the exchange record and records it.
That is slow, and it is correct. The detector narrows the work to a handful of specific
dates, so this is minutes of effort rather than an open-ended audit.

Rows imported here default to `verified=true`, because a human asserted them from a primary
source. The detector's output defaults to `verified=false` and is not applied to prices.

FORMAT
======
    symbol,action_type,ex_date,ratio_from,ratio_to,record_date,source,verified

    RELIANCE,BONUS,2017-09-07,1,1,2017-09-08,NSE_CIRCULAR,true
    INFY,BONUS,2018-09-11,1,1,,NSE_CIRCULAR,true
    HDFCBANK,SPLIT,2019-09-19,10,2,,NSE_CIRCULAR,true

Ratio semantics (must match `adjuster.multiplier_from_action`):
    BONUS          ratio_from:ratio_to = a:b, a new shares per b held  -> price x b/(a+b)
    SPLIT          face value ratio_from -> ratio_to                   -> price x to/from
    CONSOLIDATION  face value ratio_from -> ratio_to                   -> price x to/from
    DIVIDEND       ratio columns unused; put the amount in `amount`
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from tradecraft.corporate_actions.adjuster import PRICE_AFFECTING, multiplier_from_action

logger = logging.getLogger("tradecraft.ca_importer")

REQUIRED_COLUMNS = {"symbol", "action_type", "ex_date"}
VALID_ACTIONS = PRICE_AFFECTING | {"DIVIDEND"}


@dataclass
class ImportResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    unknown_symbols: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        out = ["=" * 70, "  CORPORATE ACTION IMPORT", "=" * 70]
        out.append(f"  inserted : {self.inserted}")
        out.append(f"  updated  : {self.updated}")
        out.append(f"  skipped  : {self.skipped}")
        if self.unknown_symbols:
            out.append(f"\n  unknown symbols (not in instruments table): "
                       f"{', '.join(sorted(set(self.unknown_symbols)))}")
        if self.errors:
            out.append(f"\n  ERRORS ({len(self.errors)}):")
            for e in self.errors[:25]:
                out.append(f"    {e}")
        out.append("=" * 70)
        if self.inserted or self.updated:
            out.append("  Next: python -m tradecraft data corporate-actions apply --dry-run")
        return "\n".join(out)


class CorporateActionImporter:
    """Loads verified corporate actions from a CSV into the database."""

    def _symbol_map(self, session: Session) -> dict[str, Any]:
        rows = session.execute(text("SELECT symbol, id FROM instruments")).all()
        return {r[0].upper(): r[1] for r in rows}

    def load(self, session: Session, csv_path: str | Path) -> ImportResult:
        res = ImportResult()
        path = Path(csv_path)
        if not path.exists():
            res.errors.append(f"File not found: {path}")
            return res

        symbols = self._symbol_map(session)

        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            missing = REQUIRED_COLUMNS - {c.strip().lower() for c in (reader.fieldnames or [])}
            if missing:
                res.errors.append(f"CSV missing required column(s): {sorted(missing)}")
                return res

            for lineno, raw in enumerate(reader, start=2):
                row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
                try:
                    parsed = self._parse(row, lineno, symbols, res)
                except ValueError as e:
                    res.errors.append(f"line {lineno}: {e}")
                    continue
                if parsed is None:
                    continue
                self._upsert(session, parsed, res)

        if res.ok:
            session.commit()
        else:
            session.rollback()
        return res

    def _parse(
        self, row: dict[str, str], lineno: int, symbols: dict[str, Any], res: ImportResult
    ) -> dict[str, Any] | None:
        symbol = row.get("symbol", "").upper()
        if not symbol:
            raise ValueError("symbol is empty")

        iid = symbols.get(symbol)
        if iid is None:
            res.unknown_symbols.append(symbol)
            res.skipped += 1
            return None

        action_type = row.get("action_type", "").upper()
        if action_type not in VALID_ACTIONS:
            raise ValueError(
                f"action_type '{action_type}' invalid; expected one of {sorted(VALID_ACTIONS)}"
            )

        try:
            ex_date = date.fromisoformat(row["ex_date"])
        except Exception:
            raise ValueError(f"ex_date '{row.get('ex_date')}' is not ISO format (YYYY-MM-DD)")

        record_date = None
        if row.get("record_date"):
            try:
                record_date = date.fromisoformat(row["record_date"])
            except Exception:
                raise ValueError(f"record_date '{row['record_date']}' is not ISO format")

        def _int(key: str) -> int | None:
            v = row.get(key)
            return int(v) if v else None

        ratio_from, ratio_to = _int("ratio_from"), _int("ratio_to")

        if action_type in PRICE_AFFECTING:
            if ratio_from is None or ratio_to is None:
                raise ValueError(f"{action_type} requires ratio_from and ratio_to")
            m = multiplier_from_action(action_type, ratio_from, ratio_to)
            if m is None or m <= 0:
                raise ValueError(
                    f"{action_type} {ratio_from}:{ratio_to} yields no valid price multiplier"
                )
            # Catch inverted entry early — a bonus that raises the price is a typo.
            if action_type == "BONUS" and m >= 1.0:
                raise ValueError(
                    f"BONUS {ratio_from}:{ratio_to} implies price multiplier {m:.4f} >= 1. "
                    "Bonus issues reduce the price; check the ratio order (a:b = a new per b held)."
                )

        amount = Decimal(row["amount"]) if row.get("amount") else None
        verified = row.get("verified", "true").lower() not in ("false", "0", "no", "")

        return {
            "iid": iid,
            "symbol": symbol,
            "action_type": action_type,
            "ex_date": ex_date,
            "record_date": record_date,
            "ratio_from": ratio_from,
            "ratio_to": ratio_to,
            "amount": amount,
            "source": row.get("source") or "MANUAL_VERIFIED",
            "verified": verified,
        }

    def _upsert(self, session: Session, p: dict[str, Any], res: ImportResult) -> None:
        existing = session.execute(
            text(
                """
                SELECT id FROM corporate_actions
                WHERE instrument_id = :iid AND action_type = :at AND ex_date = :ed
                """
            ),
            {"iid": p["iid"], "at": p["action_type"], "ed": p["ex_date"]},
        ).first()

        params = {
            "iid": p["iid"], "at": p["action_type"], "ed": p["ex_date"],
            "rd": p["record_date"], "rf": p["ratio_from"], "rt": p["ratio_to"],
            "amt": p["amount"], "src": p["source"], "ver": p["verified"],
        }

        if existing:
            session.execute(
                text(
                    """
                    UPDATE corporate_actions
                    SET record_date = :rd, ratio_from = :rf, ratio_to = :rt,
                        amount = :amt, source = :src, verified = :ver
                    WHERE id = :id
                    """
                ),
                {**params, "id": existing[0]},
            )
            res.updated += 1
        else:
            session.execute(
                text(
                    """
                    INSERT INTO corporate_actions
                        (id, instrument_id, action_type, ex_date, record_date,
                         ratio_from, ratio_to, amount, source, verified)
                    VALUES
                        (gen_random_uuid(), :iid, :at, :ed, :rd, :rf, :rt, :amt, :src, :ver)
                    """
                ),
                params,
            )
            res.inserted += 1


def write_template(path: str | Path, detected: list[Any] | None = None) -> Path:
    """Write a CSV template, optionally pre-filled with detector candidates.

    Pre-filling turns verification into a checking exercise rather than a transcription
    exercise: the human confirms or corrects each row against the NSE circular instead of
    typing it from scratch. Every pre-filled row is marked `verified=false` — it becomes
    authoritative only when a person changes that to `true`.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["symbol", "action_type", "ex_date", "ratio_from", "ratio_to",
             "record_date", "source", "verified"]
        )
        if detected:
            for a in detected:
                rf = rt = ""
                if a.ratio_label and a.action_type == "BONUS" and ":" in a.ratio_label:
                    rf, rt = a.ratio_label.split(":")
                elif a.ratio_label and "->" in a.ratio_label:
                    rf, rt = a.ratio_label.split("->")
                w.writerow(
                    [a.symbol, a.action_type or "", a.ex_date.isoformat(),
                     rf, rt, "", "PRICE_INFERRED_NEEDS_VERIFICATION", "false"]
                )
        else:
            w.writerow(["RELIANCE", "BONUS", "2017-09-07", "1", "1", "", "NSE_CIRCULAR", "true"])
    return p
