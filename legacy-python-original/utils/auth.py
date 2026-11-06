from functools import wraps
from flask import session, redirect, url_for, flash, request, abort
from utils.database import query_db

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for('resident_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def resident_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'resident':
            flash("Please switch to resident account to view this page.", "warning")
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' not in session:
        return None
    user = query_db("SELECT id, username, email, role, full_name, phone, created_at FROM users WHERE id = ?", (session['user_id'],), one=True)
    return user

def get_resident_info(user_id):
    """Retrieve resident and associated flat information for a user."""
    return query_db("""
        SELECT r.*, f.flat_number, f.building_block, f.floor, f.flat_type, f.maintenance_rate
        FROM residents r
        JOIN flats f ON r.flat_id = f.id
        WHERE r.user_id = ?
    """, (user_id,), one=True)
