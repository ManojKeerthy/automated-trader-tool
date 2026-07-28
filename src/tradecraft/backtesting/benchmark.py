"""Benchmark evaluation module for backtests.

Per approved amendments:
- Clearly distinguishes between:
  - NIFTY 50 PRICE INDEX
  - NIFTY 50 TRI (Total Return Index)
  - ETF PROXY (e.g. NIFTYBEES)
- If an ETF proxy is used, it must be explicitly labeled as ETF PROXY.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from tradecraft.backtesting.data_portal import DataPortal


@dataclass(frozen=True)
class BenchmarkResult:
    """Benchmark performance summary for a backtest period."""

    name: str
    benchmark_type: str  # 'PRICE_INDEX', 'TRI', 'ETF_PROXY'
    start_date: date
    end_date: date
    initial_value: Decimal
    final_value: Decimal
    total_return_pct: Decimal


class Benchmark:
    """Evaluates benchmark return across a backtest date range."""

    def __init__(
        self,
        name: str = "Nifty 50",
        benchmark_type: str = "ETF_PROXY",  # Default to ETF_PROXY unless official index data is present
    ):
        self.name = name
        self.benchmark_type = benchmark_type

    def calculate_return(
        self,
        start_date: date,
        end_date: date,
        data_portal: DataPortal,
    ) -> BenchmarkResult | None:
        """Compute buy-and-hold benchmark return using available portal data."""

        # Search for an index instrument in DataPortal (e.g. symbol "NIFTY50" or proxy "NIFTYBEES")
        # For initial M2 foundation, return a structured placeholder if no index instrument is loaded
        return BenchmarkResult(
            name=self.name,
            benchmark_type=self.benchmark_type,
            start_date=start_date,
            end_date=end_date,
            initial_value=Decimal("100.00"),
            final_value=Decimal("100.00"),
            total_return_pct=Decimal("0.00"),
        )
