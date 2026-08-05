"""Execution-Derived Master Runner for Milestone M3E — Single Authoritative Validation Backtest.

Executes EarningsDriftV1Strategy through BacktestEngine.run(config) against historical market_bars database rows
on the sealed VALIDATION dataset (2022-01-01 through 2024-06-30).
"""

import hashlib
import json
import logging
import platform

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.engine import BacktestConfig, BacktestEngine, EndOfBacktestPolicy
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.core.db_models import Base
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.splits import VALIDATION_SPLIT
from tradecraft.sdk import ResearchClient
from tradecraft.strategy.earnings_drift_v1 import EarningsDriftV1Strategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3e_validation_backtest")


def compute_file_sha256(filepath: Path) -> str:
    if not filepath.exists():
        raise FileNotFoundError(f"Required artifact file missing for checksum verification: {filepath}")
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def run_m3e_validation_backtest() -> Dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    logger.info("=== M3E EXECUTION-DERIVED SINGLE VALIDATION BACKTEST ===")

    # 1. Pre-Execution Integrity Verification against Validation Manifest
    scratch_dir = Path("scratch")
    manifest_json_path = scratch_dir / "m3e_0_validation_manifest.json"
    if not manifest_json_path.exists():
        raise RuntimeError("CRITICAL FAILURE: Validation Manifest JSON missing! Execution aborted.")

    manifest_data = json.loads(manifest_json_path.read_text(encoding="utf-8"))
    frozen_checksums = manifest_data["frozen_checksums"]

    checksum_targets = {
        "strategy_sha256": Path("src/tradecraft/strategy/earnings_drift_v1.py"),
        "backtest_engine_sha256": Path("src/tradecraft/backtesting/engine.py"),
        "research_sdk_sha256": Path("src/tradecraft/sdk/research_client.py"),
        "feature_store_sha256": Path("src/tradecraft/research/feature_store.py"),
        "security_master_sha256": Path("src/tradecraft/universe/security_master.py"),
    }

    for key, path in checksum_targets.items():
        actual_sha = compute_file_sha256(path)
        expected_sha = frozen_checksums[key]
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"GOVERNANCE LOCK VIOLATION: Checksum mismatch for {key}! "
                f"Expected: {expected_sha}, Actual: {actual_sha}. Execution aborted."
            )
        logger.info(f"VERIFIED CHECKSUM [{key}]: {actual_sha[:16]}... MATCHES MANIFEST.")

    # 2. Database & DataPortal Setup for VALIDATION Split
    engine_db = create_engine("sqlite:///c:/infiligence/automated-trader-tool/data/tradecraft.db")
    Base.metadata.create_all(engine_db)
    SessionLocal = sessionmaker(bind=engine_db)
    db_session = SessionLocal()
    calendar = TradingCalendar()

    client = ResearchClient()
    strategy = EarningsDriftV1Strategy(research_client=client)

    config = BacktestConfig(
        strategy=strategy,
        universe_name="NIFTY_50",
        start_date=VALIDATION_SPLIT.start_date,
        end_date=VALIDATION_SPLIT.end_date,
        initial_capital=Decimal("1000000.00"),
        cost_model=IndianEquityDeliveryCostModel(),
        slippage_model=FixedBasisPointSlippage(bps=5),
        end_of_backtest_policy=EndOfBacktestPolicy.FORCE_CLOSE,
    )

    # 3. Execute Backtest via Production BacktestEngine
    logger.info("Executing BacktestEngine.run(config) on sealed VALIDATION dataset...")
    engine = BacktestEngine(db_session=db_session, calendar_instance=calendar)
    result = engine.run(config)

    # 4. Derive Metrics Exclusively from BacktestResult
    trades = result.trades
    total_trades_count = len(trades)
    winning_trades_list = [t for t in trades if (t.net_pnl or Decimal("0")) > Decimal("0")]
    losing_trades_list = [t for t in trades if (t.net_pnl or Decimal("0")) <= Decimal("0")]

    winning_count = len(winning_trades_list)
    losing_count = len(losing_trades_list)
    win_rate_pct = round((winning_count / total_trades_count * 100.0), 2) if total_trades_count > 0 else 0.0

    gross_profit_sum = sum((t.net_pnl for t in winning_trades_list), Decimal("0"))
    gross_loss_sum = abs(sum((t.net_pnl for t in losing_trades_list), Decimal("0")))
    net_pnl_realized = gross_profit_sum - gross_loss_sum

    profit_factor_ratio = (
        round(float(gross_profit_sum / gross_loss_sum), 2)
        if gross_loss_sum > Decimal("0")
        else 999.99
    )

    avg_win_val = gross_profit_sum / Decimal(str(winning_count)) if winning_count > 0 else Decimal("0")
    avg_loss_val = gross_loss_sum / Decimal(str(losing_count)) if losing_count > 0 else Decimal("1")
    expectancy_r_val = (
        round(float((avg_win_val - avg_loss_val) / avg_loss_val), 2)
        if avg_loss_val > Decimal("0")
        else 0.0
    )

    final_equity_snapshot = result.equity_curve[-1]
    final_equity_val = final_equity_snapshot.total_equity
    equity_diff = final_equity_val - config.initial_capital
    residual_error_val = float(abs(equity_diff - net_pnl_realized))

    # Evaluate Gate
    gate_evaluations = {
        "expectancy_r": {"threshold": ">= +0.20R", "actual": expectancy_r_val, "passed": expectancy_r_val >= 0.20},
        "profit_factor": {"threshold": ">= 1.25", "actual": profit_factor_ratio, "passed": profit_factor_ratio >= 1.25},
        "sharpe_ratio": {"threshold": ">= 1.20", "actual": result.sharpe_ratio, "passed": result.sharpe_ratio >= 1.20},
        "max_drawdown_pct": {"threshold": "<= 20.0%", "actual": result.max_drawdown_pct, "passed": result.max_drawdown_pct <= 20.0},
        "residual_error_inr": {"threshold": "= 0.0000 INR", "actual": residual_error_val, "passed": residual_error_val == 0.0},
        "total_trades": {"threshold": ">= 30", "actual": total_trades_count, "passed": total_trades_count >= 30},
    }

    all_gates_passed = all(g["passed"] for g in gate_evaluations.values())
    verdict = "VALIDATION_SURVIVOR" if all_gates_passed else "FAILED_IN_VALIDATION"

    end_time = datetime.now(timezone.utc)
    duration_sec = round((end_time - start_time).total_seconds(), 2)

    results_data = {
        "execution_source": "EXECUTION_DERIVED_FROM_BACKTEST_ENGINE",
        "milestone": "M3E",
        "status": "VALIDATION_COMPLETED",
        "verdict": verdict,
        "hypothesis_uuid": strategy.hypothesis_uuid,
        "strategy_id": strategy.strategy_id,
        "version": strategy.version,
        "validation_period": f"{config.start_date} to {config.end_date}",
        "policy": "FORCE_CLOSE",
        "performance_metrics": {
            "total_trades": total_trades_count,
            "winning_trades": winning_count,
            "losing_trades": losing_count,
            "win_rate_pct": win_rate_pct,
            "gross_profit_inr": float(gross_profit_sum),
            "gross_loss_inr": float(gross_loss_sum),
            "net_pnl_inr": float(net_pnl_realized),
            "profit_factor": profit_factor_ratio,
            "expectancy_r": expectancy_r_val,
            "max_drawdown_pct": result.max_drawdown_pct,
            "sharpe_ratio": result.sharpe_ratio,
        },
        "accounting_reconciliation": {
            "starting_cash_inr": float(config.initial_capital),
            "ending_cash_inr": float(final_equity_val),
            "realized_pnl_inr": float(net_pnl_realized),
            "residual_error_inr": residual_error_val,
            "reconciliation_status": "VERIFIED_EXACT_0.0000_RESIDUAL" if residual_error_val == 0.0 else "UNRECONCILED",
        },
        "gate_evaluations": gate_evaluations,
    }

    cert_data = {
        "execution_source": "EXECUTION_DERIVED_FROM_BACKTEST_ENGINE",
        "validation_verdict": verdict,
        "manifest_sha256": compute_file_sha256(manifest_json_path),
        "strategy_sha256": frozen_checksums["strategy_sha256"],
        "dataset_version": "NSE_EQUITY_DAILY_V1",
        "python_version": platform.python_version(),
        "operating_system": f"{platform.system()}-{platform.release()}",
        "execution_start_timestamp": start_time.isoformat(),
        "execution_end_timestamp": end_time.isoformat(),
        "execution_duration_seconds": duration_sec,
    }

    with open(scratch_dir / "m3e_validation_results.json", "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    with open(scratch_dir / "m3e_validation_certificate.json", "w", encoding="utf-8") as f:
        json.dump(cert_data, f, indent=2)

    db_session.close()
    logger.info("=== M3E EXECUTION-DERIVED VALIDATION BACKTEST COMPLETED ===")
    return results_data


if __name__ == "__main__":
    run_m3e_validation_backtest()
