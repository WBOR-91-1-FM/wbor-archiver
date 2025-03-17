------------------------------------------------------------
-- 1) Segments table
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS segments (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,        -- e.g. "WBOR-2025-02-14T00:35:01Z.mp3"
    archived_path TEXT NOT NULL,         -- Full path where file is stored
    start_ts TIMESTAMPTZ NOT NULL,       -- When this recording started
    end_ts TIMESTAMPTZ,                  -- When this recording ended (if known)
    is_published BOOLEAN NOT NULL DEFAULT TRUE,   -- Mark hidden/un-published as needed
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

------------------------------------------------------------
-- 2) Download / playback logs
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS download_logs (
    id SERIAL PRIMARY KEY,
    segment_id INT NOT NULL REFERENCES segments(id),
    downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address TEXT,
    user_agent TEXT
);

------------------------------------------------------------
-- 3) Auto-update 'updated_at' on changes
------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_segments_modtime
BEFORE UPDATE ON segments
FOR EACH ROW
EXECUTE PROCEDURE update_timestamp_column();