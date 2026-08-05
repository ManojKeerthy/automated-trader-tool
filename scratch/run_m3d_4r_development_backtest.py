"""Authoritative Master Runner for Milestone M3D.4R — First Execution-Derived DEVELOPMENT Backtest.

Executes EarningsDriftV1Strategy through BacktestEngine.run(config) against historical market_bars database rows
on the DEVELOPMENT dataset (2016-08-01 through 2021-12-31).
"""

import hashlib
import json
import logging
import platform
import sqlite3
import time
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
from tradecraft.research.authenticity_verifier import AuthenticityVerifier
from tradecraft.research.firewall import GLOBAL_FIREWALL, DataBoundaryViolationError
from tradecraft.research.splits import DEVELOPMENT_SPLIT, VALIDATION_SPLIT
from tradecraft.sdk import ResearchClient
from tradecraft.strategy.earnings_drift_v1 import EarningsDriftV1Strategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3d_4r_development_backtest")


def compute_file_sha256(filepath: Path) -> str:
    if not filepath.exists():
        raise FileNotFoundError(f"Required artifact missing: {filepath}")
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def run_m3d_4r_development_backtest() -> Dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    t_start = time.perf_counter()
    logger.info("=== M3D.4R AUTHORITATIVE EXECUTION-DERIVED DEVELOPMENT BACKTEST ===")

    # 1. Firewall Verification
    try:
        GLOBAL_FIREWALL.validate_date(VALIDATION_SPLIT.start_date)
        raise RuntimeError("FIREWALL DEFECT: Validation date access was NOT blocked!")
    except DataBoundaryViolationError as e:
        logger.info(f"FIREWALL GUARD VERIFIED: Blocked Validation date query ({e})")

    # 2. Pre-Execution Fingerprint Verification
    db_path = Path("data/tradecraft.db")
    expected_fingerprints = {
        "database_sha256": ("data/tradecraft.db", "6d336dcdf1e1a0454ca53a56861ada387f24e70c9aa476b74081c8014c81f28f"),
        "strategy_sha256": ("src/tradecraft/strategy/earnings_drift_v1.py", "c3f19080926cf203ea7e82ab254215a30190d9b86efee2b0db41b4cd277d3521"),
        "engine_sha256": ("src/tradecraft/backtesting/engine.py", "d098affd9b5fb98a5274659688fdd62ef42e96404282606db43c7de06dcd551c"),
        "cost_model_sha256": ("src/tradecraft/backtesting/costs.py", "bc133d17c1571545850caa3a4c5ab5c210d8493e92bc1fca570f5c3fa2c41002"),
        "slippage_model_sha256": ("src/tradecraft/backtesting/slippage.py", "f282ad43e6274409459d4176ed2b37545a026cfd213d5deb4971bfa9c2928a9b"),
        "feature_store_sha256": ("src/tradecraft/research/feature_store.py", "b5fcb96a8e1df5cccce25fdbf986322ae17894e5058859b6e255953bb777c375"),
        "universe_registry_sha256": ("src/tradecraft/universe/universe_registry.py", "c5e2d78f094b4672f1d873f2ccc3a24987fe82b1699d9aaf2252d92cff25ac91"),
    }

    observed_fingerprints = {}
    for fp_key, (rel_path, expected_sha) in expected_fingerprints.items():
        actual_sha = compute_file_sha256(Path(rel_path))
        observed_fingerprints[fp_key] = actual_sha
        if actual_sha != expected_sha:
            raise RuntimeError(f"PREFLIGHT FINGERPRINT MISMATCH: {fp_key} expected {expected_sha}, got {actual_sha}!")
        logger.info(f"VERIFIED FINGERPRINT [{fp_key}]: {actual_sha[:16]}... MATCHES.")

    # 3. Database Connection & Production Engine Setup
    engine_db = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine_db)
    SessionLocal = sessionmaker(bind=engine_db)
    db_session = SessionLocal()
    calendar = TradingCalendar()

    client = ResearchClient()
    strategy = EarningsDriftV1Strategy(research_client=client)

    config = BacktestConfig(
        strategy=strategy,
        universe_name="NIFTY_50",
        start_date=DEVELOPMENT_SPLIT.start_date,
        end_date=DEVELOPMENT_SPLIT.end_date,
        initial_capital=Decimal("1000000.00"),
        cost_model=IndianEquityDeliveryCostModel(),
        slippage_model=FixedBasisPointSlippage(bps=5),
        end_of_backtest_policy=EndOfBacktestPolicy.FORCE_CLOSE,
    )

    # 4. Execute Production Backtest Engine
    logger.info("Executing BacktestEngine.run(config) against historical market_bars database...")
    engine = BacktestEngine(db_session=db_session, calendar_instance=calendar)
    result = engine.run(config)

    t_end = time.perf_counter()
    duration_sec = round(t_end - t_start, 2)
    end_time = datetime.now(timezone.utc)

    # 5. Derive All Metrics Exclusively from BacktestResult
    trades = result.trades
    total_trades_count = len(trades)
    winning_trades = [t for t in trades if (t.net_pnl or Decimal("0")) > Decimal("0")]
    losing_trades = [t for t in trades if (t.net_pnl or Decimal("0")) <= Decimal("0")]

    winning_count = len(winning_trades)
    losing_count = len(losing_trades)
    win_rate_pct = round((winning_count / total_trades_count * 100.0), 2) if total_trades_count > 0 else 0.0

    gross_profit_sum = sum((t.net_pnl for t in winning_trades), Decimal("0"))
    gross_loss_sum = abs(sum((t.net_pnl for t in losing_trades), Decimal("0")))
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

    # Holding period statistics
    holding_days_list = [t.holding_days for t in trades if t.holding_days is not None]
    avg_holding_days = round(sum(holding_days_list) / len(holding_days_list), 1) if holding_days_list else 0.0

    # Equity Curve & Double-Entry Cash Accounting
    equity_snapshots = result.equity_curve
    final_equity_val = equity_snapshots[-1].total_equity
    equity_diff = final_equity_val - config.initial_capital
    residual_error_val = float(abs(equity_diff - net_pnl_realized))

    # Extract metrics safely from BacktestResult
    metrics_map = result.metrics.metrics
    def get_val(k: str, default: float = 0.0) -> float:
        m = metrics_map.get(k)
        if m and m.value is not None:
            return round(float(m.value), 2)
        return default

    max_drawdown_val = get_val("max_drawdown_pct")
    sharpe_val = get_val("sharpe_ratio")
    sortino_val = get_val("sortino_ratio")
    calmar_val = get_val("calmar_ratio")
    cagr_val = get_val("cagr_pct")

    # Evaluate Survivor Gate
    gate_evaluations = {
        "expectancy_r": {"threshold": ">= +0.25R", "actual": expectancy_r_val, "passed": expectancy_r_val >= 0.25},
        "profit_factor": {"threshold": ">= 1.30", "actual": profit_factor_ratio, "passed": profit_factor_ratio >= 1.30},
        "max_drawdown_pct": {"threshold": "<= 25.0%", "actual": max_drawdown_val, "passed": max_drawdown_val <= 25.0},
        "total_trades": {"threshold": ">= 30", "actual": total_trades_count, "passed": total_trades_count >= 30},
        "residual_error_inr": {"threshold": "= 0.0000 INR", "actual": residual_error_val, "passed": residual_error_val == 0.0},
    }

    all_gates_passed = all(g["passed"] for g in gate_evaluations.values())
    verdict = "DEVELOPMENT_SURVIVOR" if all_gates_passed else "ABANDON_FAMILY"

    # Export Artifacts
    scratch_dir = Path("scratch")
    scratch_dir.mkdir(parents=True, exist_ok=True)

    # Trade Ledger Export
    trade_ledger_export = []
    for idx, t in enumerate(trades, 1):
        trade_ledger_export.append({
            "trade_id": idx,
            "instrument_symbol": t.instrument_symbol,
            "direction": t.direction,
            "signal_date": t.signal_date.isoformat(),
            "entry_date": t.entry_date.isoformat() if t.entry_date else None,
            "exit_date": t.exit_date.isoformat() if t.exit_date else None,
            "quantity": t.quantity,
            "entry_price": float(t.entry_price) if t.entry_price else 0.0,
            "exit_price": float(t.exit_price) if t.exit_price else 0.0,
            "gross_pnl_inr": float(t.gross_pnl) if t.gross_pnl else 0.0,
            "total_fees_inr": float(t.total_fees) if t.total_fees else 0.0,
            "slippage_cost_inr": float(t.slippage_cost) if t.slippage_cost else 0.0,
            "net_pnl_inr": float(t.net_pnl) if t.net_pnl else 0.0,
            "holding_days": t.holding_days,
            "exit_reason": t.exit_reason,
        })

    # Equity Curve Export
    equity_curve_export = [
        {
            "date": eq.trading_date.isoformat(),
            "total_equity_inr": float(eq.total_equity),
            "cash_balance_inr": float(eq.cash),
            "invested_inr": float(eq.invested),
            "drawdown_pct": float(eq.drawdown_pct),
        }
        for eq in equity_snapshots
    ]

    # Cash Ledger Export
    cash_ledger_export = {
        "starting_capital_inr": float(config.initial_capital),
        "gross_profit_inr": float(gross_profit_sum),
        "gross_loss_inr": float(gross_loss_sum),
        "net_realized_pnl_inr": float(net_pnl_realized),
        "ending_cash_balance_inr": float(final_equity_val),
        "residual_error_inr": residual_error_val,
        "reconciliation_status": "VERIFIED_EXACT_0.0000_RESIDUAL" if residual_error_val == 0.0 else "UNRECONCILED",
    }

    # Results Payload
    results_payload = {
        "milestone": "M3D.4R",
        "status": "AUTHORITATIVE_DEVELOPMENT_BACKTEST_COMPLETED",
        "execution_source": "EXECUTION_DERIVED_FROM_BACKTEST_ENGINE",
        "verdict": verdict,
        "hypothesis_uuid": strategy.hypothesis_uuid,
        "strategy_id": strategy.strategy_id,
        "version": strategy.version,
        "development_period": f"{config.start_date} to {config.end_date}",
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
            "max_drawdown_pct": max_drawdown_val,
            "sharpe_ratio": sharpe_val,
            "sortino_ratio": sortino_val,
            "calmar_ratio": calmar_val,
            "cagr_pct": cagr_val,
            "avg_holding_days": avg_holding_days,
        },
        "gate_evaluations": gate_evaluations,
        "reproducibility": {
            "database_sha256": observed_fingerprints["database_sha256"],
            "strategy_sha256": observed_fingerprints["strategy_sha256"],
            "engine_sha256": observed_fingerprints["engine_sha256"],
            "python_version": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version,
            "operating_system": f"{platform.system()}-{platform.release()}",
            "execution_start_timestamp": start_time.isoformat(),
            "execution_end_timestamp": end_time.isoformat(),
            "duration_seconds": duration_sec,
        },
    }

    # Write files
    with open(scratch_dir / "m3d_4r_trade_ledger.json", "w", encoding="utf-8") as f:
        json.dump(trade_ledger_export, f, indent=2)

    with open(scratch_dir / "m3d_4r_equity_curve.json", "w", encoding="utf-8") as f:
        json.dump(equity_curve_export, f, indent=2)

    with open(scratch_dir / "m3d_4r_cash_ledger.json", "w", encoding="utf-8") as f:
        json.dump(cash_ledger_export, f, indent=2)

    with open(scratch_dir / "m3d_4r_results.json", "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    with open(scratch_dir / "m3d_4r_reproducibility_manifest.json", "w", encoding="utf-8") as f:
        json.dump(results_payload["reproducibility"], f, indent=2)

    # 6. Authenticity Certificate Verification
    verifier = AuthenticityVerifier()
    audit_res = verifier.verify_script(Path("scratch/run_m3d_4r_development_backtest.py"))
    cert_payload = {
        "milestone": "M3D.4R",
        "script": "scratch/run_m3d_4r_development_backtest.py",
        "is_authentic": audit_res.is_authentic,
        "data_source_verified": audit_res.data_source_verified,
        "engine_execution_verified": audit_res.engine_execution_verified,
        "trade_ledger_verified": audit_res.trade_ledger_verified,
        "metric_computation_verified": audit_res.metric_computation_verified,
        "prohibited_patterns_detected": audit_res.prohibited_patterns_detected,
        "certificate_issued_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(scratch_dir / "m3d_4r_authenticity_certificate.json", "w", encoding="utf-8") as f:
        json.dump(cert_payload, f, indent=2)

    db_session.close()
    logger.info(f"=== M3D.4R BACKTEST COMPLETED SUCCESSFULLY: VERDICT = {verdict} ===")
    return results_payload


if __name__ == "__main__":
    run_m3d_4r_development_backtest()
