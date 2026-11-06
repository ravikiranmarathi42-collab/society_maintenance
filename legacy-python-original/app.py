import os
import csv
import io
import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, Response, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from utils.database import get_db, close_db, query_db, execute_db, init_db
from utils.auth import login_required, admin_required, resident_required, get_current_user, get_resident_info

app = Flask(__name__)
app.config.from_object(Config)

# Register database teardown
app.teardown_appcontext(close_db)

@app.template_filter('format_date')
def format_date_filter(val):
    if not val:
        return ''
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    return str(val)[:10]

@app.template_filter('format_datetime')
def format_datetime_filter(val):
    if not val:
        return ''
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d %H:%M')
    return str(val)[:16]

@app.context_processor
def inject_global_data():
    """Inject global context variables into templates."""
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    return {
        'config': Config,
        'current_date': today_str
    }

# ==============================================================================
# 1. PUBLIC ROUTES (Home, Login, Register, Logout)
# ==============================================================================

@app.route('/')
def index():
    """Home landing page."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('resident_dashboard'))
    return render_template('index.html', active_page='home')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Unified user authentication for Admin and Resident."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('resident_dashboard'))

    if request.method == 'POST':
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        selected_role = request.form.get('role', 'resident')

        if not login_input or not password:
            flash("Please enter both username/email and password.", "danger")
            return render_template('login.html', active_page='login')

        # Query user by username or email
        user = query_db("""
            SELECT * FROM users 
            WHERE (username = ? OR email = ?) AND role = ?
        """, (login_input, login_input, selected_role), one=True)

        if user and check_password_hash(user['password_hash'], password):
            # Create session
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']

            flash(f"Welcome back, {user['full_name']}!", "success")
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('resident_dashboard'))
        else:
            flash("Invalid credentials or incorrect role selected. Please try again.", "danger")

    return render_template('login.html', active_page='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Resident self-registration."""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        flat_id = request.form.get('flat_id')
        emergency_contact = request.form.get('emergency_contact', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server side validations
        if not (full_name and username and email and phone and flat_id and password):
            flash("All required fields marked with * must be filled.", "danger")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "danger")
            return redirect(url_for('register'))

        # Check existing username or email
        existing_user = query_db("SELECT id FROM users WHERE username = ? OR email = ?", (username, email), one=True)
        if existing_user:
            flash("Username or Email is already registered. Please choose another or login.", "danger")
            return redirect(url_for('register'))

        # Check if flat is still vacant
        flat = query_db("SELECT * FROM flats WHERE id = ?", (flat_id,), one=True)
        if not flat:
            flash("Selected flat does not exist.", "danger")
            return redirect(url_for('register'))

        try:
            # 1. Create user record
            pw_hash = generate_password_hash(password)
            user_id, _ = execute_db("""
                INSERT INTO users (username, email, password_hash, role, full_name, phone)
                VALUES (?, ?, ?, 'resident', ?, ?)
            """, (username, email, pw_hash, full_name, phone))

            # 2. Create resident record connected to user & flat
            today_str = datetime.date.today().strftime('%Y-%m-%d')
            execute_db("""
                INSERT INTO residents (user_id, flat_id, full_name, phone, email, joining_date, emergency_contact, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
            """, (user_id, flat_id, full_name, phone, email, today_str, emergency_contact))

            # 3. Mark flat as Occupied
            execute_db("UPDATE flats SET status = 'Occupied' WHERE id = ?", (flat_id,))

            # Automatic login
            session.clear()
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = 'resident'
            session['full_name'] = full_name

            flash("Registration successful! Welcome to Greenfield Heights.", "success")
            return redirect(url_for('resident_dashboard'))
        except Exception as e:
            flash(f"An error occurred while creating your account: {str(e)}", "danger")
            return redirect(url_for('register'))

    # GET request: load vacant flats
    vacant_flats = query_db("SELECT * FROM flats WHERE status = 'Vacant' ORDER BY building_block, floor, flat_number")
    return render_template('register.html', available_flats=vacant_flats, active_page='register')

@app.route('/logout')
def logout():
    """Clear session and log user out."""
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('login'))

# ==============================================================================
# 2. ADMIN DASHBOARD & CORE MODULES
# ==============================================================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin Overview Dashboard."""
    # Flat statistics
    flats_count = query_db("SELECT COUNT(*) as count FROM flats", one=True)['count']
    occupied_count = query_db("SELECT COUNT(*) as count FROM flats WHERE status = 'Occupied'", one=True)['count']
    vacant_count = flats_count - occupied_count

    # Resident count
    residents_count = query_db("SELECT COUNT(*) as count FROM residents WHERE status = 'Active'", one=True)['count']

    # Financial collections
    collected_row = query_db("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'Success'", one=True)
    total_collected = collected_row['total'] if collected_row else 0.0

    paid_bills_count = query_db("SELECT COUNT(*) as count FROM maintenance_bills WHERE status = 'Paid'", one=True)['count']

    # Pending dues
    pending_row = query_db("""
        SELECT COALESCE(SUM(amount + penalty), 0) as total, COUNT(*) as count 
        FROM maintenance_bills 
        WHERE status IN ('Pending', 'Overdue')
    """, one=True)
    pending_amount = pending_row['total'] if pending_row else 0.0
    pending_bills_count = pending_row['count'] if pending_row else 0

    # Complaints statistics
    complaints_row = query_db("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Submitted' THEN 1 ELSE 0 END) as submitted,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved
        FROM complaints
    """, one=True)
    
    total_complaints = complaints_row['total'] or 0
    complaints_sub = complaints_row['submitted'] or 0
    complaints_in_prog = complaints_row['in_progress'] or 0
    complaints_res = complaints_row['resolved'] or 0
    unresolved_complaints = complaints_sub + complaints_in_prog

    # Expenses
    current_month_prefix = datetime.date.today().strftime('%Y-%m')
    curr_exp_row = query_db("""
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM expenses 
        WHERE strftime('%Y-%m', expense_date) = ?
    """, (current_month_prefix,), one=True)
    monthly_expenses = curr_exp_row['total'] if curr_exp_row else 0.0

    tot_exp_row = query_db("SELECT COALESCE(SUM(amount), 0) as total FROM expenses", one=True)
    total_expenses = tot_exp_row['total'] if tot_exp_row else 0.0

    treasury_balance = total_collected - total_expenses

    stats = {
        'total_flats': flats_count,
        'occupied_flats': occupied_count,
        'vacant_flats': vacant_count,
        'total_residents': residents_count,
        'total_collected': total_collected,
        'paid_bills_count': paid_bills_count,
        'pending_amount': pending_amount,
        'pending_bills_count': pending_bills_count,
        'total_complaints': total_complaints,
        'complaints_submitted': complaints_sub,
        'complaints_in_progress': complaints_in_prog,
        'complaints_resolved': complaints_res,
        'unresolved_complaints': unresolved_complaints,
        'monthly_expenses': monthly_expenses,
        'total_expenses': total_expenses,
        'treasury_balance': treasury_balance
    }

    # Recent payments (limit 5)
    recent_payments = query_db("""
        SELECT p.*, b.billing_month, f.flat_number, r.full_name as resident_name
        FROM payments p
        JOIN maintenance_bills b ON p.bill_id = b.id
        JOIN flats f ON b.flat_id = f.id
        LEFT JOIN residents r ON p.resident_id = r.id
        ORDER BY p.payment_date DESC
        LIMIT 5
    """)

    # Recent complaints (limit 4)
    recent_complaints = query_db("""
        SELECT c.*, f.flat_number, r.full_name as resident_name
        FROM complaints c
        JOIN flats f ON c.flat_id = f.id
        JOIN residents r ON c.resident_id = r.id
        WHERE c.status != 'Resolved'
        ORDER BY c.created_at DESC
        LIMIT 4
    """)

    # Chart datasets: last 5 months financial data
    chart_months = ['2026-06', '2026-07', '2026-08', '2026-09', '2026-10']
    chart_collections = []
    chart_expenses = []
    for m in chart_months:
        c_val = query_db("SELECT COALESCE(SUM(amount), 0) as t FROM payments WHERE strftime('%Y-%m', payment_date) = ?", (m,), one=True)['t']
        e_val = query_db("SELECT COALESCE(SUM(amount), 0) as t FROM expenses WHERE strftime('%Y-%m', expense_date) = ?", (m,), one=True)['t']
        chart_collections.append(c_val)
        chart_expenses.append(e_val)

    return render_template(
        'admin_dashboard.html',
        active_page='dashboard',
        stats=stats,
        recent_payments=recent_payments,
        recent_complaints=recent_complaints,
        chart_months=chart_months,
        chart_collections=chart_collections,
        chart_expenses=chart_expenses
    )

# ------------------------------------------------------------------------------
# Flats Management
# ------------------------------------------------------------------------------
@app.route('/admin/flats')
@admin_required
def flats():
    """Manage flats list."""
    all_flats = query_db("""
        SELECT f.*, r.full_name as resident_name, r.phone as resident_phone
        FROM flats f
        LEFT JOIN residents r ON f.id = r.flat_id AND r.status = 'Active'
        ORDER BY f.building_block, f.floor, f.flat_number
    """)
    return render_template('flats.html', flats=all_flats, active_page='flats')

@app.route('/admin/flats/add', methods=['POST'])
@admin_required
def add_flat():
    flat_number = request.form.get('flat_number', '').strip()
    building_block = request.form.get('building_block', '').strip()
    floor = request.form.get('floor', type=int)
    flat_type = request.form.get('flat_type', '2 BHK')
    maintenance_rate = request.form.get('maintenance_rate', type=float) or 3000.0
    status = request.form.get('status', 'Vacant')

    if not flat_number or not building_block:
        flash("Flat number and block are required.", "danger")
        return redirect(url_for('flats'))

    # Check duplicate flat number
    exists = query_db("SELECT id FROM flats WHERE flat_number = ?", (flat_number,), one=True)
    if exists:
        flash(f"Flat {flat_number} already exists.", "danger")
        return redirect(url_for('flats'))

    execute_db("""
        INSERT INTO flats (flat_number, building_block, floor, flat_type, maintenance_rate, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (flat_number, building_block, floor, flat_type, maintenance_rate, status))

    flash(f"Flat {flat_number} registered successfully.", "success")
    return redirect(url_for('flats'))

@app.route('/admin/flats/edit/<int:flat_id>', methods=['POST'])
@admin_required
def edit_flat(flat_id):
    flat_number = request.form.get('flat_number', '').strip()
    building_block = request.form.get('building_block', '').strip()
    floor = request.form.get('floor', type=int)
    flat_type = request.form.get('flat_type')
    maintenance_rate = request.form.get('maintenance_rate', type=float)
    status = request.form.get('status')

    execute_db("""
        UPDATE flats
        SET flat_number = ?, building_block = ?, floor = ?, flat_type = ?, maintenance_rate = ?, status = ?
        WHERE id = ?
    """, (flat_number, building_block, floor, flat_type, maintenance_rate, status, flat_id))

    flash(f"Flat {flat_number} updated successfully.", "success")
    return redirect(url_for('flats'))

@app.route('/admin/flats/delete/<int:flat_id>', methods=['POST'])
@admin_required
def delete_flat(flat_id):
    # Check if residents are assigned
    res_count = query_db("SELECT COUNT(*) as count FROM residents WHERE flat_id = ?", (flat_id,), one=True)['count']
    if res_count > 0:
        flash("Cannot delete flat while residents are mapped to it. Please reassign or remove residents first.", "danger")
        return redirect(url_for('flats'))

    execute_db("DELETE FROM flats WHERE id = ?", (flat_id,))
    flash("Flat record deleted successfully.", "info")
    return redirect(url_for('flats'))

# ------------------------------------------------------------------------------
# Residents Management
# ------------------------------------------------------------------------------
@app.route('/admin/residents')
@admin_required
def residents():
    """Manage residents list."""
    all_residents = query_db("""
        SELECT r.*, f.flat_number, f.building_block, f.floor, u.username
        FROM residents r
        JOIN flats f ON r.flat_id = f.id
        LEFT JOIN users u ON r.user_id = u.id
        ORDER BY r.id DESC
    """)
    vacant_flats = query_db("SELECT * FROM flats WHERE status = 'Vacant' ORDER BY flat_number")
    return render_template('residents.html', residents=all_residents, vacant_flats=vacant_flats, active_page='residents')

@app.route('/admin/residents/add', methods=['POST'])
@admin_required
def add_resident():
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    flat_id = request.form.get('flat_id', type=int)
    joining_date = request.form.get('joining_date')
    emergency_contact = request.form.get('emergency_contact', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not full_name or not phone or not email or not flat_id:
        flash("Full name, phone, email, and flat assignment are required.", "danger")
        return redirect(url_for('residents'))

    user_id = None
    if username and password:
        # Check duplicate username
        exist = query_db("SELECT id FROM users WHERE username = ? OR email = ?", (username, email), one=True)
        if exist:
            flash("Username or email already in use for login.", "danger")
            return redirect(url_for('residents'))
        
        user_id, _ = execute_db("""
            INSERT INTO users (username, email, password_hash, role, full_name, phone)
            VALUES (?, ?, ?, 'resident', ?, ?)
        """, (username, email, generate_password_hash(password), full_name, phone))

    execute_db("""
        INSERT INTO residents (user_id, flat_id, full_name, phone, email, joining_date, emergency_contact, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
    """, (user_id, flat_id, full_name, phone, email, joining_date, emergency_contact))

    # Mark flat as occupied
    execute_db("UPDATE flats SET status = 'Occupied' WHERE id = ?", (flat_id,))

    flash(f"Resident {full_name} registered successfully.", "success")
    return redirect(url_for('residents'))

@app.route('/admin/residents/edit/<int:resident_id>', methods=['POST'])
@admin_required
def edit_resident(resident_id):
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    new_flat_id = request.form.get('flat_id', type=int)
    joining_date = request.form.get('joining_date')
    emergency_contact = request.form.get('emergency_contact', '').strip()
    status = request.form.get('status', 'Active')

    current_res = query_db("SELECT flat_id, user_id FROM residents WHERE id = ?", (resident_id,), one=True)
    if not current_res:
        flash("Resident not found.", "danger")
        return redirect(url_for('residents'))

    old_flat_id = current_res['flat_id']

    # Update resident record
    execute_db("""
        UPDATE residents
        SET full_name = ?, phone = ?, email = ?, flat_id = ?, joining_date = ?, emergency_contact = ?, status = ?
        WHERE id = ?
    """, (full_name, phone, email, new_flat_id, joining_date, emergency_contact, status, resident_id))

    # Also sync users table full_name and phone if linked
    if current_res['user_id']:
        execute_db("""
            UPDATE users SET full_name = ?, phone = ?, email = ? WHERE id = ?
        """, (full_name, phone, email, current_res['user_id']))

    # If flat changed, update flat statuses
    if old_flat_id != new_flat_id:
        execute_db("UPDATE flats SET status = 'Occupied' WHERE id = ?", (new_flat_id,))
        # Check if old flat has other residents
        active_on_old = query_db("SELECT COUNT(*) as c FROM residents WHERE flat_id = ? AND status = 'Active'", (old_flat_id,), one=True)['c']
        if active_on_old == 0:
            execute_db("UPDATE flats SET status = 'Vacant' WHERE id = ?", (old_flat_id,))

    flash("Resident details updated successfully.", "success")
    return redirect(url_for('residents'))

@app.route('/admin/residents/delete/<int:resident_id>', methods=['POST'])
@admin_required
def delete_resident(resident_id):
    res = query_db("SELECT flat_id, user_id FROM residents WHERE id = ?", (resident_id,), one=True)
    if res:
        flat_id = res['flat_id']
        user_id = res['user_id']
        execute_db("DELETE FROM residents WHERE id = ?", (resident_id,))
        if user_id:
            execute_db("DELETE FROM users WHERE id = ?", (user_id,))
        # Check if any active resident remains for this flat
        rem = query_db("SELECT COUNT(*) as c FROM residents WHERE flat_id = ? AND status = 'Active'", (flat_id,), one=True)['c']
        if rem == 0:
            execute_db("UPDATE flats SET status = 'Vacant' WHERE id = ?", (flat_id,))

    flash("Resident removed successfully.", "info")
    return redirect(url_for('residents'))

# ------------------------------------------------------------------------------
# Maintenance Bills Management
# ------------------------------------------------------------------------------
@app.route('/admin/bills')
@admin_required
def maintenance_bills():
    """List maintenance bills with status filter."""
    status_filter = request.args.get('status', 'all')
    
    if status_filter != 'all':
        bills_list = query_db("""
            SELECT b.*, f.flat_number, f.building_block, r.full_name as resident_name
            FROM maintenance_bills b
            JOIN flats f ON b.flat_id = f.id
            LEFT JOIN residents r ON f.id = r.flat_id AND r.status = 'Active'
            WHERE b.status = ?
            ORDER BY b.billing_month DESC, b.id DESC
        """, (status_filter,))
    else:
        bills_list = query_db("""
            SELECT b.*, f.flat_number, f.building_block, r.full_name as resident_name
            FROM maintenance_bills b
            JOIN flats f ON b.flat_id = f.id
            LEFT JOIN residents r ON f.id = r.flat_id AND r.status = 'Active'
            ORDER BY b.billing_month DESC, b.id DESC
        """)

    all_flats = query_db("SELECT * FROM flats ORDER BY flat_number")
    return render_template(
        'maintenance_bills.html',
        bills=bills_list,
        all_flats=all_flats,
        current_status=status_filter,
        active_page='bills'
    )

@app.route('/admin/bills/generate-single', methods=['POST'])
@admin_required
def generate_single_bill():
    flat_id = request.form.get('flat_id', type=int)
    billing_month = request.form.get('billing_month')  # e.g. '2026-11'
    due_date = request.form.get('due_date')
    amount = request.form.get('amount', type=float)
    notes = request.form.get('notes', 'Monthly society maintenance charges')

    flat = query_db("SELECT * FROM flats WHERE id = ?", (flat_id,), one=True)
    if not flat:
        flash("Invalid flat selected.", "danger")
        return redirect(url_for('maintenance_bills'))

    if not amount or amount <= 0:
        amount = flat['maintenance_rate']

    # Generate unique bill number
    clean_month = billing_month.replace('-', '')
    bill_no = f"BILL-{clean_month}-F{flat['flat_number'].replace('-', '')}"

    # Check duplicate
    exists = query_db("SELECT id FROM maintenance_bills WHERE flat_id = ? AND billing_month = ?", (flat_id, billing_month), one=True)
    if exists:
        flash(f"A bill for Flat {flat['flat_number']} for month {billing_month} already exists.", "warning")
        return redirect(url_for('maintenance_bills'))

    execute_db("""
        INSERT INTO maintenance_bills (bill_no, flat_id, billing_month, amount, due_date, penalty, status, notes)
        VALUES (?, ?, ?, ?, ?, 0.0, 'Pending', ?)
    """, (bill_no, flat_id, billing_month, amount, due_date, notes))

    flash(f"Bill {bill_no} generated successfully for Flat {flat['flat_number']}.", "success")
    return redirect(url_for('maintenance_bills'))

@app.route('/admin/bills/generate-bulk', methods=['POST'])
@admin_required
def generate_bulk_bills():
    """Bulk generate monthly bills for all occupied flats."""
    billing_month = request.form.get('billing_month')
    due_date = request.form.get('due_date')
    notes = request.form.get('notes', 'Regular monthly society maintenance bill')

    if not billing_month or not due_date:
        flash("Billing month and due date are required.", "danger")
        return redirect(url_for('maintenance_bills'))

    occupied_flats = query_db("SELECT * FROM flats WHERE status = 'Occupied'")
    clean_month = billing_month.replace('-', '')
    count = 0

    for flat in occupied_flats:
        # Check if already billed for this month
        exists = query_db("SELECT id FROM maintenance_bills WHERE flat_id = ? AND billing_month = ?", (flat['id'], billing_month), one=True)
        if not exists:
            bill_no = f"BILL-{clean_month}-F{flat['flat_number'].replace('-', '')}"
            execute_db("""
                INSERT INTO maintenance_bills (bill_no, flat_id, billing_month, amount, due_date, penalty, status, notes)
                VALUES (?, ?, ?, ?, ?, 0.0, 'Pending', ?)
            """, (bill_no, flat['id'], billing_month, flat['maintenance_rate'], due_date, notes))
            count += 1

    flash(f"Bulk billing completed! Generated {count} new maintenance bills for {billing_month}.", "success")
    return redirect(url_for('maintenance_bills'))

@app.route('/admin/bills/edit/<int:bill_id>', methods=['POST'])
@admin_required
def edit_bill(bill_id):
    amount = request.form.get('amount', type=float)
    penalty = request.form.get('penalty', type=float) or 0.0
    due_date = request.form.get('due_date')
    status = request.form.get('status')
    notes = request.form.get('notes')

    execute_db("""
        UPDATE maintenance_bills
        SET amount = ?, penalty = ?, due_date = ?, status = ?, notes = ?
        WHERE id = ?
    """, (amount, penalty, due_date, status, notes, bill_id))

    flash("Bill details updated successfully.", "success")
    return redirect(url_for('maintenance_bills'))

@app.route('/admin/bills/delete/<int:bill_id>', methods=['POST'])
@admin_required
def delete_bill(bill_id):
    execute_db("DELETE FROM maintenance_bills WHERE id = ?", (bill_id,))
    flash("Maintenance bill deleted successfully.", "info")
    return redirect(url_for('maintenance_bills'))

# ------------------------------------------------------------------------------
# Payment Management & Receipts
# ------------------------------------------------------------------------------
@app.route('/admin/payments')
@admin_required
def payments():
    """Admin payments listing."""
    payments_list = query_db("""
        SELECT p.*, b.bill_no, b.billing_month, f.flat_number, r.full_name as resident_name
        FROM payments p
        JOIN maintenance_bills b ON p.bill_id = b.id
        JOIN flats f ON b.flat_id = f.id
        LEFT JOIN residents r ON p.resident_id = r.id
        ORDER BY p.payment_date DESC
    """)
    total_col = sum(p['amount'] for p in payments_list)
    return render_template('payments.html', payments=payments_list, total_collected=total_col, active_page='payments')

@app.route('/admin/payments/record', methods=['POST'])
@admin_required
def record_payment():
    """Record payment by Admin (offline/cash/cheque)."""
    bill_id = request.form.get('bill_id', type=int)
    amount = request.form.get('amount', type=float)
    payment_method = request.form.get('payment_method', 'Cash')
    transaction_id = request.form.get('transaction_id', '').strip()
    payment_date = request.form.get('payment_date')

    bill = query_db("""
        SELECT b.*, f.id as flat_id, r.id as resident_id
        FROM maintenance_bills b
        JOIN flats f ON b.flat_id = f.id
        LEFT JOIN residents r ON f.id = r.flat_id AND r.status = 'Active'
        WHERE b.id = ?
    """, (bill_id,), one=True)

    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for('maintenance_bills'))

    # Generate receipt number
    receipt_no = f"RCT-{datetime.date.today().strftime('%Y%m')}-{bill_id:04d}"

    # Insert payment record
    pay_id, _ = execute_db("""
        INSERT INTO payments (receipt_no, bill_id, resident_id, amount, payment_date, payment_method, transaction_id, remarks, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Recorded by Admin', 'Success')
    """, (receipt_no, bill_id, bill['resident_id'], amount, payment_date, payment_method, transaction_id))

    # Mark bill as Paid
    execute_db("UPDATE maintenance_bills SET status = 'Paid' WHERE id = ?", (bill_id,))

    flash(f"Payment recorded successfully! Receipt #{receipt_no} generated.", "success")
    return redirect(url_for('view_receipt', payment_id=pay_id))

@app.route('/receipt/<int:payment_id>')
@login_required
def view_receipt(payment_id):
    """View and print official payment receipt."""
    payment = query_db("""
        SELECT p.*, b.bill_no, b.billing_month, b.amount as base_amount, b.penalty,
               f.flat_number, f.building_block, f.floor, f.flat_type,
               r.full_name as resident_name, r.phone as resident_phone, r.email as resident_email,
               r.user_id as resident_user_id
        FROM payments p
        JOIN maintenance_bills b ON p.bill_id = b.id
        JOIN flats f ON b.flat_id = f.id
        LEFT JOIN residents r ON p.resident_id = r.id
        WHERE p.id = ?
    """, (payment_id,), one=True)

    if not payment:
        flash("Receipt record not found.", "danger")
        return redirect(url_for('index'))

    # Resident authorization check: Residents can only view their own receipts
    if session.get('role') == 'resident':
        if payment['resident_user_id'] != session.get('user_id'):
            flash("Access denied. You can only view your own receipts.", "danger")
            return redirect(url_for('resident_dashboard'))

    return render_template('receipt.html', payment=payment, active_page='payments')

@app.route('/bill-receipt/<int:bill_id>')
@login_required
def view_bill_receipt(bill_id):
    """Convenience helper to view receipt by bill ID."""
    payment = query_db("SELECT id FROM payments WHERE bill_id = ? ORDER BY id DESC LIMIT 1", (bill_id,), one=True)
    if payment:
        return redirect(url_for('view_receipt', payment_id=payment['id']))
    flash("No payment receipt found for this bill.", "warning")
    return redirect(url_for('maintenance_bills' if session.get('role') == 'admin' else 'resident_dashboard'))

# ------------------------------------------------------------------------------
# Complaints Management
# ------------------------------------------------------------------------------
@app.route('/admin/complaints')
@admin_required
def complaints():
    """Admin complaints list with status filter."""
    status_filter = request.args.get('status', 'all')
    if status_filter != 'all':
        complaints_list = query_db("""
            SELECT c.*, f.flat_number, r.full_name as resident_name, r.phone as resident_phone
            FROM complaints c
            JOIN flats f ON c.flat_id = f.id
            JOIN residents r ON c.resident_id = r.id
            WHERE c.status = ?
            ORDER BY c.created_at DESC
        """, (status_filter,))
    else:
        complaints_list = query_db("""
            SELECT c.*, f.flat_number, r.full_name as resident_name, r.phone as resident_phone
            FROM complaints c
            JOIN flats f ON c.flat_id = f.id
            JOIN residents r ON c.resident_id = r.id
            ORDER BY c.created_at DESC
        """)

    return render_template('complaints.html', complaints=complaints_list, current_status=status_filter, active_page='complaints')

@app.route('/admin/complaints/update/<int:complaint_id>', methods=['POST'])
@admin_required
def update_complaint_status(complaint_id):
    status = request.form.get('status')
    admin_remarks = request.form.get('admin_remarks', '').strip()

    resolved_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'Resolved' else None

    execute_db("""
        UPDATE complaints
        SET status = ?, admin_remarks = ?, resolved_at = COALESCE(?, resolved_at)
        WHERE id = ?
    """, (status, admin_remarks, resolved_at, complaint_id))

    flash(f"Complaint #{complaint_id} updated to '{status}'.", "success")
    return redirect(url_for('complaints'))

# ------------------------------------------------------------------------------
# Notices & Announcements
# ------------------------------------------------------------------------------
@app.route('/admin/notices')
@login_required
def notices():
    """Notice board accessible to both Admin and Resident."""
    all_notices = query_db("SELECT * FROM notices ORDER BY published_date DESC, id DESC")
    return render_template('notices.html', notices=all_notices, active_page='notices')

@app.route('/admin/notices/add', methods=['POST'])
@admin_required
def add_notice():
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'General')
    published_date = request.form.get('published_date')
    expiry_date = request.form.get('expiry_date') or None
    message = request.form.get('message', '').strip()

    if not title or not message:
        flash("Title and message are required.", "danger")
        return redirect(url_for('notices'))

    execute_db("""
        INSERT INTO notices (title, message, category, published_date, expiry_date, is_active, created_by)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (title, message, category, published_date, expiry_date, session.get('user_id')))

    flash("Society notice published successfully.", "success")
    return redirect(url_for('notices'))

@app.route('/admin/notices/edit/<int:notice_id>', methods=['POST'])
@admin_required
def edit_notice(notice_id):
    title = request.form.get('title', '').strip()
    category = request.form.get('category')
    published_date = request.form.get('published_date')
    expiry_date = request.form.get('expiry_date') or None
    message = request.form.get('message', '').strip()

    execute_db("""
        UPDATE notices
        SET title = ?, message = ?, category = ?, published_date = ?, expiry_date = ?
        WHERE id = ?
    """, (title, message, category, published_date, expiry_date, notice_id))

    flash("Notice updated successfully.", "success")
    return redirect(url_for('notices'))

@app.route('/admin/notices/delete/<int:notice_id>', methods=['POST'])
@admin_required
def delete_notice(notice_id):
    execute_db("DELETE FROM notices WHERE id = ?", (notice_id,))
    flash("Notice removed successfully.", "info")
    return redirect(url_for('notices'))

# ------------------------------------------------------------------------------
# Society Expenses Management
# ------------------------------------------------------------------------------
@app.route('/admin/expenses')
@admin_required
def expenses():
    """Society operational expenses ledger."""
    all_expenses = query_db("SELECT * FROM expenses ORDER BY expense_date DESC, id DESC")
    
    current_month_prefix = datetime.date.today().strftime('%Y-%m')
    curr_exp_row = query_db("""
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM expenses 
        WHERE strftime('%Y-%m', expense_date) = ?
    """, (current_month_prefix,), one=True)
    current_month_expenses = curr_exp_row['total'] if curr_exp_row else 0.0

    tot_exp_row = query_db("SELECT COALESCE(SUM(amount), 0) as total FROM expenses", one=True)
    total_expenses = tot_exp_row['total'] if tot_exp_row else 0.0

    return render_template(
        'expenses.html',
        expenses=all_expenses,
        current_month_expenses=current_month_expenses,
        total_expenses=total_expenses,
        active_page='expenses'
    )

@app.route('/admin/expenses/add', methods=['POST'])
@admin_required
def add_expense():
    category = request.form.get('category', 'Other')
    description = request.form.get('description', '').strip()
    amount = request.form.get('amount', type=float)
    expense_date = request.form.get('expense_date')
    paid_to = request.form.get('paid_to', '').strip()
    payment_method = request.form.get('payment_method', 'Bank Transfer')
    receipt_ref = request.form.get('receipt_ref', '').strip()

    if not description or not amount or not paid_to:
        flash("Category, description, amount, and payee are required.", "danger")
        return redirect(url_for('expenses'))

    clean_date = expense_date.replace('-', '')[:6]
    exp_count = query_db("SELECT COUNT(*) as c FROM expenses", one=True)['c'] + 1
    expense_no = f"EXP-{clean_date}-{exp_count:02d}"

    execute_db("""
        INSERT INTO expenses (expense_no, category, description, amount, expense_date, paid_to, payment_method, receipt_ref, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (expense_no, category, description, amount, expense_date, paid_to, payment_method, receipt_ref, session.get('user_id')))

    flash(f"Expense voucher #{expense_no} recorded successfully.", "success")
    return redirect(url_for('expenses'))

@app.route('/admin/expenses/edit/<int:expense_id>', methods=['POST'])
@admin_required
def edit_expense(expense_id):
    category = request.form.get('category')
    description = request.form.get('description', '').strip()
    amount = request.form.get('amount', type=float)
    expense_date = request.form.get('expense_date')
    paid_to = request.form.get('paid_to', '').strip()
    payment_method = request.form.get('payment_method')
    receipt_ref = request.form.get('receipt_ref', '').strip()

    execute_db("""
        UPDATE expenses
        SET category = ?, description = ?, amount = ?, expense_date = ?, paid_to = ?, payment_method = ?, receipt_ref = ?
        WHERE id = ?
    """, (category, description, amount, expense_date, paid_to, payment_method, receipt_ref, expense_id))

    flash("Expense voucher updated successfully.", "success")
    return redirect(url_for('expenses'))

@app.route('/admin/expenses/delete/<int:expense_id>', methods=['POST'])
@admin_required
def delete_expense(expense_id):
    execute_db("DELETE FROM expenses WHERE id = ?", (expense_id,))
    flash("Expense voucher deleted successfully.", "info")
    return redirect(url_for('expenses'))

# ------------------------------------------------------------------------------
# Reports & Analytics (with CSV Export)
# ------------------------------------------------------------------------------
@app.route('/admin/reports')
@admin_required
def reports():
    """Reporting suite for collections, overdue bills, balance sheets, and complaints."""
    active_tab = request.args.get('tab', 'collections')

    # Data for collections
    collections_data = query_db("""
        SELECT p.*, b.bill_no, b.billing_month, f.flat_number, r.full_name as resident_name
        FROM payments p
        JOIN maintenance_bills b ON p.bill_id = b.id
        JOIN flats f ON b.flat_id = f.id
        LEFT JOIN residents r ON p.resident_id = r.id
        ORDER BY p.payment_date DESC
    """)
    total_collected = sum(c['amount'] for c in collections_data)

    # Data for pending/overdue bills
    pending_data = query_db("""
        SELECT b.*, f.flat_number, r.full_name as resident_name, r.phone as resident_phone
        FROM maintenance_bills b
        JOIN flats f ON b.flat_id = f.id
        LEFT JOIN residents r ON f.id = r.flat_id AND r.status = 'Active'
        WHERE b.status IN ('Pending', 'Overdue')
        ORDER BY b.due_date ASC
    """)
    total_pending_amount = sum(b['amount'] + b['penalty'] for b in pending_data)

    # Data for expenses & balance sheet
    expenses_data = query_db("SELECT * FROM expenses ORDER BY expense_date DESC")
    total_expenses = sum(e['amount'] for e in expenses_data)
    
    expense_by_category = query_db("""
        SELECT category, COUNT(*) as count, SUM(amount) as total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
    """)

    # Data for complaints
    complaints_data = query_db("""
        SELECT c.*, f.flat_number, r.full_name as resident_name
        FROM complaints c
        JOIN flats f ON c.flat_id = f.id
        JOIN residents r ON c.resident_id = r.id
        ORDER BY c.created_at DESC
    """)

    return render_template(
        'reports.html',
        active_tab=active_tab,
        collections_data=collections_data,
        total_collected=total_collected,
        pending_data=pending_data,
        total_pending_amount=total_pending_amount,
        expenses_data=expenses_data,
        total_expenses=total_expenses,
        expense_by_category=expense_by_category,
        complaints_data=complaints_data,
        active_page='reports'
    )

@app.route('/admin/reports/export/<report_type>')
@admin_required
def export_csv(report_type):
    """Dynamic CSV export engine for society audit reports."""
    si = io.StringIO()
    writer = csv.writer(si)

    if report_type == 'collections':
        filename = f"maintenance_collections_{datetime.date.today()}.csv"
        writer.writerow(['Receipt No', 'Bill No', 'Flat Number', 'Resident Name', 'Billing Month', 'Amount (INR)', 'Payment Method', 'Payment Date', 'Transaction ID'])
        rows = query_db("""
            SELECT p.receipt_no, b.bill_no, f.flat_number, r.full_name, b.billing_month, p.amount, p.payment_method, p.payment_date, p.transaction_id
            FROM payments p
            JOIN maintenance_bills b ON p.bill_id = b.id
            JOIN flats f ON b.flat_id = f.id
            LEFT JOIN residents r ON p.resident_id = r.id
            ORDER BY p.payment_date DESC
        """)
        for r in rows:
            writer.writerow([r['receipt_no'], r['bill_no'], r['flat_number'], r['full_name'], r['billing_month'], r['amount'], r['payment_method'], r['payment_date'], r['transaction_id']])

    elif report_type == 'pending':
        filename = f"pending_maintenance_dues_{datetime.date.today()}.csv"
        writer.writerow(['Bill No', 'Flat Number', 'Resident Name', 'Phone', 'Billing Month', 'Base Amount', 'Penalty', 'Total Due', 'Due Date', 'Status'])
        rows = query_db("""
            SELECT b.bill_no, f.flat_number, r.full_name, r.phone, b.billing_month, b.amount, b.penalty, (b.amount + b.penalty) as total_due, b.due_date, b.status
            FROM maintenance_bills b
            JOIN flats f ON b.flat_id = f.id
            LEFT JOIN residents r ON f.id = r.flat_id AND r.status = 'Active'
            WHERE b.status IN ('Pending', 'Overdue')
            ORDER BY b.due_date ASC
        """)
        for r in rows:
            writer.writerow([r['bill_no'], r['flat_number'], r['full_name'], r['phone'], r['billing_month'], r['amount'], r['penalty'], r['total_due'], r['due_date'], r['status']])

    elif report_type in ('expenses', 'income_expense'):
        filename = f"society_expenses_{datetime.date.today()}.csv"
        writer.writerow(['Voucher No', 'Category', 'Description', 'Amount (INR)', 'Expense Date', 'Paid To', 'Payment Method', 'Receipt Reference'])
        rows = query_db("SELECT * FROM expenses ORDER BY expense_date DESC")
        for r in rows:
            writer.writerow([r['expense_no'], r['category'], r['description'], r['amount'], r['expense_date'], r['paid_to'], r['payment_method'], r['receipt_ref']])

    elif report_type == 'complaints':
        filename = f"complaints_report_{datetime.date.today()}.csv"
        writer.writerow(['ID', 'Flat Number', 'Resident Name', 'Category', 'Subject', 'Priority', 'Status', 'Date Logged', 'Admin Remarks'])
        rows = query_db("""
            SELECT c.id, f.flat_number, r.full_name, c.category, c.subject, c.priority, c.status, c.created_at, c.admin_remarks
            FROM complaints c
            JOIN flats f ON c.flat_id = f.id
            JOIN residents r ON c.resident_id = r.id
            ORDER BY c.created_at DESC
        """)
        for r in rows:
            writer.writerow([r['id'], r['flat_number'], r['full_name'], r['category'], r['subject'], r['priority'], r['status'], r['created_at'], r['admin_remarks']])
    else:
        abort(404)

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# ==============================================================================
# 3. RESIDENT DASHBOARD & SPECIFIC ROUTES
# ==============================================================================

@app.route('/resident/dashboard')
@resident_required
def resident_dashboard():
    """Resident Dashboard overview."""
    user_id = session.get('user_id')
    res_info = get_resident_info(user_id)

    if not res_info:
        flash("No active resident record linked to your user account. Please contact society office.", "warning")
        return redirect(url_for('logout'))

    flat_id = res_info['flat_id']
    resident_id = res_info['id']

    # Bills for this flat
    bills = query_db("""
        SELECT * FROM maintenance_bills 
        WHERE flat_id = ? 
        ORDER BY billing_month DESC
    """, (flat_id,))

    pending_bills = [b for b in bills if b['status'] in ('Pending', 'Overdue')]
    pending_amount = sum(b['amount'] + b['penalty'] for b in pending_bills)

    # Payments made for this flat
    payments = query_db("""
        SELECT p.*, b.billing_month, b.bill_no
        FROM payments p
        JOIN maintenance_bills b ON p.bill_id = b.id
        WHERE b.flat_id = ?
        ORDER BY p.payment_date DESC
    """, (flat_id,))
    total_paid = sum(p['amount'] for p in payments)

    # Complaints submitted by this resident
    complaints = query_db("""
        SELECT * FROM complaints 
        WHERE resident_id = ? 
        ORDER BY created_at DESC
    """, (resident_id,))

    # Active society notices
    notices = query_db("""
        SELECT * FROM notices 
        WHERE is_active = 1 
        ORDER BY published_date DESC 
        LIMIT 5
    """)

    return render_template(
        'resident_dashboard.html',
        resident_info=res_info,
        bills=bills,
        pending_bills=pending_bills,
        pending_bills_amount=pending_amount,
        payments=payments,
        total_paid_amount=total_paid,
        complaints=complaints,
        notices=notices,
        active_page='dashboard'
    )

@app.route('/resident/bills')
@resident_required
def resident_bills():
    """Resident bills view."""
    return redirect(url_for('resident_dashboard'))

@app.route('/resident/payments')
@resident_required
def resident_payments():
    """Resident payments view."""
    return redirect(url_for('resident_dashboard'))

@app.route('/resident/complaints')
@resident_required
def resident_complaints():
    """Resident complaints view."""
    return redirect(url_for('resident_dashboard'))

@app.route('/resident/notices')
@resident_required
def resident_notices():
    """Resident notices view."""
    all_notices = query_db("SELECT * FROM notices WHERE is_active = 1 ORDER BY published_date DESC")
    return render_template('notices.html', notices=all_notices, active_page='notices')

@app.route('/resident/pay/<int:bill_id>', methods=['POST'])
@resident_required
def resident_pay_bill(bill_id):
    """Simulated payment processing for residents."""
    user_id = session.get('user_id')
    res_info = get_resident_info(user_id)

    if not res_info:
        flash("Resident record not found.", "danger")
        return redirect(url_for('resident_dashboard'))

    # Verify bill belongs to resident's flat
    bill = query_db("SELECT * FROM maintenance_bills WHERE id = ? AND flat_id = ?", (bill_id, res_info['flat_id']), one=True)
    if not bill:
        flash("Invalid bill or unauthorized action.", "danger")
        return redirect(url_for('resident_dashboard'))

    if bill['status'] == 'Paid':
        flash("This maintenance bill is already paid.", "info")
        return redirect(url_for('resident_dashboard'))

    payment_method = request.form.get('payment_method', 'UPI')
    total_payable = bill['amount'] + bill['penalty']

    # Generate receipt & transaction reference
    now_str = datetime.datetime.now().strftime('%Y%m%d%H%M')
    receipt_no = f"RCT-{datetime.date.today().strftime('%Y%m')}-{bill_id:04d}"
    txn_ref = f"TXN_{payment_method[:3].upper()}_{now_str}_{bill_id}"

    # Insert payment record
    pay_id, _ = execute_db("""
        INSERT INTO payments (receipt_no, bill_id, resident_id, amount, payment_date, payment_method, transaction_id, remarks, status)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, 'Online maintenance settlement via resident portal', 'Success')
    """, (receipt_no, bill_id, res_info['id'], total_payable, payment_method, txn_ref))

    # Mark bill as Paid
    execute_db("UPDATE maintenance_bills SET status = 'Paid' WHERE id = ?", (bill_id,))

    flash(f"Payment successful! ₹{total_payable:,.2f} received via {payment_method}. Official receipt #{receipt_no} generated.", "success")
    return redirect(url_for('view_receipt', payment_id=pay_id))

@app.route('/resident/complaint/submit', methods=['POST'])
@resident_required
def resident_submit_complaint():
    """Resident lodges a maintenance complaint."""
    user_id = session.get('user_id')
    res_info = get_resident_info(user_id)

    if not res_info:
        flash("Resident record not found.", "danger")
        return redirect(url_for('resident_dashboard'))

    category = request.form.get('category', 'Other')
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'Medium')

    if not subject or not description:
        flash("Subject and description are required.", "danger")
        return redirect(url_for('resident_dashboard'))

    execute_db("""
        INSERT INTO complaints (resident_id, flat_id, category, subject, description, priority, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Submitted')
    """, (res_info['id'], res_info['flat_id'], category, subject, description, priority))

    flash("Your complaint has been submitted to the society management desk. You will receive updates here.", "success")
    return redirect(url_for('resident_dashboard'))

# ==============================================================================
# 4. PROFILE & ACCOUNT SETTINGS
# ==============================================================================

@app.route('/profile')
@login_required
def profile():
    """View user profile."""
    user = get_current_user()
    res_info = get_resident_info(user['id']) if user['role'] == 'resident' else None
    return render_template('profile.html', user=user, resident_info=res_info, active_page='profile')

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update profile information."""
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    user_id = session.get('user_id')

    if not full_name or not email:
        flash("Name and email cannot be empty.", "danger")
        return redirect(url_for('profile'))

    execute_db("""
        UPDATE users SET full_name = ?, email = ?, phone = ? WHERE id = ?
    """, (full_name, email, phone, user_id))

    # If resident, also update resident table
    if session.get('role') == 'resident':
        execute_db("""
            UPDATE residents SET full_name = ?, email = ?, phone = ? WHERE user_id = ?
        """, (full_name, email, phone, user_id))

    session['full_name'] = full_name
    flash("Profile information updated successfully.", "success")
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change account password."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    user_id = session.get('user_id')

    user = query_db("SELECT password_hash FROM users WHERE id = ?", (user_id,), one=True)

    if not check_password_hash(user['password_hash'], current_password):
        flash("Current password entered is incorrect.", "danger")
        return redirect(url_for('profile'))

    if len(new_password) < 6:
        flash("New password must be at least 6 characters long.", "danger")
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash("New password and confirm password do not match.", "danger")
        return redirect(url_for('profile'))

    execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), user_id))
    flash("Password updated successfully.", "success")
    return redirect(url_for('profile'))

# ==============================================================================
# 5. ERROR HANDLERS
# ==============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', content="<div class='container py-5 text-center'><h3>Page Not Found (404)</h3><p class='text-muted'>The requested page does not exist.</p><a href='/' class='btn btn-primary btn-sm'>Return Home</a></div>"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('base.html', content="<div class='container py-5 text-center'><h3>Server Error (500)</h3><p class='text-muted'>Something went wrong internally. Please try again.</p><a href='/' class='btn btn-primary btn-sm'>Return Home</a></div>"), 500

# ==============================================================================
# 6. APP INITIALIZATION & ENTRY POINT
# ==============================================================================

if __name__ == '__main__':
    # Initialize database tables and sample data if needed
    with app.app_context():
        init_db()
    print("=" * 60)
    print("  Society Maintenance Management System is starting...")
    print(f"  Society: {Config.SOCIETY_NAME}")
    print("  Admin Login:    username 'admin'    | password 'admin123'")
    print("  Resident Login: username 'resident1'| password 'resident123'")
    print("  URL: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)
