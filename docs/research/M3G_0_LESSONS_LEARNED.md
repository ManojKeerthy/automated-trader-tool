# M3G.0 — RESEARCH CYCLE 2 LESSONS LEARNED & KNOWLEDGE CAPTURE

> **DOCUMENT TYPE**: **`INSTITUTIONAL KNOWLEDGE CAPTURE`**

---

## 1. ENGINEERING LESSONS
- **Interface Contract Validation**: Strategy evaluate signatures must explicitly receive and forward active portfolio position state (`active_positions`) to ensure stateful counters (such as `_bars_held`) increment correctly on every trading session bar.
- **Automated Regression Testing**: Every stateful exit rule must be accompanied by explicit unit test cases verifying counter increments, boundary conditions, and deletion upon position liquidation.

---

## 2. RESEARCH GOVERNANCE LESSONS
- **Forensic Consistency Audits**: Independent metric recalculation and exit reason forensics are essential. They successfully prevented deploying a flawed strategy version that relied on missing position state.
- **Preflight Access Firewalls**: Hardened database checksum verification and dataset firewall counts guarantee strict out-of-sample data integrity.

---

## 3. STATISTICAL & QUANTITATIVE STRATEGY LESSONS
- **Secular Trend Distortions**: Disabling exit conditions during long bull markets causes passive equity accumulation that masquerades as strategy alpha.
- **Multi-Factor Requirement**: Raw single-factor PEAD momentum entry without market regime filters, volume gates, or earnings surprise filters suffers from high false-breakout frequency on NIFTY 50 large-cap stocks.

---

## 4. FUTURE STRATEGY DESIGN IMPLICATIONS FOR CYCLE 3
- Incorporate explicit market regime filters (e.g. NIFTY index trend filter).
- Include earnings surprise magnitude filters rather than simple price momentum surges.
- Combine PEAD signals with quality/volatility gates to filter out weak breakouts.
