"""Validation Governance Lock Enactor for Milestone M3E.0R.

Freezes all execution-derived artifacts, source file SHA-256 hashes, pre-registered decision gates,
environment metadata, and firewall rules before single-shot VALIDATION execution.
"""

import hashlib
import json
import logging
import platform
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from tradecraft.research.authenticity_verifier import AuthenticityVerifier
from tradecraft.research.firewall import GLOBAL_FIREWALL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3e_0r_validation_lock")


def compute_sha256(filepath: Path) -> str:
    if not filepath.exists():
        raise FileNotFoundError(f"Missing required artifact for freeze: {filepath}")
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def get_git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "GIT_COMMIT_NOT_AVAILABLE"


def run_m3e_0r_validation_lock() -> Dict[str, Any]:
    logger.info("=== M3E.0R VALIDATION GOVERNANCE LOCK (EXECUTION-DERIVED) ===")

    # 1. Verify Firewall State
    val_access_count = GLOBAL_FIREWALL.validation_access_count
    if val_access_count != 0:
        raise RuntimeError(f"GOVERNANCE LOCK FAILURE: VALIDATION_ACCESS_COUNT is {val_access_count}, expected 0!")
    logger.info("FIREWALL LOG CHECK: VALIDATION_ACCESS_COUNT == 0. VERIFIED.")

    # 2. Verify Authenticity Verifier
    verifier = AuthenticityVerifier()
    verifier_result = verifier.verify_script(Path("scratch/run_m3d_4r_development_backtest.py"))
    if not verifier_result.is_authentic:
        raise RuntimeError("GOVERNANCE LOCK FAILURE: AuthenticityVerifier failed on development runner!")
    logger.info("AUTHENTICITY VERIFIER CHECK: PASS. VERIFIED.")

    # 3. Compute SHA-256 Fingerprints for All Production & Research Artifacts
    frozen_artifacts = {
        "database_sha256": ("data/tradecraft.db", compute_sha256(Path("data/tradecraft.db"))),
        "strategy_sha256": ("src/tradecraft/strategy/earnings_drift_v1.py", compute_sha256(Path("src/tradecraft/strategy/earnings_drift_v1.py"))),
        "engine_sha256": ("src/tradecraft/backtesting/engine.py", compute_sha256(Path("src/tradecraft/backtesting/engine.py"))),
        "cost_model_sha256": ("src/tradecraft/backtesting/costs.py", compute_sha256(Path("src/tradecraft/backtesting/costs.py"))),
        "slippage_model_sha256": ("src/tradecraft/backtesting/slippage.py", compute_sha256(Path("src/tradecraft/backtesting/slippage.py"))),
        "dataportal_sha256": ("src/tradecraft/backtesting/data_portal.py", compute_sha256(Path("src/tradecraft/backtesting/data_portal.py"))),
        "feature_store_sha256": ("src/tradecraft/research/feature_store.py", compute_sha256(Path("src/tradecraft/research/feature_store.py"))),
        "security_master_sha256": ("src/tradecraft/core/db_models.py", compute_sha256(Path("src/tradecraft/core/db_models.py"))),
        "universe_registry_sha256": ("src/tradecraft/universe/universe_registry.py", compute_sha256(Path("src/tradecraft/universe/universe_registry.py"))),
        # Development Artifacts
        "m3d_4r_report_sha256": ("docs/research/M3D_4R_DEVELOPMENT_BACKTEST.md", compute_sha256(Path("docs/research/M3D_4R_DEVELOPMENT_BACKTEST.md"))),
        "m3d_4_5r_report_sha256": ("docs/research/M3D_4_5R_FORENSIC_AUDIT.md", compute_sha256(Path("docs/research/M3D_4_5R_FORENSIC_AUDIT.md"))),
        "trade_ledger_sha256": ("scratch/m3d_4r_trade_ledger.json", compute_sha256(Path("scratch/m3d_4r_trade_ledger.json"))),
        "equity_curve_sha256": ("scratch/m3d_4r_equity_curve.json", compute_sha256(Path("scratch/m3d_4r_equity_curve.json"))),
        "cash_ledger_sha256": ("scratch/m3d_4r_cash_ledger.json", compute_sha256(Path("scratch/m3d_4r_cash_ledger.json"))),
        "authenticity_cert_sha256": ("scratch/m3d_4r_authenticity_certificate.json", compute_sha256(Path("scratch/m3d_4r_authenticity_certificate.json"))),
    }

    # 4. Strategy & Experiment Configuration Freeze
    frozen_config = {
        "hypothesis_uuid": "hypo-cycle2-alpha013-v1",
        "strategy_id": "strat_earnings_drift_v1",
        "strategy_version": "1.0.0",
        "parameters": {
            "holding_period_max_sessions": 30,
            "atr_stop_multiplier": "2.0",
            "min_volume_expansion_ratio": "1.5",
            "position_size_pct": "0.10",
        },
        "execution_policy": "FORCE_CLOSE",
        "initial_capital_inr": "1000000.00",
        "cost_model": "IndianEquityDeliveryCostModel",
        "slippage_model": "FixedBasisPointSlippage(5)",
        "universe_name": "NIFTY_50",
    }

    # 5. Pre-Registered Validation Decision Gates
    pre_registered_gates = {
        "profit_factor": {"threshold": ">= 1.30", "is_mandatory": True},
        "expectancy_r": {"threshold": ">= +0.25R", "is_mandatory": True},
        "sharpe_ratio": {"threshold": ">= 0.50", "is_mandatory": True},
        "max_drawdown_pct": {"threshold": "<= 25.0%", "is_mandatory": True},
        "residual_error_inr": {"threshold": "= 0.0000 INR", "is_mandatory": True},
        "minimum_trades": {"threshold": ">= 15", "is_mandatory": True},
    }

    # 6. Environmental Reproducibility Metadata
    requirements_path = Path("requirements.txt")
    req_sha = compute_sha256(requirements_path) if requirements_path.exists() else "NO_REQUIREMENTS_TXT"

    environment_metadata = {
        "python_version": platform.python_version(),
        "operating_system": f"{platform.system()}-{platform.release()}",
        "git_commit": get_git_commit(),
        "sqlite_version": sqlite3.sqlite_version,
        "requirements_sha256": req_sha,
        "timezone": "UTC",
        "random_seed": 42,
        "validation_access_count": val_access_count,
        "lock_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 7. Construct Manifest
    validation_manifest = {
        "manifest_version": "M3E.0R-V1",
        "milestone": "M3E.0R",
        "status": "VALIDATION_GOVERNANCE_LOCK_ENACTED",
        "dataset_split": {
            "validation_period": "2022-01-01 to 2024-06-30",
            "validation_access_count": val_access_count,
            "development_status": "PERMANENTLY_CLOSED",
            "final_test_status": "SEALED",
        },
        "frozen_config": frozen_config,
        "pre_registered_gates": pre_registered_gates,
        "frozen_artifacts": frozen_artifacts,
        "reproducibility": environment_metadata,
        "governance_rules": [
            "1. Exactly ONE out-of-sample backtest execution permitted under M3ER.",
            "2. Runner MUST execute preflight gate verifying all SHA-256 hashes match before reading Validation data.",
            "3. Zero retries, zero tuning, zero feature modifications permitted.",
            "4. Gate failure results in immediate permanent retirement of strategy family.",
        ],
    }

    # Export scratch files
    scratch_dir = Path("scratch")
    scratch_dir.mkdir(parents=True, exist_ok=True)

    with open(scratch_dir / "m3e_0r_validation_manifest.json", "w", encoding="utf-8") as f:
        json.dump(validation_manifest, f, indent=2)

    with open(scratch_dir / "m3e_0r_reproducibility.json", "w", encoding="utf-8") as f:
        json.dump(environment_metadata, f, indent=2)

    logger.info("=== M3E.0R GOVERNANCE LOCK ENACTED SUCCESSFULLY ===")
    return validation_manifest


if __name__ == "__main__":
    run_m3e_0r_validation_lock()
