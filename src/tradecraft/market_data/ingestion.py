import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from tradecraft.core.db_models import CorporateAction, Instrument, MarketBar
from tradecraft.core.exceptions import ProviderError
from tradecraft.instruments import get_current_nifty50_constituents
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.market_data.provider import (
    CorporateActionsProvider,
    MarketDataProvider,
    ZerodhaMarketDataProvider,
)
from tradecraft.market_data.quality_engine import DataQualityEngine

logger = logging.getLogger(__name__)


class DataIngestionWorkflow:
    """Orchestrates instruments and market data ingestion."""

    def __init__(
        self,
        db_session: Session,
        calendar: TradingCalendar,
        market_provider: MarketDataProvider,
        corporate_provider: CorporateActionsProvider,
    ):
        self.db = db_session
        self.calendar = calendar
        self.market_provider = market_provider
        self.corporate_provider = corporate_provider
        self.quality_engine = DataQualityEngine(calendar)

    def run_update(self, force_refresh_instruments: bool = False) -> dict[str, Any]:
        """Perform EOD data updates for Nifty 50 constituents."""
        logger.info("Starting market data update workflow...")

        # 1. Sync instruments list
        self._sync_instruments(force_refresh=force_refresh_instruments)

        # 2. Get active instruments
        stmt = select(Instrument).where(Instrument.is_active == True)
        instruments = self.db.scalars(stmt).all()

        report: dict[str, Any] = {
            "latest_session": None,
            "total_instruments": len(instruments),
            "updated": 0,
            "failed": 0,
            "bars_inserted": 0,
            "bars_unchanged": 0,
            "corporate_actions_found": 0,
            "alerts": [],
            "status": "READY",
        }

        # Determine expected latest completed session
        today = date.today()
        latest_session = today
        if not self.calendar.is_trading_day(latest_session):
            latest_session = self.calendar.previous_trading_day(latest_session)
        report["latest_session"] = latest_session.isoformat()

        # Ingest daily bars for each active instrument
        for inst in instruments:
            try:
                # Determine incremental start date
                last_bar_stmt = (
                    select(MarketBar)
                    .where(and_(MarketBar.instrument_id == inst.id, MarketBar.is_adjusted == False))
                    .order_by(MarketBar.trading_date.desc())
                    .limit(1)
                )
                last_bar = self.db.scalars(last_bar_stmt).first()

                if last_bar:
                    start_date = last_bar.trading_date + timedelta(days=1)
                else:
                    # Ingest starting from 60 days ago by default to save API limits and time
                    start_date = latest_session - timedelta(days=60)

                end_date = latest_session

                if start_date > end_date:
                    logger.info(f"Instrument {inst.symbol} is already up to date.")
                    report["updated"] += 1
                    continue

                # Ingest bars
                # Fallback check if it's ZerodhaMarketDataProvider
                if isinstance(self.market_provider, ZerodhaMarketDataProvider):
                    if inst.instrument_token is None:
                        raise ProviderError(f"Missing instrument token for {inst.symbol}")
                    new_bars = self.market_provider.get_daily_bars_by_token(
                        inst.instrument_token, start_date, end_date
                    )
                else:
                    new_bars = self.market_provider.get_daily_bars(
                        inst.symbol, inst.exchange, start_date, end_date
                    )

                # Ingest corporate actions
                new_actions = self.corporate_provider.get_corporate_actions(
                    inst.symbol, start_date, end_date
                )

                # Run quality validation on new bars
                # Merge with previous 10 bars for context (stale or extreme returns check)
                history_stmt = (
                    select(MarketBar)
                    .where(and_(MarketBar.instrument_id == inst.id, MarketBar.is_adjusted == False))
                    .order_by(MarketBar.trading_date.desc())
                    .limit(10)
                )
                history_bars = self.db.scalars(history_stmt).all()
                history_dicts = [
                    {
                        "trading_date": hb.trading_date,
                        "open": hb.open,
                        "high": hb.high,
                        "low": hb.low,
                        "close": hb.close,
                        "volume": hb.volume,
                    }
                    for hb in reversed(history_bars)
                ]

                validation_set = history_dicts + new_bars
                inst_alerts = self.quality_engine.validate_bars(inst.symbol, validation_set)

                # Filter alerts to only report those relevant to the new bars or overall state
                for alert in inst_alerts:
                    if alert["level"] in ("ERROR", "CRITICAL"):
                        report["status"] = "INVALID"
                    report["alerts"].append({"symbol": inst.symbol, **alert})

                # Persist new bars
                for bar_data in new_bars:
                    bar = MarketBar(
                        instrument_id=inst.id,
                        trading_date=bar_data["trading_date"],
                        open=bar_data["open"],
                        high=bar_data["high"],
                        low=bar_data["low"],
                        close=bar_data["close"],
                        volume=bar_data["volume"],
                        source=bar_data["source"],
                        retrieved_at=bar_data["retrieved_at"],
                        is_adjusted=False,
                        adjustment_factor=Decimal("1.000000"),
                    )
                    self.db.add(bar)
                    report["bars_inserted"] += 1

                # Persist corporate actions
                for act_data in new_actions:
                    # Check duplicate action
                    existing_act_stmt = select(CorporateAction).where(
                        and_(
                            CorporateAction.instrument_id == inst.id,
                            CorporateAction.action_type == act_data["action_type"],
                            CorporateAction.ex_date == act_data["ex_date"],
                        )
                    )
                    existing_act = self.db.scalars(existing_act_stmt).first()
                    if not existing_act:
                        act = CorporateAction(
                            instrument_id=inst.id,
                            action_type=act_data["action_type"],
                            ex_date=act_data["ex_date"],
                            record_date=act_data.get("record_date"),
                            ratio_from=act_data.get("ratio_from"),
                            ratio_to=act_data.get("ratio_to"),
                            amount=act_data.get("amount"),
                            source=act_data["source"],
                            verified=act_data.get("verified", False),
                        )
                        self.db.add(act)
                        report["corporate_actions_found"] += 1

                self.db.commit()
                report["updated"] += 1

            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to ingest data for {inst.symbol}: {e}")
                report["failed"] += 1
                report["alerts"].append(
                    {
                        "symbol": inst.symbol,
                        "level": "CRITICAL",
                        "category": "instrument_mapping",
                        "message": f"Ingestion failed: {e}",
                        "trading_date": None,
                    }
                )
                report["status"] = "INCOMPLETE"

        # Check if the latest session is completely missing for all active instruments
        if report["bars_inserted"] == 0 and report["updated"] > 0:
            # Check if we are stale
            report["status"] = "STALE"

        return report

    def _sync_instruments(self, force_refresh: bool = False) -> None:
        """Ensure instruments master reflects Nifty 50 constituents."""
        logger.info("Syncing instruments master with Nifty 50 constituents...")

        # Load from static nifty50 list
        constituents = get_current_nifty50_constituents()

        # If we are using Zerodha, we can fetch official metadata from the provider
        provider_instruments: dict[str, dict[str, Any]] = {}
        if force_refresh or not self._has_tokens_mapped():
            try:
                raw_instruments = self.market_provider.fetch_all_instruments()
                for raw_inst in raw_instruments:
                    if raw_inst["exchange"] == "NSE":
                        provider_instruments[raw_inst["symbol"]] = raw_inst
            except Exception as e:
                logger.warning(f"Could not fetch instrument master details from provider: {e}")

        for const in constituents:
            stmt = select(Instrument).where(
                and_(Instrument.exchange == const["exchange"], Instrument.symbol == const["symbol"])
            )
            inst = self.db.scalars(stmt).first()

            # Map details from provider if available
            prov_details = provider_instruments.get(const["symbol"])

            if not inst:
                inst = Instrument(
                    symbol=const["symbol"],
                    exchange=const["exchange"],
                    name=prov_details["name"] if prov_details else const["name"],
                    isin=prov_details["isin"] if prov_details else const["isin"],
                    segment=prov_details["segment"] if prov_details else const["segment"],
                    tick_size=prov_details["tick_size"] if prov_details else Decimal("0.05"),
                    lot_size=prov_details["lot_size"] if prov_details else 1,
                    instrument_token=prov_details["instrument_token"] if prov_details else None,
                    is_active=True,
                    nifty50_member_from=const["nifty50_member_from"],
                    nifty50_member_to=const["nifty50_member_to"],
                )
                self.db.add(inst)
            else:
                # Update attributes if needed
                if prov_details:
                    inst.name = prov_details["name"]
                    inst.isin = prov_details["isin"]
                    inst.segment = prov_details["segment"]
                    inst.tick_size = prov_details["tick_size"]
                    inst.lot_size = prov_details["lot_size"]
                    inst.instrument_token = prov_details["instrument_token"]
                inst.is_active = True

        self.db.commit()

    def _has_tokens_mapped(self) -> bool:
        """Check if we already have instrument tokens mapped for Nifty 50."""
        stmt = select(Instrument).where(
            and_(Instrument.exchange == "NSE", Instrument.instrument_token != None)
        )
        mapped = self.db.scalars(stmt).first()
        return mapped is not None
