"""Chronological Data Splitter for M3B Research Laboratory.

Defines the non-overlapping train, validation, and untouched final test windows,
along with rolling walk-forward window generators.
"""
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DataSplit:
    name: str
    start_date: date
    end_date: date
    is_untouched_final: bool = False


# Approved M3B Data Splits
TRAIN_SPLIT = DataSplit(
    name="TRAIN",
    start_date=date(2016, 8, 1),
    end_date=date(2021, 12, 31),
    is_untouched_final=False,
)

VALIDATION_SPLIT = DataSplit(
    name="VALIDATION",
    start_date=date(2022, 1, 1),
    end_date=date(2024, 6, 30),
    is_untouched_final=False,
)

FINAL_TEST_SPLIT = DataSplit(
    name="FINAL_TEST",
    start_date=date(2024, 7, 1),
    end_date=date(2026, 7, 28),
    is_untouched_final=True,
)


@dataclass(frozen=True)
class WalkForwardWindow:
    index: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date


class ChronologicalDataSplitter:
    """Provides structured data window partitions for strategy evaluation."""

    def __init__(self) -> None:
        self.train_split = TRAIN_SPLIT
        self.validation_split = VALIDATION_SPLIT
        self.final_test_split = FINAL_TEST_SPLIT

    def generate_walk_forward_windows(self) -> list[WalkForwardWindow]:
        """Generates rolling 3-year train / 1-year test walk-forward windows.

        Spans the research period 2016-08-01 through 2024-06-30 (excluding Final Test).
        """
        windows = [
            WalkForwardWindow(
                index=1,
                train_start=date(2016, 8, 1),
                train_end=date(2019, 7, 31),
                test_start=date(2019, 8, 1),
                test_end=date(2020, 7, 31),
            ),
            WalkForwardWindow(
                index=2,
                train_start=date(2017, 8, 1),
                train_end=date(2020, 7, 31),
                test_start=date(2020, 8, 1),
                test_end=date(2021, 7, 31),
            ),
            WalkForwardWindow(
                index=3,
                train_start=date(2018, 8, 1),
                train_end=date(2021, 7, 31),
                test_start=date(2021, 8, 1),
                test_end=date(2022, 7, 31),
            ),
            WalkForwardWindow(
                index=4,
                train_start=date(2019, 8, 1),
                train_end=date(2022, 7, 31),
                test_start=date(2022, 8, 1),
                test_end=date(2023, 7, 31),
            ),
            WalkForwardWindow(
                index=5,
                train_start=date(2020, 8, 1),
                train_end=date(2023, 7, 31),
                test_start=date(2023, 8, 1),
                test_end=date(2024, 6, 30),
            ),
        ]
        return windows
