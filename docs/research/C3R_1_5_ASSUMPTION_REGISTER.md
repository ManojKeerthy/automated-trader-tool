# C3R_1_5 — INSTITUTIONAL ASSUMPTION REGISTER & DECISION LOG (ALPHA-015)

> **AUDIT FOCUS**: Complete assumption audit, architectural decision log, and stage kill criteria for candidate `ALPHA-015`

---

## 1. ARCHITECTURAL DECISION LOG
- **DEC-001 (Long-Only)**: Long-only cash delivery chosen due to Indian equity shorting constraints.
- **DEC-002 (Max 10 Holdings)**: Max 10 positions chosen to balance stock diversification against turnover drag.
- **DEC-003 (NIFTY 50 / NIFTY 500)**: Liquid benchmark universe chosen for point-in-time constituent integrity.

---

## 2. ASSUMPTION REGISTER
- **ASM-001 (Persistence)**: Relative strength persists over 30–60 session horizons due to slow institutional fund flows.
- **ASM-002 (Survivorship Protection)**: DataPortal point-in-time constituent reconstruction eliminates survivorship bias.
- **ASM-003 (Friction Realism)**: Delivery fees + 5 bps fixed slippage accurately models Indian friction drag.
- **ASM-004 (Regime Guard)**: Absolute momentum filter protects capital during market crashes.

---

## 3. STAGE KILL CRITERIA
- **Data Gate Trigger**: Mark `BLOCKED_PENDING_DATA` if point-in-time constituent data or sector benchmarks cannot be reconstructed in C3R.2.
- **Friction Gate Trigger**: Mark `UNFEASIBLE_FRICTION` if expected turnover eats $>50\%$ of gross alpha in C3R.3.
