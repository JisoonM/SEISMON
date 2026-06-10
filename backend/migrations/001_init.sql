CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TYPE earthquake_source AS ENUM ('PHIVOLCS', 'USGS', 'EMSC');
CREATE TYPE island_group AS ENUM ('Luzon', 'Visayas', 'Mindanao', 'Outside PH');
CREATE TYPE alert_level AS ENUM ('green', 'yellow', 'orange', 'red');
CREATE TYPE alert_channel AS ENUM ('push', 'sms', 'telegram', 'email');
CREATE TYPE alert_status AS ENUM ('sent', 'failed');

CREATE TABLE IF NOT EXISTS earthquakes (
    id UUID PRIMARY KEY,
    event_id TEXT NOT NULL,
    source earthquake_source NOT NULL,
    magnitude DOUBLE PRECISION NOT NULL,
    magnitude_type TEXT NOT NULL,
    depth_km DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    place TEXT NOT NULL,
    province TEXT,
    region TEXT,
    island_group island_group,
    felt BOOLEAN NOT NULL DEFAULT FALSE,
    tsunami_warning BOOLEAN NOT NULL DEFAULT FALSE,
    alert_level alert_level NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT uq_earthquakes_source_event_id UNIQUE (source, event_id)
);

SELECT create_hypertable(
    'earthquakes',
    'occurred_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS ix_earthquakes_occurred_at ON earthquakes (occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_earthquakes_magnitude ON earthquakes (magnitude DESC);
CREATE INDEX IF NOT EXISTS ix_earthquakes_province ON earthquakes (province);
CREATE INDEX IF NOT EXISTS ix_earthquakes_source ON earthquakes (source);

CREATE TABLE IF NOT EXISTS alert_log (
    id UUID PRIMARY KEY,
    earthquake_id UUID NOT NULL REFERENCES earthquakes(id) ON DELETE CASCADE,
    channel alert_channel NOT NULL,
    recipient TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status alert_status NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS ix_alert_log_earthquake_id ON alert_log (earthquake_id);
CREATE INDEX IF NOT EXISTS ix_alert_log_sent_at ON alert_log (sent_at DESC);

CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', occurred_at) AS bucket,
    COUNT(*) AS event_count,
    MAX(magnitude) AS max_magnitude,
    AVG(depth_km) AS avg_depth_km
FROM earthquakes
GROUP BY bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'hourly_stats',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_retention_policy('earthquakes', INTERVAL '90 days', if_not_exists => TRUE);
