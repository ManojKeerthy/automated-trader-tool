# TRADECRAFT RESEARCH METHODOLOGY & EXPERIMENT LIFECYCLE

> **METHODOLOGICAL SPECIFICATION**: Conceptual taxonomy and research lifecycle standards for TradeCraft.

---

## 1. CONCEPTUAL TAXONOMY — DO NOT CONFLATE

TradeCraft strictly distinguishes between nine distinct levels of research validity. Conflating these concepts is prohibited.

```mermaid
flowchart TD
    A["1. Engineering Correctness (Bug-Free Code & Accounting)"] --> B["2. Statistical Evidence (Sample Size & Conservation)"]
    B --> C["3. Economic Plausibility (Sound Market Mechanism)"]
    C --> D["4. Backtest Profitability (Positive PnL)"]
    D --> E["5. Robustness (Friction & Regime Sensitivity)"]
    E --> F["6. Development Survival (Passes Pre-declared Gate)"]
    F --> G["7. Validation Survival (Out-of-Sample Un-peeked Data)"]
    G --> H["8. Final Test Survival (Paper Trading / Final Period)"]
    H --> I["9. Production Readiness (Live Broker Allocation)"]
```

### Key Methodological Rules:
1. **Backtest Profitability $\neq$ Development Survival**: A strategy with +20.46% return (Mean Reversion V3) is NOT a Development Survivor if it fails any pre-declared gate criterion (Win Rate 14.2% < 35.0%).
2. **Development Survival $\neq$ Out-of-Sample Edge**: Passing the Development Gate means ONLY that a strategy is `ELIGIBLE_FOR_FUTURE_VALIDATION`. It does not guarantee out-of-sample edge.
3. **Engineering Defect $\neq$ Strategy Failure**: An accounting residual or sizing defect invalidates the backtest run; it does not prove or disprove strategy edge.

---

## 2. RESEARCH EXPERIMENT LIFECYCLE

```mermaid
sequenceDiagram
    participant R as Researcher / Agent
    participant H as Hypothesis Registry
    participant F as Data Firewall
    participant E as Backtest Engine
    participant G as Development Gate
    participant L as Research Ledger

    R->>H: 1. Pre-register Hypothesis & Parameter Provenance
    H->>H: Audit Provenance (Alternatives Tested = NO, PnL Used = NO)
    H-->>R: Export Frozen SHA256 Hash
    R->>F: 2. Check Dataset Boundary (DEVELOPMENT Only)
    F-->>R: Boundary Approved
    R->>E: 3. Run Blind Signal Viability Check (P&L-Blind)
    E-->>R: Viability Approved (>= 50 signals, >= 10 inst)
    R->>E: 4. Execute Single Backtest (FORCE_CLOSE)
    E-->>R: Reconciled Trade Ledger & Equity Curve
    R->>G: 5. Evaluate Development Survivor Gate (V2DevelopmentGate v1.0)
    G-->>L: 6. Record Outcome (DEVELOPMENT_SURVIVOR or ABANDON_FAMILY)
    L-->>R: Immutable Ledger Entry Persisted
```
