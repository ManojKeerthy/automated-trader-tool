# ADR-006: Cross-Platform Portability

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution)

## Context

Development begins on Windows but production deployment targets Linux. macOS is also a supported development platform. The same codebase must work on all three.

## Decision

Follow the principle: **Build once, configure per environment, run anywhere.**

### Code Portability
- Python: Use `pathlib.Path` for all filesystem operations
- Node.js: Use `path` module
- No hard-coded drive letters, path separators, or OS-specific paths
- No OS-specific temporary directories
- No shell-specific commands in application code
- No OS-specific networking assumptions

### Infrastructure
- Docker Compose for all infrastructure services
- Same `docker compose up` command on all platforms
- PostgreSQL always in Docker (local dev)

### Configuration
- Environment variables for all environment-specific values
- `.env` file for local development
- No OS-specific configuration files

### Scripts
- Prefer portable commands (Python CLI, Docker Compose, Make)
- Avoid separate `run-windows.bat` / `run-mac.sh` / `run-linux.sh`
- If OS-specific scripts unavoidable, they must be thin wrappers

### Dependencies
- Pin important dependencies
- Verify cross-platform support for native dependencies
- Do not introduce OS-specific libraries without documentation

## Rationale

1. **Portability**: Avoids lock-in to any operating system
2. **Cloud readiness**: Linux production must not require code changes
3. **Developer experience**: Same workflow everywhere
4. **CI**: Enables multi-OS testing

## Consequences

- CI must test on Windows + Linux (macOS best effort)
- Same market data + strategy + config must produce equivalent results across OS
- Floating-point tolerances documented where numerical differences arise
- Platform-specific differences must NEVER silently change trading decisions
