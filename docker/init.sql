-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ─────────────────────────────────────────
-- MARKET DATA TABLES
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS equity_ohlcv (
    symbol        VARCHAR(32)     NOT NULL,
    ts            TIMESTAMPTZ     NOT NULL,
    open          DECIMAL(18, 4)  NOT NULL,
    high          DECIMAL(18, 4)  NOT NULL,
    low           DECIMAL(18, 4)  NOT NULL,
    close         DECIMAL(18, 4)  NOT NULL,
    volume        BIGINT          NOT NULL,
    adj_close     DECIMAL(18, 4),
    interval      VARCHAR(8)      NOT NULL DEFAULT '1d',
    PRIMARY KEY (symbol, ts, interval)
);

SELECT create_hypertable('equity_ohlcv', 'ts',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_ts ON equity_ohlcv (symbol, ts DESC);

-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS options_chain (
    symbol        VARCHAR(32)     NOT NULL,
    ts            TIMESTAMPTZ     NOT NULL,
    expiry        DATE            NOT NULL,
    strike        DECIMAL(18, 2)  NOT NULL,
    option_type   CHAR(2)         NOT NULL,  -- CE or PE
    last_price    DECIMAL(18, 4),
    bid           DECIMAL(18, 4),
    ask           DECIMAL(18, 4),
    volume        BIGINT,
    open_interest BIGINT,
    iv            DECIMAL(10, 6),
    delta         DECIMAL(10, 6),
    gamma         DECIMAL(10, 6),
    theta         DECIMAL(10, 6),
    vega          DECIMAL(10, 6),
    PRIMARY KEY (symbol, ts, expiry, strike, option_type)
);

SELECT create_hypertable('options_chain', 'ts',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_options_symbol_expiry ON options_chain (symbol, expiry, ts DESC);

-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS futures_oi (
    symbol            VARCHAR(32)     NOT NULL,
    ts                TIMESTAMPTZ     NOT NULL,
    expiry            DATE            NOT NULL,
    open_interest     BIGINT,
    oi_change         BIGINT,
    volume            BIGINT,
    settlement_price  DECIMAL(18, 4),
    basis             DECIMAL(18, 4),
    PRIMARY KEY (symbol, ts, expiry)
);

SELECT create_hypertable('futures_oi', 'ts',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE);

-- ─────────────────────────────────────────
-- ANALYTICS RESULTS TABLE (generic KV store per module)
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analytics_results (
    symbol    VARCHAR(32)     NOT NULL,
    ts        TIMESTAMPTZ     NOT NULL,
    module    VARCHAR(32)     NOT NULL,  -- volatility | regime | factor
    metric    VARCHAR(64)     NOT NULL,
    value     DECIMAL(24, 8),
    value_str TEXT,
    PRIMARY KEY (symbol, ts, module, metric)
);

SELECT create_hypertable('analytics_results', 'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_analytics_symbol_module ON analytics_results (symbol, module, ts DESC);

-- ─────────────────────────────────────────
-- REGIME STATE TABLE
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS regime_states (
    symbol        VARCHAR(32)     NOT NULL,
    ts            TIMESTAMPTZ     NOT NULL,
    state         SMALLINT        NOT NULL,  -- 0=low-vol, 1=trending, 2=high-vol
    state_label   VARCHAR(32),
    prob_state0   DECIMAL(8, 6),
    prob_state1   DECIMAL(8, 6),
    prob_state2   DECIMAL(8, 6),
    PRIMARY KEY (symbol, ts)
);

SELECT create_hypertable('regime_states', 'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE);

-- ─────────────────────────────────────────
-- FACTOR LOADINGS TABLE
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS factor_loadings (
    symbol        VARCHAR(32)     NOT NULL,
    ts            TIMESTAMPTZ     NOT NULL,
    window_days   SMALLINT        NOT NULL DEFAULT 252,
    beta_market   DECIMAL(10, 6),
    beta_size     DECIMAL(10, 6),
    beta_value    DECIMAL(10, 6),
    beta_momentum DECIMAL(10, 6),
    beta_quality  DECIMAL(10, 6),
    alpha         DECIMAL(10, 6),
    r_squared     DECIMAL(8, 6),
    residual_vol  DECIMAL(10, 6),
    PRIMARY KEY (symbol, ts, window_days)
);

SELECT create_hypertable('factor_loadings', 'ts',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE);

-- ─────────────────────────────────────────
-- WATCHLIST & METADATA
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS instruments (
    symbol        VARCHAR(32)     PRIMARY KEY,
    name          VARCHAR(128),
    exchange      VARCHAR(16),
    asset_class   VARCHAR(16),    -- equity | futures | options | index
    sector        VARCHAR(64),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id            SERIAL PRIMARY KEY,
    symbol        VARCHAR(32),
    ts            TIMESTAMPTZ DEFAULT NOW(),
    status        VARCHAR(16),   -- success | error | partial
    rows_inserted INTEGER,
    message       TEXT
);

-- ─────────────────────────────────────────
-- SEED INSTRUMENTS
-- ─────────────────────────────────────────

INSERT INTO instruments (symbol, name, exchange, asset_class, sector) VALUES
    ('RELIANCE.NS',   'Reliance Industries',      'NSE', 'equity', 'Energy'),
    ('TCS.NS',        'Tata Consultancy Services', 'NSE', 'equity', 'Technology'),
    ('INFY.NS',       'Infosys',                   'NSE', 'equity', 'Technology'),
    ('HDFCBANK.NS',   'HDFC Bank',                 'NSE', 'equity', 'Financials'),
    ('ICICIBANK.NS',  'ICICI Bank',                'NSE', 'equity', 'Financials'),
    ('SBIN.NS',       'State Bank of India',       'NSE', 'equity', 'Financials'),
    ('BHARTIARTL.NS', 'Bharti Airtel',             'NSE', 'equity', 'Telecom'),
    ('ITC.NS',        'ITC Limited',               'NSE', 'equity', 'FMCG'),
    ('KOTAKBANK.NS',  'Kotak Mahindra Bank',       'NSE', 'equity', 'Financials'),
    ('LT.NS',         'Larsen & Toubro',           'NSE', 'equity', 'Industrials'),
    ('AXISBANK.NS',   'Axis Bank',                 'NSE', 'equity', 'Financials'),
    ('BAJFINANCE.NS', 'Bajaj Finance',             'NSE', 'equity', 'Financials'),
    ('HINDUNILVR.NS', 'Hindustan Unilever',        'NSE', 'equity', 'FMCG'),
    ('WIPRO.NS',      'Wipro',                     'NSE', 'equity', 'Technology'),
    ('MARUTI.NS',     'Maruti Suzuki',             'NSE', 'equity', 'Automobile'),
    ('^NSEI',         'Nifty 50 Index',            'NSE', 'index',  NULL),
    ('^NSEBANK',      'Nifty Bank Index',          'NSE', 'index',  NULL)
ON CONFLICT (symbol) DO NOTHING;

-- Retention policy: keep raw OHLCV for 5 years
SELECT add_retention_policy('equity_ohlcv', INTERVAL '5 years', if_not_exists => TRUE);
SELECT add_retention_policy('options_chain', INTERVAL '2 years', if_not_exists => TRUE);
SELECT add_retention_policy('analytics_results', INTERVAL '5 years', if_not_exists => TRUE);
