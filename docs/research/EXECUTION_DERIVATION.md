# EXECUTION DERIVATION SPECIFICATION

This document outlines the strict technical requirements for deriving all metrics exclusively from `BacktestResult`:

1. **No Hard-Coded Metric Assignments**:
   Metric variables must not be assigned constant numeric values. They must be calculated dynamically via methods on `BacktestResult` or by processing `BacktestResult.trades`.

2. **No Random or Synthetic Trade Generation**:
   Trade objects must be generated strictly by `BacktestEngine.run()` processing strategy signals over price bars.

3. **Verification via `AuthenticityVerifier`**:
   The `AuthenticityVerifier` parses AST structures of runner scripts to reject any syntax or pattern violating these requirements.
