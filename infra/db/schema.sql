-- Market State & Risk Analytics Platform (MSRAP)
-- Database schema (PostgreSQL + TimescaleDB)

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- =========================
-- EQUITY PRICES
-- =========================
CREATE TABLE equity_prices (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    PRIMARY KEY (trade_date, symbol)
);

SELECT create_hypertable('equity_prices', 'trade_date', if_not_exists => TRUE);

-- =========================
-- INDEX PRICES
-- =========================
CREATE TABLE index_prices (
    trade_date DATE NOT NULL,
    index_name TEXT NOT NULL,
    close NUMERIC,
    returns NUMERIC,
    PRIMARY KEY (trade_date, index_name)
);

SELECT create_hypertable('index_prices', 'trade_date', if_not_exists => TRUE);

-- =========================
-- FUTURES DATA
-- =========================
CREATE TABLE futures_data (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    expiry DATE NOT NULL,
    close NUMERIC,
    volume BIGINT,
    open_interest BIGINT,
    PRIMARY KEY (trade_date, symbol, expiry)
);

SELECT create_hypertable('futures_data', 'trade_date', if_not_exists => TRUE);

-- =========================
-- OPTIONS DATA
-- =========================
CREATE TABLE options_data (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    expiry DATE NOT NULL,
    strike NUMERIC NOT NULL,
    option_type CHAR(1) NOT NULL,
    close NUMERIC,
    implied_vol NUMERIC,
    open_interest BIGINT,
    oi_change BIGINT,
    volume BIGINT,
    PRIMARY KEY (trade_date, symbol, expiry, strike, option_type)
);

SELECT create_hypertable('options_data', 'trade_date', if_not_exists => TRUE);

-- =========================
-- DERIVED MARKET STATES
-- =========================
CREATE TABLE market_states (
    trade_date DATE NOT NULL,
    market TEXT NOT NULL,
    model TEXT NOT NULL,
    state_label TEXT NOT NULL,
    probability NUMERIC,
    PRIMARY KEY (trade_date, market, model)
);

SELECT create_hypertable('market_states', 'trade_date', if_not_exists => TRUE);

