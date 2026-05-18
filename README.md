# MSRAP — Market State & Risk Analytics Platform

A research-grade analytics platform for Indian equity and derivatives markets (NSE). Ingests historical OHLCV data via yfinance, computes volatility surfaces, HMM regime states, and Fama-French factor loadings, and exposes everything through a dark-themed React dashboard.

> **Research only.** No order execution. No trading signals.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                           │
│                                                                 │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  React +    │    │  Spring Boot 3.2 │    │  FastAPI      │  │
│  │  Vite       │───▶│  (Java 21)       │    │  (Python 3.11)│  │
│  │  :3000      │    │  :8080           │    │  :8000        │  │
│  └─────────────┘    └────────┬─────────┘    └───────────────┘  │
│                              │                                  │
│             REST /api/*      │  subprocess                      │
│                              ▼                                  │
│                    ┌──────────────────┐                         │
│                    │  Python workers  │                         │
│                    │  (vol/regime/    │                         │
│                    │   factor/ingest) │                         │
│                    └────────┬─────────┘                         │
│                             │  SQLAlchemy                       │
│                             ▼                                   │
│                    ┌──────────────────┐                         │
│                    │  TimescaleDB     │                         │
│                    │  (PostgreSQL 15) │                         │
│                    │  :5432           │                         │
│                    └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow:**

1. `MarketScheduler` (Spring) fires cron → `IngestionService.ingestSymbol()` → spawns `python3 analytics/ingestion/fetcher.py --symbol X` subprocess → parses JSON stdout → upserts to `equity_ohlcv`
2. `AnalyticsService.run*Worker()` → spawns `python3 analytics/volatility/vol_worker.py --symbol X` etc. → workers read from DB via SQLAlchemy → write results back to `analytics_results / regime_states / factor_loadings`
3. React frontend calls Spring Boot REST API (`/api/analytics/...`) → Spring queries TimescaleDB → returns JSON

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | 24+ |
| Docker Compose | v2 (plugin) |
| Python | 3.11+ (for scripts outside Docker) |
| Java | 21 (for IDE dev only; Docker builds it) |

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url> msrap && cd msrap

# 2. Start all services (first run takes ~3 min to build images)
docker compose up --build -d

# 3. Wait for backend to be healthy
docker compose ps          # backend should show "healthy"

# 4. Trigger a full historical backfill (5 years for all 17 symbols)
curl -X POST http://localhost:8080/api/ingestion/backfill

# 5. Open the dashboard
open http://localhost:3000
```

Services:

| Service | URL |
|---------|-----|
| Frontend dashboard | http://localhost:3000 |
| Spring Boot API | http://localhost:8080/api |
| Spring Boot health | http://localhost:8080/api/actuator/health |
| TimescaleDB | localhost:5432 (user: `msrap`, pass: `msrap_secret`, db: `msrap`) |

---

## Running Without Docker (development)

### 1. Start TimescaleDB only

```bash
docker compose up timescaledb -d
```

### 2. Python analytics environment

```bash
cd analytics
pip install -r requirements.txt
# Set DB env vars
export DB_HOST=localhost DB_PORT=5432 DB_NAME=msrap DB_USER=msrap DB_PASSWORD=msrap_secret
```

### 3. Spring Boot backend

```bash
cd backend
./mvnw spring-boot:run
```

### 4. React frontend (Vite dev server)

```bash
cd frontend
npm install
npm run dev          # → http://localhost:5173
```

---

## CLI Scripts

All scripts live in `scripts/` and connect to the DB using the standard env vars (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).

### Backfill historical OHLCV

```bash
# Backfill specific symbols (5 years)
python scripts/backfill.py --symbols RELIANCE.NS TCS.NS --days 1825

# Backfill all 17 configured symbols
python scripts/backfill.py --all --days 1825

# Dry run — fetch but don't write
python scripts/backfill.py --all --dry-run
```

### Run analytics workers manually

```bash
# All workers for specific symbols
python scripts/run_analytics.py --symbols RELIANCE.NS TCS.NS

# Only volatility worker for all symbols
python scripts/run_analytics.py --all --workers vol

# All workers, all symbols
python scripts/run_analytics.py --all
```

### Health check

```bash
python scripts/health_check.py
python scripts/health_check.py --verbose
python scripts/health_check.py --staleness-days 3
```

### Options chain fetch

```bash
# Fetch 4 nearest expiries for a symbol and persist to DB
python analytics/ingestion/options_fetcher.py --symbol RELIANCE.NS --expiries 4
python analytics/ingestion/options_fetcher.py --symbol RELIANCE.NS --dry-run
```

---

## Python Unit Tests

```bash
# From repo root
pip install pytest numpy pandas hmmlearn scikit-learn statsmodels arch
pytest                        # runs all tests in analytics/tests/
pytest -v analytics/tests/test_vol_models.py
pytest -v analytics/tests/test_regime_models.py
pytest -v analytics/tests/test_factor_models.py
```

---

## REST API Reference

All endpoints are prefixed with `/api` (Spring Boot context path).

### Market Data — `/api/market`

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| `GET` | `/market/instruments` | — | All seeded instruments |
| `GET` | `/market/instruments/{symbol}` | — | Single instrument metadata |
| `GET` | `/market/instruments/sector/{sector}` | — | Instruments by sector |
| `GET` | `/market/symbols` | — | List of available ticker symbols |
| `GET` | `/market/ohlcv/{symbol}` | `interval=1d`, `days=365` | OHLCV bars |
| `GET` | `/market/ohlcv/{symbol}/latest` | `interval=1d` | Most recent bar |
| `GET` | `/market/ohlcv/{symbol}/range` | `interval`, `from`, `to` | Date-range OHLCV |

### Analytics — `/api/analytics`

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| `GET` | `/analytics/volatility/{symbol}` | `days=365` | All volatility metrics (timeseries) |
| `GET` | `/analytics/volatility/{symbol}/{metric}` | `days=365` | Single metric (e.g. `rv_21d`) |
| `GET` | `/analytics/regime/{symbol}` | `days=365` | HMM regime history |
| `GET` | `/analytics/regime/{symbol}/current` | — | Latest regime state |
| `GET` | `/analytics/factor/{symbol}` | `window=252`, `days=730` | Rolling factor loadings |
| `GET` | `/analytics/factor/{symbol}/latest` | `window=252` | Latest factor loadings |
| `GET` | `/analytics/summary/{symbol}` | — | Combined summary card |
| `POST` | `/analytics/run/volatility/{symbol}` | — | Trigger vol worker |
| `POST` | `/analytics/run/regime/{symbol}` | — | Trigger regime worker |
| `POST` | `/analytics/run/factor/{symbol}` | — | Trigger factor worker |
| `POST` | `/analytics/run/all/{symbol}` | — | Trigger all three workers |

### Ingestion — `/api/ingestion`

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| `POST` | `/ingestion/ingest/{symbol}` | `interval=1d` | Ingest (incremental) for one symbol |
| `POST` | `/ingestion/ingest/batch` | body: `["SYM1","SYM2"]`, `interval=1d` | Batch ingest |
| `POST` | `/ingestion/backfill` | — | Full backfill for all configured symbols |

### Actuator — `/api/actuator`

| Path | Description |
|------|-------------|
| `/actuator/health` | Service health (DB, disk) |
| `/actuator/info` | Build info |
| `/actuator/metrics` | JVM metrics |

---

## Database Schema

Tables are TimescaleDB hypertables partitioned by time. Schema is applied via `docker/init.sql` on first DB start.

| Table | Key columns | Hypertable partition |
|-------|-------------|----------------------|
| `equity_ohlcv` | `symbol, ts, interval` | 1 week |
| `options_chain` | `symbol, ts, expiry, strike, option_type` | 1 week |
| `futures_oi` | `symbol, ts, expiry` | 1 week |
| `analytics_results` | `symbol, ts, module, metric` | 1 month |
| `regime_states` | `symbol, ts` | 1 month |
| `factor_loadings` | `symbol, ts, window_days` | 1 month |
| `instruments` | `symbol` | (plain table) |

---

## Configured Symbols

17 NSE instruments are seeded by default (index and equity tickers use yfinance `.NS` / `^NSE*` suffixes):

`RELIANCE.NS` · `TCS.NS` · `INFY.NS` · `HDFCBANK.NS` · `ICICIBANK.NS` · `SBIN.NS` · `BHARTIARTL.NS` · `ITC.NS` · `KOTAKBANK.NS` · `LT.NS` · `AXISBANK.NS` · `BAJFINANCE.NS` · `HINDUNILVR.NS` · `WIPRO.NS` · `MARUTI.NS` · `^NSEI` · `^NSEBANK`

To add symbols, edit `msrap.ingestion.symbols` in `backend/src/main/resources/application.yml` and insert into the `instruments` table.

---

## Analytics Methodology

### Volatility

- **Close-to-close** — standard log-return rolling std
- **Parkinson** — H/L range estimator (more efficient than C-t-C)
- **Rogers-Satchell** — handles non-zero drift
- **Yang-Zhang** — minimum-variance unbiased; handles overnight gaps
- **GARCH family** — GARCH(1,1), GJR-GARCH, EGARCH; best model selected by AIC
- **Vol cone** — percentile distribution across 5/10/21/42/63/126/252-day windows

### Regime Classification

3-state Gaussian HMM fitted on `[log_return, rv_21d, rv_5d]` feature matrix. States are labelled post-hoc by ascending realised vol:

| State | Label | Interpretation |
|-------|-------|---------------|
| 0 | `low-vol` | Calm, range-bound |
| 1 | `trending` | Moderate vol, directional |
| 2 | `high-vol` | Stressed, crisis |

### Factor Model

Fama-French style factors constructed from the NSE universe using price-based proxies (no fundamental data required):

| Factor | Proxy |
|--------|-------|
| MKT | Equal-weighted universe return minus 6.5% annual Rf |
| SMB | High-vol (small-cap proxy) minus low-vol basket |
| HML | Low-36m-return (value proxy) minus high-return basket |
| MOM | 12-1 month momentum winners minus losers |
| QMJ | High rolling-Sharpe (quality) minus low |

Rolling 252-day OLS regression gives time-varying betas, alpha, R², and residual vol.

---

## Project Structure

```
msrap/
├── docker-compose.yml          ← Service orchestration
├── docker/init.sql             ← TimescaleDB schema (hypertables + seed data)
├── pytest.ini                  ← Python test config
├── scripts/
│   ├── backfill.py             ← Historical OHLCV backfill CLI
│   ├── run_analytics.py        ← Manual analytics trigger CLI
│   └── health_check.py        ← DB connectivity + freshness checker
├── analytics/                  ← Python workers (called as subprocesses by Java)
│   ├── ingestion/
│   │   ├── fetcher.py          ← yfinance OHLCV fetcher (stdout JSON)
│   │   └── options_fetcher.py  ← yfinance options chain fetcher
│   ├── volatility/
│   │   ├── vol_models.py       ← All vol estimators + GARCH + cone
│   │   └── vol_worker.py       ← Worker: reads DB → computes → writes DB
│   ├── regime/
│   │   ├── regime_models.py    ← HMM, breadth, sector RS
│   │   └── regime_worker.py
│   ├── factor/
│   │   ├── factor_models.py    ← IndiaFactorLibrary, rolling OLS, PCA
│   │   └── factor_worker.py
│   ├── utils/db.py             ← SQLAlchemy engine + helpers
│   ├── api.py                  ← FastAPI service (optional direct HTTP calls)
│   └── tests/
│       ├── test_vol_models.py
│       ├── test_regime_models.py
│       └── test_factor_models.py
├── backend/                    ← Spring Boot 3.2 (Java 21)
│   └── src/
│       ├── main/java/com/msrap/
│       │   ├── config/         ← AppConfig (CORS), IngestionProperties
│       │   ├── controller/     ← Market, Analytics, Ingestion, GlobalExceptionHandler
│       │   ├── model/          ← JPA entities
│       │   ├── repository/     ← Spring Data JPA repos
│       │   ├── scheduler/      ← MarketScheduler (daily cron)
│       │   └── service/        ← IngestionService, AnalyticsService, MarketDataService
│       └── test/java/com/msrap/
│           └── MsrapApplicationTests.java
└── frontend/                   ← React 18 + Vite + Recharts
    └── src/
        ├── hooks/useSymbolData.js   ← Shared data-fetching hook
        ├── components/
        │   ├── charts/Charts.jsx    ← PriceChart, SeriesChart, RegimeChart, VolConeChart, FactorBetaChart
        │   ├── dashboard/Cards.jsx  ← StatCard, Skeleton, PageSkeleton, Grid …
        │   └── error/ErrorBoundary.jsx
        ├── pages/                   ← Dashboard, VolatilityPage, RegimePage, FactorPage, InstrumentsPage
        └── services/api.js          ← Axios calls
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://localhost:5432/msrap` | JDBC URL |
| `SPRING_DATASOURCE_USERNAME` | `msrap` | DB user |
| `SPRING_DATASOURCE_PASSWORD` | `msrap_secret` | DB password |
| `ANALYTICS_PYTHON_PATH` | `/app/analytics` | Absolute path to analytics directory |
| `ANALYTICS_PYTHON_URL` | `http://analytics:8000` | FastAPI service URL |
| `DB_HOST` | `localhost` | (Python workers) |
| `DB_PORT` | `5432` | (Python workers) |
| `DB_NAME` | `msrap` | (Python workers) |
| `DB_USER` | `msrap` | (Python workers) |
| `DB_PASSWORD` | `msrap_secret` | (Python workers) |

---

## Troubleshooting

**Backend won't start** — check DB is healthy: `docker compose logs timescaledb`

**No data showing in dashboard** — trigger a backfill: `curl -X POST http://localhost:8080/api/ingestion/backfill` then wait a few minutes.

**Python worker errors** — check the analytics container: `docker compose logs analytics`

**yfinance rate-limit / empty data** — NSE data via yfinance can be patchy for indices. Add a short delay between symbols in the backfill script (`--symbols` one at a time).

**HMM not converging** — the model needs at least ~100 data points after the 21-day warm-up. Ensure at least 6 months of OHLCV history is backfilled before running the regime worker.
