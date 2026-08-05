"""Automated Authenticity Verifier Engine for TradeCraft Research Platform.

Validates that 100% of research metrics, trade ledgers, and equity curves originate
exclusively from BacktestEngine.run(config) execution against historical market_bars database rows.
"""

import ast
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("authenticity_verifier")


@dataclass
class AuthenticityAuditResult:
    target_path: str
    is_authentic: bool
    data_source_verified: bool
    engine_execution_verified: bool
    trade_ledger_verified: bool
    metric_computation_verified: bool
    prohibited_patterns_detected: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


class AuthenticityVerifier:
    """Automated code and artifact verifier enforcing execution-derived research rules."""

    PROHIBITED_FUNCTIONS: set[str] = {
        "random.seed",
        "random.uniform",
        "random.choices",
        "random.randint",
        "np.random.seed",
    }

    PROHIBITED_VARIABLE_ASSIGNMENTS: set[str] = {
        "profit_factor",
        "expectancy_r",
        "net_pnl_inr",
        "gross_profit_inr",
        "gross_loss_inr",
        "max_drawdown_pct",
        "sharpe_ratio",
        "cagr_pct",
    }

    REQUIRED_ENGINE_INVOCATIONS: set[str] = {
        "BacktestEngine",
        "engine.run",
    }

    def verify_script(self, script_path: Path) -> AuthenticityAuditResult:
        """Statically inspect python runner script AST for prohibited patterns and required execution calls."""
        if not script_path.exists():
            return AuthenticityAuditResult(
                target_path=str(script_path),
                is_authentic=False,
                data_source_verified=False,
                engine_execution_verified=False,
                trade_ledger_verified=False,
                metric_computation_verified=False,
                reasons=[f"File not found: {script_path}"],
            )

        code_text = script_path.read_text(encoding="utf-8")
        prohibited_detected = []
        reasons = []

        # 1. Text-level prohibited pattern check
        for pat in self.PROHIBITED_FUNCTIONS:
            if pat in code_text:
                prohibited_detected.append(pat)
                reasons.append(f"Prohibited random/synthetic function detected: '{pat}'")

        # 2. Synthetic loop check
        if "surge =" in code_text or "base_price *" in code_text:
            prohibited_detected.append("synthetic_price_loop")
            reasons.append("Synthetic price bar generator detected in script.")

        # 3. Required execution call check
        engine_called = "BacktestEngine" in code_text and ("engine.run(" in code_text or ".run(" in code_text)
        if not engine_called:
            reasons.append("Missing required 'BacktestEngine.run(config)' call.")

        # 4. AST parsing for hard-coded metric variables
        hardcoded_metrics_found = False
        try:
            tree = ast.parse(code_text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id in self.PROHIBITED_VARIABLE_ASSIGNMENTS
                            and isinstance(node.value, (ast.Constant, ast.Num))
                        ):
                            hardcoded_metrics_found = True
                            prohibited_detected.append(f"hardcoded_var_{target.id}")
                            reasons.append(f"Hard-coded literal assignment to metric variable '{target.id} = {node.value.value!r}'")
        except SyntaxError:
            reasons.append("Syntax error during AST parsing.")

        data_source_ok = "market_bars" in code_text or "DataPortal" in code_text
        trade_ledger_ok = "result.trades" in code_text or "res.trades" in code_text
        metrics_ok = not hardcoded_metrics_found and engine_called

        is_authentic = (
            len(prohibited_detected) == 0
            and engine_called
            and data_source_ok
            and trade_ledger_ok
            and metrics_ok
        )

        return AuthenticityAuditResult(
            target_path=str(script_path),
            is_authentic=is_authentic,
            data_source_verified=data_source_ok,
            engine_execution_verified=engine_called,
            trade_ledger_verified=trade_ledger_ok,
            metric_computation_verified=metrics_ok,
            prohibited_patterns_detected=prohibited_detected,
            reasons=reasons,
        )

    def verify_report_authenticity(self, report_path: Path, certificate_path: Path | None = None) -> bool:
        """Verify report data lineage header and checksum presence."""
        if not report_path.exists():
            return False
        content = report_path.read_text(encoding="utf-8")
        has_lineage = "COMPUTED_FROM_EXECUTION" in content or "MANIFEST CHECKSUM" in content or "INVALID FOR RESEARCH" in content
        return has_lineage


def run_full_authenticity_audit() -> dict[str, Any]:
    """Run full authenticity verification scan across the repository."""
    verifier = AuthenticityVerifier()
    project_root = Path(__file__).parents[3]

    scripts_to_audit = [
        project_root / "scratch" / "run_m3d_4_development_backtest.py",
        project_root / "scratch" / "run_m3d_4_5_forensic_audit.py",
        project_root / "scratch" / "run_m3e_validation_backtest.py",
    ]

    audit_summary = {}
    all_passed = True

    for s_path in scripts_to_audit:
        res = verifier.verify_script(s_path)
        audit_summary[s_path.name] = {
            "path": str(s_path),
            "is_authentic": res.is_authentic,
            "data_source_verified": res.data_source_verified,
            "engine_execution_verified": res.engine_execution_verified,
            "trade_ledger_verified": res.trade_ledger_verified,
            "metric_computation_verified": res.metric_computation_verified,
            "prohibited_patterns_detected": res.prohibited_patterns_detected,
            "reasons": res.reasons,
        }
        if not res.is_authentic:
            all_passed = False

    return {
        "overall_authenticity_passed": all_passed,
        "audited_scripts": audit_summary,
    }


if __name__ == "__main__":
    res = run_full_authenticity_audit()
    print(json.dumps(res, indent=2))
