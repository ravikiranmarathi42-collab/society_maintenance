-- Society Maintenance Management System Database Schema
PRAGMA foreign_keys = ON;

-- Users Table (Authentication and Authorization)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'resident')),
    full_name TEXT NOT NULL,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Flats Table (Apartment / Flat records)
CREATE TABLE IF NOT EXISTS flats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flat_number TEXT UNIQUE NOT NULL,
    building_block TEXT NOT NULL,
    floor INTEGER NOT NULL,
    flat_type TEXT NOT NULL, -- e.g., '1 BHK', '2 BHK', '3 BHK', '4 BHK'
    maintenance_rate REAL DEFAULT 2500.0,
    status TEXT NOT NULL DEFAULT 'Vacant' CHECK(status IN ('Vacant', 'Occupied')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Residents Table (Resident profiles connected to Flats and Users)
CREATE TABLE IF NOT EXISTS residents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    flat_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    joining_date DATE NOT NULL,
    emergency_contact TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (flat_id) REFERENCES flats(id) ON DELETE RESTRICT
);

-- Maintenance Bills Table
CREATE TABLE IF NOT EXISTS maintenance_bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_no TEXT UNIQUE NOT NULL,
    flat_id INTEGER NOT NULL,
    billing_month TEXT NOT NULL, -- Format: YYYY-MM
    amount REAL NOT NULL,
    due_date DATE NOT NULL,
    penalty REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Paid', 'Overdue')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flat_id) REFERENCES flats(id) ON DELETE CASCADE
);

-- Payments Table (Payment records, receipts)
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_no TEXT UNIQUE NOT NULL,
    bill_id INTEGER NOT NULL,
    resident_id INTEGER,
    amount REAL NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_method TEXT NOT NULL CHECK(payment_method IN ('UPI', 'Cash', 'Bank Transfer', 'Credit/Debit Card', 'Cheque')),
    transaction_id TEXT,
    remarks TEXT,
    status TEXT NOT NULL DEFAULT 'Success' CHECK(status IN ('Success', 'Failed', 'Pending')),
    FOREIGN KEY (bill_id) REFERENCES maintenance_bills(id) ON DELETE CASCADE,
    FOREIGN KEY (resident_id) REFERENCES residents(id) ON DELETE SET NULL
);

-- Complaints Table
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL,
    flat_id INTEGER NOT NULL,
    category TEXT NOT NULL, -- 'Water Supply', 'Electricity', 'Cleaning', 'Security', 'Parking', 'Lift / Elevator', 'Plumbing', 'Other'
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Emergency')),
    status TEXT NOT NULL DEFAULT 'Submitted' CHECK(status IN ('Submitted', 'In Progress', 'Resolved', 'Closed')),
    admin_remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (resident_id) REFERENCES residents(id) ON DELETE CASCADE,
    FOREIGN KEY (flat_id) REFERENCES flats(id) ON DELETE CASCADE
);

-- Notices Table (Society Announcements)
CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    category TEXT DEFAULT 'General' CHECK(category IN ('General', 'Maintenance', 'Meeting', 'Emergency', 'Event', 'Rule Update')),
    published_date DATE NOT NULL,
    expiry_date DATE,
    is_active INTEGER DEFAULT 1,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Society Expenses Table
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_no TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL, -- 'Cleaning & Housekeeping', 'Security Services', 'Electricity & Power', 'Repairs & Maintenance', 'Water Supply & Tanker', 'Gardening & Landscaping', 'Staff Salary', 'Lift AMC', 'Other'
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    expense_date DATE NOT NULL,
    paid_to TEXT NOT NULL,
    payment_method TEXT NOT NULL CHECK(payment_method IN ('Bank Transfer', 'UPI', 'Cheque', 'Cash')),
    receipt_ref TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Useful Indexes
CREATE INDEX IF NOT EXISTS idx_flats_number ON flats(flat_number);
CREATE INDEX IF NOT EXISTS idx_residents_flat ON residents(flat_id);
CREATE INDEX IF NOT EXISTS idx_residents_user ON residents(user_id);
CREATE INDEX IF NOT EXISTS idx_bills_flat ON maintenance_bills(flat_id);
CREATE INDEX IF NOT EXISTS idx_bills_status ON maintenance_bills(status);
CREATE INDEX IF NOT EXISTS idx_bills_month ON maintenance_bills(billing_month);
CREATE INDEX IF NOT EXISTS idx_payments_bill ON payments(bill_id);
CREATE INDEX IF NOT EXISTS idx_complaints_resident ON complaints(resident_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
