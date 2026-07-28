# TradeCraft — Local Operation Guide

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Supported Platforms

| Platform | Status |
|----------|--------|
| Windows 10/11 | First-class (primary dev environment) |
| macOS | First-class |
| Linux | First-class (production target) |

## 2. Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Backend, quantitative engine |
| Node.js | 18+ | Dashboard build |
| Docker + Docker Compose | Latest | PostgreSQL, services |
| Git | Latest | Version control |

## 3. Quick Start (All Platforms)

```bash
# 1. Clone repository
git clone <repository-url>
cd automated-trader-tool

# 2. Configure environment
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD at minimum

# 3. Start infrastructure
docker compose up -d

# 4. Create Python virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

# 5. Install dependencies
pip install -e ".[dev]"

# 6. Run database migrations (when implemented)
# python -m tradecraft.db migrate

# 7. Start application (when implemented)
# python -m tradecraft

# 8. Open dashboard (when implemented)
# http://localhost:3000
```

## 4. Daily Trading Workflow

Target window: **~4:30 PM–6:00 PM IST** (after Indian market close)

```
1. Start system
   docker compose up -d
   python -m tradecraft  (when implemented)

2. System automatically:
   - Downloads latest market data
   - Runs data quality checks
   - Updates feature calculations
   - Runs active strategies
   - Generates trade proposals

3. Review dashboard:
   - Check portfolio status
   - Review trade proposals
   - APPROVE or REJECT proposals
   - Review risk status
   - Check system health

4. System processes approvals:
   - Validated orders queued for next market open
   - Protective stops updated

5. Shutdown (optional for paper trading)
```

## 5. Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| Storage | 256 GB SSD | 512 GB SSD |
| CPU | Any modern x64 | Multi-core recommended for backtesting |
| Network | Required for data download | Broadband |

## 6. File System Layout

```
automated-trader-tool/          # Source code (Git)
├── .env                        # Secrets (not committed)
├── data/                       # Downloaded/generated data (not committed)
│   ├── market/
│   ├── corporate_actions/
│   └── exports/
├── logs/                       # Application logs (not committed)
└── backups/                    # Database backups (not committed)
```

All runtime paths are configurable via environment variables.

## 7. Cross-Platform Notes

- All paths use `pathlib` — no hard-coded separators
- No dependency on Windows drive letters
- No dependency on `/home/` paths
- Timezone: Application uses `Asia/Kolkata` explicitly, never local TZ
- Shell commands via Python `subprocess` with platform detection where needed
- PostgreSQL runs identically in Docker on all platforms
