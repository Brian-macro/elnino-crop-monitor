
CREATE TABLE IF NOT EXISTS source_documents (
 document_id VARCHAR PRIMARY KEY, source VARCHAR, source_url VARCHAR, raw_path VARCHAR,
 sha256 VARCHAR, publication_date DATE, available_date DATE, download_timestamp TIMESTAMP,
 publication_date_basis VARCHAR, title VARCHAR, UNIQUE(source, source_url, sha256));
CREATE TABLE IF NOT EXISTS actual_production (record_id VARCHAR PRIMARY KEY, document_id VARCHAR NOT NULL,
 crop VARCHAR NOT NULL, country VARCHAR NOT NULL, region VARCHAR NOT NULL DEFAULT '',
 target_year INTEGER NOT NULL, year_basis VARCHAR NOT NULL, commodity_basis VARCHAR NOT NULL,
 metric VARCHAR NOT NULL, value DOUBLE NOT NULL CHECK(isfinite(value) AND value >= 0), unit VARCHAR NOT NULL,
 source VARCHAR NOT NULL, publication_date DATE, available_date DATE NOT NULL,
 download_timestamp TIMESTAMP NOT NULL, methodology VARCHAR NOT NULL, source_url VARCHAR NOT NULL);
CREATE TABLE IF NOT EXISTS forecast_production (record_id VARCHAR PRIMARY KEY, document_id VARCHAR NOT NULL,
 crop VARCHAR NOT NULL, country VARCHAR NOT NULL, region VARCHAR NOT NULL DEFAULT '',
 target_year INTEGER NOT NULL, year_basis VARCHAR NOT NULL, commodity_basis VARCHAR NOT NULL,
 metric VARCHAR NOT NULL, value DOUBLE NOT NULL CHECK(isfinite(value) AND value >= 0), unit VARCHAR NOT NULL,
 source VARCHAR NOT NULL, publication_date DATE, available_date DATE NOT NULL,
 download_timestamp TIMESTAMP NOT NULL, methodology VARCHAR NOT NULL, source_url VARCHAR NOT NULL);
CREATE TABLE IF NOT EXISTS estimated_production (record_id VARCHAR PRIMARY KEY, document_id VARCHAR NOT NULL,
 crop VARCHAR NOT NULL, country VARCHAR NOT NULL, region VARCHAR NOT NULL DEFAULT '',
 target_year INTEGER NOT NULL, year_basis VARCHAR NOT NULL, commodity_basis VARCHAR NOT NULL,
 metric VARCHAR NOT NULL, value DOUBLE NOT NULL CHECK(isfinite(value) AND value >= 0), unit VARCHAR NOT NULL,
 source VARCHAR NOT NULL, publication_date DATE, available_date DATE NOT NULL,
 download_timestamp TIMESTAMP NOT NULL, methodology VARCHAR NOT NULL, source_url VARCHAR NOT NULL);
CREATE TABLE IF NOT EXISTS climate (
 record_id VARCHAR PRIMARY KEY, document_id VARCHAR, index_name VARCHAR, date DATE,
 season VARCHAR, value DOUBLE, unit VARCHAR, source VARCHAR, available_date DATE);
CREATE TABLE IF NOT EXISTS prices (
 record_id VARCHAR PRIMARY KEY, document_id VARCHAR, crop VARCHAR, market VARCHAR,
 symbol VARCHAR, date DATE, value DOUBLE CHECK(value > 0), currency VARCHAR, unit VARCHAR,
 price_type VARCHAR, source VARCHAR, available_date DATE);
CREATE TABLE IF NOT EXISTS futures_prices (
 record_id VARCHAR PRIMARY KEY, document_id VARCHAR NOT NULL, series_id VARCHAR NOT NULL,
 crop VARCHAR, market VARCHAR, symbol VARCHAR, date DATE,
 open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE CHECK(isfinite(close) AND close > 0),
 volume DOUBLE, open_interest DOUBLE, settlement DOUBLE, usable BOOLEAN,
 currency VARCHAR, unit VARCHAR, commodity_basis VARCHAR, source VARCHAR,
 available_date DATE, roll_method VARCHAR);
CREATE TABLE IF NOT EXISTS regions (
 country VARCHAR, region VARCHAR, parent_region VARCHAR, latitude DOUBLE, longitude DOUBLE,
 source_url VARCHAR, PRIMARY KEY(country,region));
CREATE TABLE IF NOT EXISTS crop_calendar (
 crop VARCHAR, country VARCHAR, region VARCHAR, stage VARCHAR, start_month INTEGER,
 end_month INTEGER, source_url VARCHAR, publication_date DATE);
CREATE TABLE IF NOT EXISTS source_metadata (
 source VARCHAR PRIMARY KEY, last_checked TIMESTAMP, last_success TIMESTAMP,
 last_publication_date DATE, latest_observation_date DATE, status VARCHAR, error VARCHAR,
 rows_ingested BIGINT DEFAULT 0);
CREATE VIEW IF NOT EXISTS production_all AS
 SELECT *, 'actual' AS status FROM actual_production UNION ALL
 SELECT *, 'forecast' AS status FROM forecast_production UNION ALL
 SELECT *, 'estimate' AS status FROM estimated_production;
CREATE VIEW IF NOT EXISTS forecast_vintage AS
 SELECT *, available_date AS forecast_date, value AS forecast_value,
 DENSE_RANK() OVER (PARTITION BY crop,country,region,target_year,source,year_basis,commodity_basis,metric
 ORDER BY available_date,download_timestamp,document_id) AS revision_number
 FROM forecast_production;
