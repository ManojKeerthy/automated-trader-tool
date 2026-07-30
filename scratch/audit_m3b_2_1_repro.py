"""M3B.2.1 Step 1: Hash Verification & Phase D Baseline Reproduction."""

import logging
import sys
from decimal import Decimal

from tradecraft.core.db import SessionLocal
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.research.splits import DEVELOPMENT_SPLIT
from tradecraft.strategy.v2_strategies import (
    TrendPullbackV2Strategy,
    BreakoutConfirmV2Strategy,
    MomentumRSV2Strategy,
    MeanReversionV2Strategy,
)
from tradecraft.backtesting.engine import BacktestEngine, BacktestConfig
from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.market_data.calendar import TradingCalendar

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3b_2_1_repro")


EXPECTED_HASHES = {
    "strat_trend_pullback_v2": "5fe9bb5d935533952ac5d6573fccbb696d12471ccc5e2b925e24c5c802690523",
    "strat_breakout_confirm_v2": "f482e1baa26bdc15e7b589ff3baa06550a314f911db667062f553c029c4da213",
    "strat_momentum_rs_v2": "8e3c4586fb115e38138f9109b815568d2a2b02fdaafcecf1236b26a8f7c33e2d",
    "strat_mean_reversion_v2": "8bf0965a6c0ed6a234424a66b6324bdaaa3e96b10e9873b63e314bf4bd553b82",
}


def main() -> None:
    logger.info("=== M3B.2.1 HASH VERIFICATION & BASELINE REPRODUCTION ===")

    # 1. Dataset Firewall Guard
    DevelopmentOnlyGuard.validate_range(DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)
    logger.info(f"Verified DEVELOPMENT range: {DEVELOPMENT_SPLIT.start_date} -> {DEVELOPMENT_SPLIT.end_date}")

    # 2. Hash Matching Verification
    v2_strats = [
        TrendPullbackV2Strategy(),
        BreakoutConfirmV2Strategy(),
        MomentumRSV2Strategy(),
        MeanReversionV2Strategy(),
    ]

    for strat in v2_strats:
        exp_h = EXPECTED_HASHES[strat.strategy_id]
        act_h = strat.config_hash
        if act_h != exp_h:
            logger.error(f"M3B2_CANONICAL_HASH_MISMATCH for {strat.name}: expected {exp_h}, got {act_h}")
            sys.exit(1)
        logger.info(f"HASH MATCH VERIFIED for {strat.name}: {act_h}")

    # 3. Phase D Baseline Reproduction
    logger.info("\n--- REPRODUCING M3B.2 PHASE D BASELINE ---")
    with SessionLocal() as db:
        engine = BacktestEngine(db, TradingCalendar())
        for strat in v2_strats:
            config = BacktestConfig(
                strategy=strat,
                universe_name="NIFTY_50",
                start_date=DEVELOPMENT_SPLIT.start_date,
                end_date=DEVELOPMENT_SPLIT.end_date,
                initial_capital=Decimal("1000000.00"),
                cost_model=IndianEquityDeliveryCostModel(),
                slippage_model=FixedBasisPointSlippage(bps=5),
            )
            res = engine.run(config)
            executed_trades = len(res.trades)
            logger.info(
                f"REPRODUCTION CHECK for {strat.name}: Executed Trades = {executed_trades} "
                f"(Expected = 0)"
            )
            if executed_trades != 0:
                logger.error(f"M3B2_PHASE_D_REPRODUCTION_FAILURE for {strat.name}: got {executed_trades} trades instead of 0!")
                sys.exit(1)

    logger.info("\nSUCCESS: All SHA256 hashes match and Phase-D 0-trade baseline reproduced exactly across all 4 V2 families.")


if __name__ == "__main__":
    main()
