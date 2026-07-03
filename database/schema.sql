-- SQLite Schema for Business Guardian AI Database
-- Schema version 1.0

-- Table 1: products (Product catalog)
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    sku TEXT,
    unit_cost REAL NOT NULL,
    unit_price REAL NOT NULL,
    reorder_point INTEGER NOT NULL,
    reorder_quantity INTEGER NOT NULL,
    supplier_id TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Table 2: inventory (Current stock levels)
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    current_stock INTEGER NOT NULL,
    warehouse_location TEXT,
    last_updated TEXT NOT NULL,
    recorded_by TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);

-- Table 3: sales (Sales transactions)
CREATE TABLE IF NOT EXISTS sales (
    sale_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    quantity_sold INTEGER NOT NULL,
    sale_amount REAL NOT NULL,
    unit_price_at_sale REAL NOT NULL,
    sale_date TEXT NOT NULL,
    channel TEXT,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);

-- Table 4: expenses (Business expenses)
CREATE TABLE IF NOT EXISTS expenses (
    expense_id TEXT PRIMARY KEY,
    expense_category TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    expense_date TEXT NOT NULL,
    vendor TEXT,
    recorded_at TEXT NOT NULL
);

-- Table 5: suppliers (Supplier records)
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    contact_name TEXT,
    contact_email TEXT,
    country TEXT NOT NULL,
    product_categories TEXT NOT NULL,
    dependency_percentage REAL,
    contract_start_date TEXT,
    contract_end_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Table 6: compliance_events (Compliance deadlines and obligations)
CREATE TABLE IF NOT EXISTS compliance_events (
    event_id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    due_date TEXT NOT NULL,
    description TEXT,
    responsible_party TEXT,
    status TEXT NOT NULL,
    recurrence TEXT,
    created_at TEXT NOT NULL
);

-- Table 7: risk_scores (Stored risk scores from agents)
CREATE TABLE IF NOT EXISTS risk_scores (
    score_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    score_type TEXT NOT NULL,
    score_value INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

-- Table 8: reports (Generated analysis reports)
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    business_id TEXT NOT NULL,
    business_name TEXT NOT NULL,
    report_type TEXT NOT NULL,
    content TEXT NOT NULL,
    system_status TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

-- Table 9: audit_logs (System audit logs)
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    agent_name TEXT,
    input_payload TEXT,
    output_payload TEXT,
    status TEXT NOT NULL,
    error_code TEXT,
    duration_ms INTEGER,
    timestamp TEXT NOT NULL
);
