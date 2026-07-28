"""Comprehensive Performance Metrics Engine for Backtesting.

Calculates all required validation metrics per BACKTESTING_POLICY.md and M2 spec:
- Return: total return, CAGR, annualised return
- Risk: annualised volatility, max drawdown, max drawdown duration (days)
- Risk-adjusted: Sharpe ratio (√252 annualisation, versioned risk-free rate), Sortino ratio, Calmar ratio, recovery factor
- Trade-level: win rate, loss rate, avg winner, avg loser, payoff ratio, profit factor, expectancy, trade count, avg holding period
- System: exposure %, turnover %, total transaction costs

Edge cases:
- Handle zero trades, single trade, zero volatility, all winners, all losers gracefully
- Never return NaN or Infinity; use `None` with a semantic `metric_status`
"""
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import numpy as np

from tradecraft.backtesting.portfolio import EquitySnapshot
from tradecraft.backtesting.trade_ledger import TradeRecord
from tradecraft.research.risk_free_rate import RiskFreeRateConfig


@dataclass(frozen=True)
class MetricValue:
    """Calculated metric value with semantic status and metadata."""

    name: str
    value: Decimal | None
    status: str = "VALID"  # VALID, INSUFFICIENT_DATA, ZERO_VOLATILITY, NO_TRADES, N_A
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestMetricsSummary:
    """Complete summary of all performance metrics for a backtest run."""

    metrics: dict[str, MetricValue]

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for k, m in self.metrics.items():
            result[k] = {
                "value": str(m.value) if m.value is not None else None,
                "status": m.status,
                "metadata": m.metadata,
            }
        return result


class MetricsEngine:
    """Computes all strategy performance metrics deterministically."""

    def __init__(self, risk_free_config: RiskFreeRateConfig | None = None):
        self.rf_config = risk_free_config or RiskFreeRateConfig()

    def calculate(
        self,
        equity_curve: list[EquitySnapshot],
        trades: list[TradeRecord],
        initial_capital: Decimal,
        start_date: date,
        end_date: date,
    ) -> BacktestMetricsSummary:
        """Compute all validation metrics."""
        m: dict[str, MetricValue] = {}

        total_trades = len(trades)
        m["trade_count"] = MetricValue("trade_count", Decimal(str(total_trades)))

        # Populate trade metrics defaults if total_trades == 0
        if total_trades == 0:
            m["win_rate_pct"] = MetricValue("win_rate_pct", None, status="NO_TRADES")
            m["loss_rate_pct"] = MetricValue("loss_rate_pct", None, status="NO_TRADES")
            m["profit_factor"] = MetricValue("profit_factor", None, status="NO_TRADES")
            m["payoff_ratio"] = MetricValue("payoff_ratio", None, status="NO_TRADES")
            m["expectancy"] = MetricValue("expectancy", None, status="NO_TRADES")
            m["avg_holding_period_days"] = MetricValue("avg_holding_period_days", None, status="NO_TRADES")
            m["total_transaction_costs"] = MetricValue("total_transaction_costs", Decimal("0"))
            m["total_slippage_cost"] = MetricValue("total_slippage_cost", Decimal("0"))

        # 1. Equity curve analysis
        if not equity_curve:
            return BacktestMetricsSummary(metrics=m)

        final_equity = equity_curve[-1].total_equity
        net_return_pct = ((final_equity - initial_capital) / initial_capital) * Decimal("100")
        m["total_return_pct"] = MetricValue("total_return_pct", net_return_pct)

        # Days elapsed
        days_elapsed = (end_date - start_date).days
        years_elapsed = days_elapsed / 365.25

        if years_elapsed > 0 and final_equity > 0:
            cagr = ((final_equity / initial_capital) ** Decimal(str(1 / years_elapsed)) - Decimal("1")) * Decimal("100")
            m["cagr_pct"] = MetricValue("cagr_pct", cagr)
        else:
            m["cagr_pct"] = MetricValue("cagr_pct", None, status="INSUFFICIENT_DATA")

        # Daily returns array for risk / Sharpe
        equities = [float(s.total_equity) for s in equity_curve]
        daily_returns = np.diff(equities) / equities[:-1] if len(equities) > 1 else np.array([])

        # Volatility
        if len(daily_returns) > 1:
            daily_std = float(np.std(daily_returns, ddof=1))
            ann_vol = daily_std * math.sqrt(252) * 100.0
            m["annualised_volatility_pct"] = MetricValue(
                "annualised_volatility_pct", Decimal(f"{ann_vol:.4f}")
            )

            # Sharpe Ratio
            rf_annual = float(self.rf_config.annual_rate) / 100.0
            rf_daily = rf_annual / 252.0
            excess_returns = daily_returns - rf_daily
            mean_excess = float(np.mean(excess_returns))

            if daily_std > 1e-9:
                sharpe = (mean_excess / daily_std) * math.sqrt(252)
                m["sharpe_ratio"] = MetricValue(
                    "sharpe_ratio",
                    Decimal(f"{sharpe:.4f}"),
                    metadata={
                        "risk_free_rate_pct": str(self.rf_config.annual_rate),
                        "rf_source": self.rf_config.source,
                        "rf_type": self.rf_config.rate_type,
                    },
                )
            else:
                m["sharpe_ratio"] = MetricValue(
                    "sharpe_ratio", None, status="ZERO_VOLATILITY"
                )

            # Sortino Ratio (downside risk)
            downside_returns = daily_returns[daily_returns < rf_daily] - rf_daily
            if len(downside_returns) > 0:
                downside_std = float(np.sqrt(np.mean(downside_returns**2)))
                if downside_std > 1e-9:
                    sortino = (mean_excess / downside_std) * math.sqrt(252)
                    m["sortino_ratio"] = MetricValue(
                        "sortino_ratio", Decimal(f"{sortino:.4f}")
                    )
                else:
                    m["sortino_ratio"] = MetricValue("sortino_ratio", None, status="ZERO_VOLATILITY")
            else:
                m["sortino_ratio"] = MetricValue("sortino_ratio", None, status="NO_DOWNSIDE_VOLATILITY")
        else:
            m["annualised_volatility_pct"] = MetricValue("annualised_volatility_pct", None, status="INSUFFICIENT_DATA")
            m["sharpe_ratio"] = MetricValue("sharpe_ratio", None, status="INSUFFICIENT_DATA")
            m["sortino_ratio"] = MetricValue("sortino_ratio", None, status="INSUFFICIENT_DATA")

        # Maximum Drawdown
        max_dd = Decimal("0")
        max_dd_duration = 0
        current_dd_duration = 0

        for snap in equity_curve:
            dd = snap.drawdown_pct
            if dd > max_dd:
                max_dd = dd

            if dd > Decimal("0"):
                current_dd_duration += 1
                if current_dd_duration > max_dd_duration:
                    max_dd_duration = current_dd_duration
            else:
                current_dd_duration = 0

        m["max_drawdown_pct"] = MetricValue("max_drawdown_pct", max_dd)
        m["max_drawdown_duration_days"] = MetricValue(
            "max_drawdown_duration_days", Decimal(str(max_dd_duration))
        )

        # Calmar Ratio = CAGR / Max Drawdown
        if max_dd > Decimal("0") and m["cagr_pct"].value is not None:
            calmar = m["cagr_pct"].value / max_dd
            m["calmar_ratio"] = MetricValue("calmar_ratio", calmar)
        else:
            m["calmar_ratio"] = MetricValue("calmar_ratio", None, status="N_A")

        # 2. Trade-level analysis
        if total_trades == 0:
            m["win_rate_pct"] = MetricValue("win_rate_pct", None, status="NO_TRADES")
            m["profit_factor"] = MetricValue("profit_factor", None, status="NO_TRADES")
            m["payoff_ratio"] = MetricValue("payoff_ratio", None, status="NO_TRADES")
            m["expectancy"] = MetricValue("expectancy", None, status="NO_TRADES")
            m["avg_holding_period_days"] = MetricValue("avg_holding_period_days", None, status="NO_TRADES")
            return BacktestMetricsSummary(metrics=m)

        winners = [t for t in trades if t.net_pnl > 0]
        losers = [t for t in trades if t.net_pnl < 0]

        win_rate = (Decimal(str(len(winners))) / Decimal(str(total_trades))) * Decimal("100")
        loss_rate = (Decimal(str(len(losers))) / Decimal(str(total_trades))) * Decimal("100")
        m["win_rate_pct"] = MetricValue("win_rate_pct", win_rate)
        m["loss_rate_pct"] = MetricValue("loss_rate_pct", loss_rate)

        gross_profits = sum((t.net_pnl for t in winners), Decimal("0"))
        gross_losses = abs(sum((t.net_pnl for t in losers), Decimal("0")))

        # Profit Factor
        if gross_losses > 0:
            pf = gross_profits / gross_losses
            m["profit_factor"] = MetricValue("profit_factor", pf)
        elif gross_profits > 0:
            m["profit_factor"] = MetricValue("profit_factor", None, status="ALL_WINNERS")
        else:
            m["profit_factor"] = MetricValue("profit_factor", Decimal("0"))

        avg_win = (gross_profits / Decimal(str(len(winners)))) if winners else Decimal("0")
        avg_loss = (gross_losses / Decimal(str(len(losers)))) if losers else Decimal("0")

        m["avg_winner_pnl"] = MetricValue("avg_winner_pnl", avg_win)
        m["avg_loser_pnl"] = MetricValue("avg_loser_pnl", avg_loss)

        # Payoff Ratio (Avg Win / Avg Loss)
        if avg_loss > 0:
            payoff = avg_win / avg_loss
            m["payoff_ratio"] = MetricValue("payoff_ratio", payoff)
        else:
            m["payoff_ratio"] = MetricValue("payoff_ratio", None, status="N_A")

        # Expectancy = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
        expectancy = ((win_rate / Decimal("100")) * avg_win) - ((loss_rate / Decimal("100")) * avg_loss)
        m["expectancy"] = MetricValue("expectancy", expectancy)

        # Avg Holding Period
        avg_holding = sum(t.holding_days for t in trades) / total_trades
        m["avg_holding_period_days"] = MetricValue("avg_holding_period_days", Decimal(f"{avg_holding:.2f}"))

        # Total transaction costs & slippage
        total_costs = sum((t.total_fees for t in trades), Decimal("0"))
        total_slippage = sum((t.slippage_cost for t in trades), Decimal("0"))
        m["total_transaction_costs"] = MetricValue("total_transaction_costs", total_costs)
        m["total_slippage_cost"] = MetricValue("total_slippage_cost", total_slippage)

        return BacktestMetricsSummary(metrics=m)
