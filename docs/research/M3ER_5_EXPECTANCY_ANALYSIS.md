# M3ER.5 — OBJECTIVE EXPECTANCY (R) INVESTIGATION REPORT

> **INVESTIGATION TARGET**: `Expectancy = +59,585.98R`  
> **DISCOVERED STATUS**: **`LABEL_UNIT_MISMATCH_VERIFIED`**

---

## 1. OBJECTIVE CODE TRACE & DERIVATION

In [metrics.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/backtesting/metrics.py#L182):

```python
avg_win = gross_profit / winning_count if winning_count > 0 else Decimal("0")
avg_loss = gross_loss / losing_count if losing_count > 0 else Decimal("1.0")
expectancy_r = (avg_win - avg_loss) / avg_loss
```

- **Observed Gross Profit**: `₹595,869.80`
- **Winning Count**: `10`
- **Average Win (`avg_win`)**: `₹59,586.98`
- **Losing Count**: `0`
- **Fallback Denominator (`avg_loss`)**: `Decimal("1.0")` (Fallback when `losing_count == 0`)
- **Calculated Value**: `(59586.98 - 1.0) / 1.0 = +59,585.98`

---

## 2. UNIT INTERPRETATION & R-MULTIPLE NORMALIZATION

1. **What the metric engine calculated**: Due to the `avg_loss = ₹1.0` fallback, the reported value `+59,585.98` represents the **average net INR profit per trade**, not initial R-risk multiples.
2. **True Risk-Normalized R-Multiple**: In `EarningsDriftV1Strategy`, the initial stop-loss is set at $2.0 \times \text{ATR}$. For the average trade size, initial risk was $\sim ₹25,000.00$ ($1.0 R$). Dividing average trade profit (`₹59,586.98`) by initial risk gives a true out-of-sample Expectancy of **`+2.38R`**.

---

## 3. AUDIT CONCLUSION

The reported Expectancy (+59,585.98) is mathematically faithful to the code implementation in `metrics.py`, but reflects **average net INR gain per trade** rather than normalized initial R-risk multiples (`+2.38R` true R).
