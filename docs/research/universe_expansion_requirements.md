# NIFTY 250 UNIVERSE EXPANSION ARCHITECTURAL REQUIREMENTS (M3C.1 PREPARATION)

> **ARCHITECTURAL ROADMAP**: Requirements for transitioning from NIFTY 50 research universe to NIFTY 250 Point-in-Time universe in Milestone M3C.1.

---

> [!CAUTION]
> **CRITICAL RULE**: Current NIFTY 250 index constituents MUST NEVER be projected backward through history. Historical universe membership must be point-in-time verified for every trading date $T$.

---

## 1. MANDATORY ARCHITECTURAL REQUIREMENTS FOR M3C.1

1. **Point-in-Time Index Membership**:
   - `UniverseMembership` table must store exact historical index inclusion and exclusion dates (`effective_from`, `effective_to`) for all NIFTY 250 additions and removals between 2016 and 2026.
2. **Survivorship Bias Elimination**:
   - Delisted companies, acquired entities, and demoted index constituents must be preserved in historical market data to eliminate survivorship bias.
3. **Corporate Action Adjustment Engine**:
   - Explicit handling of stock splits, bonus issues, rights offerings, and extraordinary dividends across all 250 instruments.
4. **Symbol & Identity Tracking**:
   - Permanent UUID tracking per instrument to handle corporate name changes and symbol reassignments (e.g. `TATAMOTORS`, `M&M`).
5. **Liquidity & Turnover Filtering**:
   - Point-in-time minimum daily turnover filters ($\text{Volume} \times \text{Close} \ge ₹5,000,000$) to prevent non-executable fills in illiquid mid-caps.
6. **Benchmark Selection & Index Data**:
   - Point-in-time benchmark series for NIFTY 50, NIFTY 500, and NIFTY MIDCAP 100 to support relative strength calculation.
