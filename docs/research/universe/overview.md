# POINT-IN-TIME DATA ARCHITECTURE OVERVIEW

```mermaid
flowchart TD
    Strategy["Strategy / Research Engine"] --> API["UniverseAPI"]
    API --> SM["SecurityMaster (security_uuid)"]
    API --> HM["HistoricalMembershipEngine"]
    API --> CA["CorporateActionRegistry"]
    API --> SG["SurvivorshipGuard"]
    API --> DP["DataPortal"]
    DP --> Provider["DataProvider (Zerodha/NSE/Polygon/CSV)"]
    DP --> MC["MetadataCatalog & Dataset Versioning"]
```

The Point-in-Time Data Architecture ensures that at any historical date $T$, the research engine can reconstruct exactly which securities were listed, investable, and members of any specified universe (NIFTY 50, NIFTY 100, NIFTY 200, NIFTY 250, NIFTY 500), without relying on today's index membership.
