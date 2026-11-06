import sqlite3
import os
from pathlib import Path
from flask import g, current_app
from werkzeug.security import generate_password_hash
from config import Config

def get_db():
    """Get database connection for current request context or create a new one."""
    try:
        if 'db' not in g:
            g.db = sqlite3.connect(Config.DATABASE)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON;")
        return g.db
    except RuntimeError:
        # Fallback when outside application context
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

def close_db(e=None):
    """Close the database connection if open."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Convenience helper to query the database and fetch results as dicts."""
    db = get_db()
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (dict(rv[0]) if rv else None) if one else [dict(r) for r in rv]

def execute_db(query, args=()):
    """Execute an INSERT/UPDATE/DELETE query and commit."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    row_count = cur.rowcount
    cur.close()
    return last_id, row_count

def init_db():
    base_dir = Path(__file__).resolve().parent.parent

    possible_paths = [
        base_dir / "database" / "schema.sql",
        base_dir / "schema.sql",
        base_dir.parent / "database" / "schema.sql",
        base_dir.parent / "database" / "society_management.sql"
    ]

    schema_path = next(
        (path for path in possible_paths if path.is_file()),
        None
    )

    if schema_path is None:
        raise FileNotFoundError(
            "Database schema file not found. Checked:\n" +
            "\n".join(str(path) for path in possible_paths)
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()

    # Keep the remaining existing database initialization
    # code below this point unchanged.

def seed_sample_data(db):
    """Seed comprehensive sample records for presentation and testing."""
    print("Seeding initial sample data for Society Maintenance Management System...")
    
    # 1. Seed Users
    # Admin
    admin_pw = generate_password_hash("admin123")
    res1_pw = generate_password_hash("resident123")
    res2_pw = generate_password_hash("resident123")
    res3_pw = generate_password_hash("resident123")
    
    db.execute("""
        INSERT INTO users (username, email, password_hash, role, full_name, phone)
        VALUES 
        ('admin', 'admin@greenfield.com', ?, 'admin', 'Society Administrator', '+91 98765 00001'),
        ('resident1', 'rajesh.sharma@example.com', ?, 'resident', 'Rajesh Sharma', '+91 98201 12233'),
        ('priya', 'priya.patel@example.com', ?, 'resident', 'Priya Patel', '+91 98202 23344'),
        ('vikram', 'vikram.singh@example.com', ?, 'resident', 'Vikram Singh', '+91 98203 34455')
    """, (admin_pw, res1_pw, res2_pw, res3_pw))
    
    # 2. Seed Flats
    db.execute("""
        INSERT INTO flats (flat_number, building_block, floor, flat_type, maintenance_rate, status)
        VALUES
        ('A-101', 'A', 1, '2 BHK', 3000.0, 'Occupied'),
        ('A-102', 'A', 1, '2 BHK', 3000.0, 'Occupied'),
        ('A-201', 'A', 2, '3 BHK', 4500.0, 'Occupied'),
        ('A-202', 'A', 2, '3 BHK', 4500.0, 'Vacant'),
        ('B-101', 'B', 1, '1 BHK', 2000.0, 'Vacant'),
        ('B-102', 'B', 1, '2 BHK', 3000.0, 'Vacant'),
        ('B-201', 'B', 2, '3 BHK', 4500.0, 'Vacant'),
        ('C-301', 'C', 3, 'Penthouse', 6500.0, 'Vacant')
    """)
    
    # 3. Seed Residents
    # Fetch user IDs
    users = {row['username']: row['id'] for row in db.execute("SELECT id, username FROM users").fetchall()}
    flats = {row['flat_number']: row['id'] for row in db.execute("SELECT id, flat_number FROM flats").fetchall()}
    
    db.execute("""
        INSERT INTO residents (user_id, flat_id, full_name, phone, email, joining_date, emergency_contact, status)
        VALUES
        (?, ?, 'Rajesh Sharma', '+91 98201 12233', 'rajesh.sharma@example.com', '2024-01-15', 'Sunita Sharma (+91 98201 99999)', 'Active'),
        (?, ?, 'Priya Patel', '+91 98202 23344', 'priya.patel@example.com', '2024-03-10', 'Kishore Patel (+91 98202 88888)', 'Active'),
        (?, ?, 'Vikram Singh', '+91 98203 34455', 'vikram.singh@example.com', '2023-11-01', 'Anita Singh (+91 98203 77777)', 'Active')
    """, (
        users['resident1'], flats['A-101'],
        users['priya'], flats['A-102'],
        users['vikram'], flats['A-201']
    ))
    
    residents = {row['full_name']: row['id'] for row in db.execute("SELECT id, full_name FROM residents").fetchall()}
    
    # 4. Seed Maintenance Bills
    # For A-101: 2026-09 (Paid), 2026-10 (Pending)
    # For A-102: 2026-09 (Paid), 2026-10 (Paid)
    # For A-201: 2026-08 (Paid), 2026-09 (Paid), 2026-10 (Overdue)
    db.execute("""
        INSERT INTO maintenance_bills (bill_no, flat_id, billing_month, amount, due_date, penalty, status, notes)
        VALUES
        ('BILL-202609-01', ?, '2026-09', 3000.0, '2026-09-15', 0.0, 'Paid', 'Regular monthly maintenance bill'),
        ('BILL-202610-01', ?, '2026-10', 3000.0, '2026-10-15', 0.0, 'Pending', 'Regular monthly maintenance bill'),
        ('BILL-202609-02', ?, '2026-09', 3000.0, '2026-09-15', 0.0, 'Paid', 'Regular monthly maintenance bill'),
        ('BILL-202610-02', ?, '2026-10', 3000.0, '2026-10-15', 0.0, 'Paid', 'Regular monthly maintenance bill'),
        ('BILL-202608-03', ?, '2026-08', 4500.0, '2026-08-15', 0.0, 'Paid', 'Regular monthly maintenance bill'),
        ('BILL-202609-03', ?, '2026-09', 4500.0, '2026-09-15', 0.0, 'Paid', 'Regular monthly maintenance bill'),
        ('BILL-202610-03', ?, '2026-10', 4500.0, '2026-10-10', 250.0, 'Overdue', 'Overdue with ₹250 late fee penalty')
    """, (
        flats['A-101'], flats['A-101'],
        flats['A-102'], flats['A-102'],
        flats['A-201'], flats['A-201'], flats['A-201']
    ))
    
    bills = {row['bill_no']: row['id'] for row in db.execute("SELECT id, bill_no FROM maintenance_bills").fetchall()}
    
    # 5. Seed Payments
    db.execute("""
        INSERT INTO payments (receipt_no, bill_id, resident_id, amount, payment_date, payment_method, transaction_id, remarks, status)
        VALUES
        ('RCT-202609-1001', ?, ?, 3000.0, '2026-09-10 14:22:10', 'UPI', 'UPI/260910084721/YESB', 'Online UPI payment via PhonePe', 'Success'),
        ('RCT-202609-1002', ?, ?, 3000.0, '2026-09-12 11:15:45', 'Credit/Debit Card', 'TXN_CARD_9921448', 'Paid via Visa Debit Card', 'Success'),
        ('RCT-202610-1003', ?, ?, 3000.0, '2026-10-05 16:40:00', 'Bank Transfer', 'NEFT-HDFC-991208', 'NEFT Bank Transfer from HDFC account', 'Success'),
        ('RCT-202608-1004', ?, ?, 4500.0, '2026-08-11 10:05:30', 'UPI', 'UPI/260811092831/ICIC', 'Google Pay payment', 'Success'),
        ('RCT-202609-1005', ?, ?, 4500.0, '2026-09-14 18:30:12', 'Cheque', 'CHQ#448921-SBI', 'Cheque cleared in society bank account', 'Success')
    """, (
        bills['BILL-202609-01'], residents['Rajesh Sharma'],
        bills['BILL-202609-02'], residents['Priya Patel'],
        bills['BILL-202610-02'], residents['Priya Patel'],
        bills['BILL-202608-03'], residents['Vikram Singh'],
        bills['BILL-202609-03'], residents['Vikram Singh']
    ))
    
    # 6. Seed Complaints
    db.execute("""
        INSERT INTO complaints (resident_id, flat_id, category, subject, description, priority, status, admin_remarks, created_at, resolved_at)
        VALUES
        (?, ?, 'Plumbing', 'Water leakage from master bathroom ceiling', 'There is continuous dampness and slow water leakage coming from the bathroom ceiling of flat A-101.', 'High', 'In Progress', 'Plumber assigned (Shri Ramesh Kumar). Inspection scheduled for today at 4:30 PM.', '2026-10-22 09:15:00', NULL),
        (?, ?, 'Lift / Elevator', 'Passenger Lift #1 jerking motion between 1st & 2nd floor', 'Passenger Lift in Block A makes a grinding sound and sudden jerk when decelerating on Floor 2.', 'Medium', 'Resolved', 'AMC technician inspected and calibrated the speed governor and safety shoes. Test certified.', '2026-10-18 11:30:00', '2026-10-19 16:00:00'),
        (?, ?, 'Security', 'Unregistered vehicles parked in reserved visitor bay #4', 'Unknown vehicles are regularly parked in Bay #4 blocking resident car parking access.', 'Low', 'Submitted', 'Noted. Security guard instructed to strictly issue visitor tokens and wheel-lock violators.', '2026-10-23 17:45:00', NULL)
    """, (
        residents['Rajesh Sharma'], flats['A-101'],
        residents['Vikram Singh'], flats['A-201'],
        residents['Priya Patel'], flats['A-102']
    ))
    
    # 7. Seed Notices
    admin_id = users['admin']
    db.execute("""
        INSERT INTO notices (title, message, category, published_date, expiry_date, is_active, created_by)
        VALUES
        ('Annual General Body Meeting (AGM) Notice', 'The Annual General Body Meeting for the financial year will be held on Sunday, November 15, 2026, at 10:30 AM in the Society Club House. All members are requested to attend promptly. Agenda includes approval of audited accounts and election of managing committee.', 'Meeting', '2026-10-20', '2026-11-16', 1, ?),
        ('Underground Water Tank Cleaning & Maintenance', 'Please be advised that the underground and overhead water tanks will undergo comprehensive mechanized pressure cleaning on Wednesday from 9:00 AM to 3:00 PM. Water supply will remain suspended during this window. Residents are advised to store sufficient water in advance.', 'Maintenance', '2026-10-22', '2026-10-29', 1, ?),
        ('Deepavali Society Cultural Evening & Dinner', 'Greenfield Heights invites all residents and families to the Deepavali Milan 2026 on Friday evening, 6:30 PM onwards at the central lawn. Cultural dance performances, musical night, and buffet dinner arranged.', 'Event', '2026-10-24', '2026-11-05', 1, ?),
        ('Visitor Parking & Gate Entry RFID Sticker Guidelines', 'All flat owners and tenants must collect the newly introduced RFID windshield stickers for vehicles from the society office before end of this month to ensure swift automated boom-barrier entry.', 'Rule Update', '2026-10-15', '2026-11-15', 1, ?)
    """, (admin_id, admin_id, admin_id, admin_id))
    
    # 8. Seed Expenses
    db.execute("""
        INSERT INTO expenses (expense_no, category, description, amount, expense_date, paid_to, payment_method, receipt_ref, created_by)
        VALUES
        ('EXP-202610-01', 'Security Services', 'Monthly security guard services (4 daytime + 3 night guards) for October 2026', 42000.0, '2026-10-02', 'Apex Falcon Security Pvt Ltd', 'Bank Transfer', 'INV-AF-88219', ?),
        ('EXP-202610-02', 'Cleaning & Housekeeping', 'Housekeeping contractor wages, floor disinfectant chemicals, waste bags', 16500.0, '2026-10-04', 'CleanPro Facility Solutions', 'Bank Transfer', 'INV-CP-2026/10', ?),
        ('EXP-202610-03', 'Electricity & Power', 'Common area lighting, water pump motors, and elevator electricity bill for Sep-Oct', 18450.0, '2026-10-08', 'State Electricity Board (MSEDCL)', 'Bank Transfer', 'EB-MUM-992140', ?),
        ('EXP-202610-04', 'Repairs & Maintenance', 'Compound wall LED flood light replacement & electrical switchgear servicing', 4800.0, '2026-10-12', 'Omkar Electricals & Hardware', 'UPI', 'UPI-992184-OMKAR', ?),
        ('EXP-202610-05', 'Lift AMC', 'Quarterly comprehensive maintenance contract for 3 passenger elevators', 12500.0, '2026-10-14', 'Schindler Elevators India Ltd', 'Cheque', 'CHQ#882190-SBI', ?),
        ('EXP-202610-06', 'Gardening & Landscaping', 'Lawn mowing, organic fertilizer, tree pruning, and seasonal flowering plants', 3800.0, '2026-10-18', 'Green Thumb Nursery & Garden Care', 'Cash', 'VOUCH-GT-114', ?)
    """, (admin_id, admin_id, admin_id, admin_id, admin_id, admin_id))
    
    print("Sample data successfully seeded!")
