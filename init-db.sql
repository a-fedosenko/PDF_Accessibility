-- ========================================================================
-- PDF Accessibility Solutions - PostgreSQL Database Initialization
-- ========================================================================
-- This script creates the necessary tables and indexes for the on-premises
-- deployment of PDF Accessibility Solutions
-- ========================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================================================
-- Users Table
-- ========================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL,
    upload_quota INTEGER NOT NULL DEFAULT 100,
    uploads_used INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_quota_positive CHECK (upload_quota >= 0),
    CONSTRAINT chk_uploads_positive CHECK (uploads_used >= 0),
    CONSTRAINT chk_uploads_not_exceed_quota CHECK (uploads_used <= upload_quota OR upload_quota = -1)
);

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- ========================================================================
-- Jobs Table
-- ========================================================================
CREATE TABLE IF NOT EXISTS jobs (
    job_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    s3_key VARCHAR(1000) NOT NULL,
    result_s3_key VARCHAR(1000),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress DECIMAL(5,2) DEFAULT 0.00,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Foreign key
    CONSTRAINT fk_jobs_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT chk_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    CONSTRAINT chk_progress_range CHECK (progress >= 0 AND progress <= 100)
);

-- Indexes for jobs table
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_jobs_completed_at ON jobs(completed_at) WHERE completed_at IS NOT NULL;

-- ========================================================================
-- Job Steps Table (for tracking individual processing steps)
-- ========================================================================
CREATE TABLE IF NOT EXISTS job_steps (
    step_id SERIAL PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    step_order INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    metadata JSONB,

    -- Foreign key
    CONSTRAINT fk_job_steps_job FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT chk_step_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'skipped')),
    CONSTRAINT uq_job_step UNIQUE (job_id, step_name)
);

-- Indexes for job_steps table
CREATE INDEX IF NOT EXISTS idx_job_steps_job_id ON job_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_job_steps_status ON job_steps(status);

-- ========================================================================
-- API Keys Table (for programmatic access)
-- ========================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    api_key_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    -- Foreign key
    CONSTRAINT fk_api_keys_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes for api_keys table
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- ========================================================================
-- Usage Statistics Table
-- ========================================================================
CREATE TABLE IF NOT EXISTS usage_statistics (
    stat_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    uploads_count INTEGER NOT NULL DEFAULT 0,
    processing_time_ms BIGINT NOT NULL DEFAULT 0,
    storage_bytes BIGINT NOT NULL DEFAULT 0,
    api_calls INTEGER NOT NULL DEFAULT 0,

    -- Foreign key (nullable to allow system-wide stats)
    CONSTRAINT fk_usage_statistics_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,

    -- Unique constraint
    CONSTRAINT uq_user_date UNIQUE (user_id, date)
);

-- Indexes for usage_statistics table
CREATE INDEX IF NOT EXISTS idx_usage_statistics_user_id ON usage_statistics(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_statistics_date ON usage_statistics(date DESC);

-- ========================================================================
-- System Configuration Table
-- ========================================================================
CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR(255) PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Insert default configuration values
INSERT INTO system_config (config_key, config_value, description) VALUES
    ('default_upload_quota', '100', 'Default upload quota for new users'),
    ('max_file_size_mb', '100', 'Maximum PDF file size in MB'),
    ('job_retention_days', '90', 'Number of days to keep completed job records'),
    ('enable_auto_cleanup', 'true', 'Enable automatic cleanup of old jobs'),
    ('maintenance_mode', 'false', 'Enable maintenance mode')
ON CONFLICT (config_key) DO NOTHING;

-- ========================================================================
-- Audit Log Table (for security and compliance)
-- ========================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key (nullable for system actions)
    CONSTRAINT fk_audit_log_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- Indexes for audit_log table
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- ========================================================================
-- Functions and Triggers
-- ========================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for users table
DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for jobs table
DROP TRIGGER IF EXISTS trigger_jobs_updated_at ON jobs;
CREATE TRIGGER trigger_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate job duration
CREATE OR REPLACE FUNCTION calculate_job_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND NEW.completed_at IS NULL THEN
        NEW.completed_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to set completed_at timestamp
DROP TRIGGER IF EXISTS trigger_jobs_completion ON jobs;
CREATE TRIGGER trigger_jobs_completion
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    WHEN (NEW.status IN ('completed', 'failed', 'cancelled'))
    EXECUTE FUNCTION calculate_job_duration();

-- ========================================================================
-- Views
-- ========================================================================

-- View for active jobs
CREATE OR REPLACE VIEW active_jobs AS
SELECT
    j.job_id,
    j.user_id,
    u.email,
    u.username,
    j.filename,
    j.status,
    j.progress,
    j.created_at,
    j.updated_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - j.created_at)) AS age_seconds
FROM jobs j
JOIN users u ON j.user_id = u.user_id
WHERE j.status IN ('pending', 'processing')
ORDER BY j.created_at ASC;

-- View for user statistics
CREATE OR REPLACE VIEW user_stats AS
SELECT
    u.user_id,
    u.email,
    u.username,
    u.upload_quota,
    u.uploads_used,
    COUNT(j.job_id) AS total_jobs,
    COUNT(CASE WHEN j.status = 'completed' THEN 1 END) AS completed_jobs,
    COUNT(CASE WHEN j.status = 'failed' THEN 1 END) AS failed_jobs,
    AVG(EXTRACT(EPOCH FROM (j.completed_at - j.created_at))) AS avg_processing_time_seconds
FROM users u
LEFT JOIN jobs j ON u.user_id = j.user_id
GROUP BY u.user_id, u.email, u.username, u.upload_quota, u.uploads_used;

-- View for system health metrics
CREATE OR REPLACE VIEW system_health AS
SELECT
    (SELECT COUNT(*) FROM jobs WHERE status = 'pending') AS pending_jobs,
    (SELECT COUNT(*) FROM jobs WHERE status = 'processing') AS processing_jobs,
    (SELECT COUNT(*) FROM jobs WHERE status = 'failed' AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour') AS recent_failures,
    (SELECT COUNT(DISTINCT user_id) FROM jobs WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours') AS active_users_24h,
    (SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at)))
     FROM jobs
     WHERE status = 'completed'
     AND completed_at > CURRENT_TIMESTAMP - INTERVAL '1 hour') AS avg_processing_time_1h;

-- ========================================================================
-- Initial Admin User (optional - comment out if using Keycloak)
-- ========================================================================
-- INSERT INTO users (user_id, email, username, upload_quota, is_admin)
-- VALUES ('admin', 'admin@example.com', 'admin', -1, TRUE)
-- ON CONFLICT (user_id) DO NOTHING;

-- ========================================================================
-- Grants and Permissions
-- ========================================================================
-- Grant permissions to the application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pdfuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pdfuser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO pdfuser;

-- ========================================================================
-- Database Maintenance Functions
-- ========================================================================

-- Function to cleanup old completed jobs
CREATE OR REPLACE FUNCTION cleanup_old_jobs(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM jobs
    WHERE status IN ('completed', 'failed', 'cancelled')
    AND completed_at < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update usage statistics
CREATE OR REPLACE FUNCTION update_usage_statistics()
RETURNS void AS $$
BEGIN
    INSERT INTO usage_statistics (user_id, date, uploads_count, processing_time_ms, api_calls)
    SELECT
        user_id,
        CURRENT_DATE,
        COUNT(*),
        SUM(EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000)::BIGINT,
        COUNT(*)
    FROM jobs
    WHERE DATE(created_at) = CURRENT_DATE
    GROUP BY user_id
    ON CONFLICT (user_id, date)
    DO UPDATE SET
        uploads_count = EXCLUDED.uploads_count,
        processing_time_ms = EXCLUDED.processing_time_ms,
        api_calls = EXCLUDED.api_calls;
END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- Completion Message
-- ========================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ PDF Accessibility database initialized successfully!';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - users';
    RAISE NOTICE '  - jobs';
    RAISE NOTICE '  - job_steps';
    RAISE NOTICE '  - api_keys';
    RAISE NOTICE '  - usage_statistics';
    RAISE NOTICE '  - system_config';
    RAISE NOTICE '  - audit_log';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - active_jobs';
    RAISE NOTICE '  - user_stats';
    RAISE NOTICE '  - system_health';
END $$;
