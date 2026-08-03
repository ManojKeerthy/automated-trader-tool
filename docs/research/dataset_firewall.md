# TRADECRAFT DATASET FIREWALL SPECIFICATION

> **FIREWALL SPECIFICATION**: Chronological dataset partition boundaries and runtime isolation guards.

---

## 1. HISTORICAL DATASET PARTITIONS

| Partition Name | Start Date | End Date | Status | Access Permitted? | Access Counter Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DEVELOPMENT`** | `2016-08-01` | `2021-12-31` | Consumed in Cycle 1 | **YES** (Cycle 1 only) | N/A |
| **`VALIDATION`** | `2022-01-01` | `2024-06-30` | **SEALED** | **NO** | `VALIDATION_ACCESS_COUNT = 0` |
| **`FINAL TEST`** | `2024-07-01` | `2026-07-28` | **SEALED** | **NO** | `FINAL_TEST_ACCESS_COUNT = 0` |

---

## 2. RUNTIME FIREWALL GUARD

The `DevelopmentDataFirewall` guard validates query dates on every database lookup, DataPortal access, feature calculation, and regime query:

```python
class DevelopmentDataFirewall:
    def validate_date(self, query_date: date) -> None:
        if query_date > DEVELOPMENT_SPLIT.end_date:
            if VALIDATION_SPLIT.contains(query_date):
                self._validation_access_count += 1
            elif FINAL_TEST_SPLIT.contains(query_date):
                self._final_test_access_count += 1
            raise DataBoundaryViolationError(
                f"DATA FIREWALL VIOLATION: Attempted to access date {query_date} "
                f"which is beyond DEVELOPMENT boundary ({DEVELOPMENT_SPLIT.end_date}). "
                "VALIDATION and FINAL_TEST access is strictly forbidden."
            )
```

---

## 3. FIREWALL VIOLATION PENALTY
If `VALIDATION_ACCESS_COUNT > 0` or `FINAL_TEST_ACCESS_COUNT > 0` occurs during Development research, the milestone immediately outputs `M3B_FIREWALL_FAILURE` and terminates.
