-- G.N. Enterprises Inventory & Billing Schema v2 (SAMPLE PROJECT - dummy data only)

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'staff')),
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    username TEXT,
    action   TEXT NOT NULL,
    detail   TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    phone       TEXT,
    email       TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name   TEXT NOT NULL,
    category_id    INTEGER REFERENCES categories(category_id),
    supplier_id    INTEGER REFERENCES suppliers(supplier_id),
    unit_price     REAL NOT NULL CHECK (unit_price >= 0),
    gst_rate       REAL NOT NULL DEFAULT 18 CHECK (gst_rate >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    phone       TEXT,
    gstin       TEXT,
    address     TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no     TEXT UNIQUE,                         -- e.g. GN/2026-27/00012
    customer_id    INTEGER NOT NULL REFERENCES customers(customer_id),
    invoice_date   TEXT NOT NULL,                       -- 'YYYY-MM-DD HH:MM:SS'
    subtotal       REAL NOT NULL DEFAULT 0,             -- before GST
    gst_total      REAL NOT NULL DEFAULT 0,
    total_amount   REAL NOT NULL DEFAULT 0,             -- subtotal + gst_total
    payment_status TEXT NOT NULL DEFAULT 'Pending'
                   CHECK (payment_status IN ('Paid', 'Pending', 'Cancelled'))
);

CREATE TABLE IF NOT EXISTS invoice_items (
    item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(invoice_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL,
    gst_rate   REAL NOT NULL,
    line_total REAL NOT NULL,                           -- quantity * unit_price (before GST)
    gst_amount REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    po_no       TEXT UNIQUE,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(supplier_id),
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'Draft'
                CHECK (status IN ('Draft', 'Ordered', 'Received', 'Cancelled')),
    received_at TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    po_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id      INTEGER NOT NULL REFERENCES purchase_orders(po_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost  REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_items_invoice ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON invoice_items(product_id);
CREATE INDEX IF NOT EXISTS idx_po_items_po   ON purchase_order_items(po_id);
