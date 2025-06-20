
-- test_cases definition

CREATE TABLE test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT,
    project_type TEXT,
    tcid TEXT,
    scenario TEXT,
    step_name TEXT,
    failure_reason TEXT,
    error TEXT,
    start_time TEXT,
    end_time TEXT,
    execution_time TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(100),
    execution_type VARCHAR
);
