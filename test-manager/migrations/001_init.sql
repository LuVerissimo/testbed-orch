CREATE TABLE test_jobs (
    id UUID PRIMARY KEY,
    device_id TEXT NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE test_results (
    id SERIAL PRIMARY KEY, 
    job_id uuid REFERENCES test_jobs(id) ON DELETE RESTRICT, 
    exit_code int, 
    stdout VARCHAR, 
    stderr VARCHAR, 
    duration_ms INT, 
    completed_at TIMESTAMPTZ DEFAULT NOW()
);


CREATE INDEX idx_test_results_job_id ON test_results (job_id);
CREATE INDEX idx_test_jobs_status ON test_jobs (status);