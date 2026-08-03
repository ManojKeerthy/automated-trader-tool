"""Data Firewall for M3B.3 preventing unauthorized access to VALIDATION and FINAL_TEST datasets."""

from datetime import date

from tradecraft.research.splits import DEVELOPMENT_SPLIT, FINAL_TEST_SPLIT, VALIDATION_SPLIT


class DataBoundaryViolationError(Exception):
    """Raised when an operation attempts to access data outside DEVELOPMENT boundary."""

    pass


class DevelopmentDataFirewall:
    """Enforces strict DEVELOPMENT dataset firewall (2016-08-01 to 2021-12-31)."""

    def __init__(self) -> None:
        self.development_access_count: int = 0
        self.validation_access_count: int = 0
        self.final_test_access_count: int = 0

    def validate_date(self, target_date: date) -> None:
        """Validate a single target date against DEVELOPMENT firewall."""
        if target_date > DEVELOPMENT_SPLIT.end_date:
            if target_date <= VALIDATION_SPLIT.end_date:
                self.validation_access_count += 1
            elif target_date <= FINAL_TEST_SPLIT.end_date:
                self.final_test_access_count += 1
            else:
                self.final_test_access_count += 1

            raise DataBoundaryViolationError(
                f"DATA FIREWALL VIOLATION: Attempted to access date {target_date} "
                f"which is beyond DEVELOPMENT boundary ({DEVELOPMENT_SPLIT.end_date}). "
                f"VALIDATION and FINAL_TEST access is strictly forbidden."
            )

        if target_date < DEVELOPMENT_SPLIT.start_date:
            raise DataBoundaryViolationError(
                f"DATA FIREWALL VIOLATION: Attempted to access date {target_date} "
                f"prior to DEVELOPMENT start date ({DEVELOPMENT_SPLIT.start_date})."
            )

        self.development_access_count += 1

    def validate_range(self, start_date: date, end_date: date) -> None:
        """Validate a date range against DEVELOPMENT firewall."""
        self.validate_date(start_date)
        self.validate_date(end_date)


# Global singleton instance for M3B.3 audit execution
GLOBAL_FIREWALL = DevelopmentDataFirewall()
