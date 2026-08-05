"""Execution-Derived Master Runner for Milestone M3D.4 — Single DEVELOPMENT Backtest.

Executes EarningsDriftV1Strategy through BacktestEngine.run(config) against historical market_bars database rows.
"""

import json
import logging
from datetime import date
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
from tradecraft.research.firewall import GLOBAL_FIREWALL, DataBoundaryViolationError
from tradecraft.research.splits import DEVELOPMENT_SPLIT, VALIDATION_SPLIT
from tradecraft.sdk import ResearchClient
from tradecraft.strategy.earnings_drift_v1 import EarningsDriftV1Strategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3d_4_development_backtest")


def run_m3d_4_development_backtest() -> Dict[str, Any]:
    logger.info("=== M3D.4 EXECUTION-DERIVED SINGLE DEVELOPMENT BACKTEST ===")

    # 1. Firewall Verification
    try:
        GLOBAL_FIREWALL.validate_date(VALIDATION_SPLIT.start_date)
        raise RuntimeError("FIREWALL DEFECT: Validation date access was NOT blocked!")
    except DataBoundaryViolationError as e:
        logger.info(f"FIREWALL GUARD VERIFIED: Blocked Validation date query ({e})")

    # 2. Initialize Database Session & Trading Calendar
    engine_db = create_engine("sqlite:///c:/infiligence/automated-trader-tool/data/tradecraft.db")
    Base.metadata.create_all(engine_db)
    SessionLocal = sessionmaker(bind=engine_db)
    db_session = SessionLocal()
    calendar = TradingCalendar()

    # 3. Load Strategy & Configuration
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

    # 4. Execute Backtest via Production BacktestEngine
    logger.info("Executing BacktestEngine.run(config) against historical market_bars database...")
    engine = BacktestEngine(db_session=db_session, calendar_instance=calendar)
    result = engine.run(config)

    # 5. Derive Performance & Accounting Metrics Exclusively from BacktestResult
    trades = result.trades
    total_trades_count = len(trades)
    winning_trades_list = [t for t in trades if (t.net_pnl or Decimal("0")) > Decimal("0")]
    losing_trades_list = [t for t in trades if (t.net_pnl or Decimal("0")) <= Decimal("0")]

    winning_count = len(winning_trades_list)
    losing_count = len(losing_trades_list)
    win_rate_percentage = round((winning_count / total_trades_count * 100.0), 2) if total_trades_count > 0 else 0.0

    gross_profit_sum = sum((t.net_pnl for t in winning_trades_list), Decimal("0"))
    gross_loss_sum = abs(sum((t.net_pnl for t in losing_trades_list), Decimal("0")))
    net_pnl_realized = gross_profit_sum - gross_loss_sum

    if gross_loss_sum > Decimal("0"):
        profit_factor_ratio = round(float(gross_profit_sum / gross_loss_sum), 2)
    else:
        profit_factor_ratio = 999.99

    avg_win_val = gross_profit_sum / Decimal(str(winning_count)) if winning_count > 0 else Decimal("0")
    avg_loss_val = gross_loss_sum / Decimal(str(losing_count)) if losing_count > 0 else Decimal("1")
    expectancy_r_val = round(float((avg_win_val - avg_loss_val) / avg_loss_val), 2) if avg_loss_val > Decimal("0") else 0.0

    final_equity_snapshot = result.equity_curve[-1]
    final_equity_val = final_equity_snapshot.total_equity
    equity_diff = final_equity_val - config.initial_capital
    residual_error_val = float(abs(equity_diff - net_pnl_realized))

    # Evaluate Pre-Declared Survivor Gate
    gate_passed = (
        expectancy_r_val >= 0.25
        and profit_factor_ratio >= 1.30
        and result.max_drawdown_pct <= 25.0
        and total_trades_count >= 30
    )
    verdict = "DEVELOPMENT_SURVIVOR" if gate_passed else "ABANDON_FAMILY"

    results_payload = {
        "execution_source": "EXECUTION_DERIVED_FROM_BACKTEST_ENGINE",
        "hypothesis_uuid": strategy.hypothesis_uuid,
        "strategy_id": strategy.strategy_id,
        "version": strategy.version,
        "development_period": f"{config.start_date} to {config.end_date}",
        "policy": "FORCE_CLOSE",
        "performance_metrics": {
            "total_trades": total_trades_count,
            "winning_trades": winning_count,
            "losing_trades": losing_count,
            "win_rate_pct": win_rate_percentage,
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
        "survivor_gate_evaluation": {
            "verdict": verdict,
            "passed": gate_passed,
        },
    }

    # Save artifact
    scratch_dir = Path("scratch")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    with open(scratch_dir / "m3d_4_development_results.json", "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    db_session.close()
    logger.info("=== M3D.4 EXECUTION-DERIVED BACKTEST COMPLETED ===")
    return results_payload


if __name__ == "__main__":
    run_m3d_4_development_backtest()
