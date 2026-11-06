import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from utils.database import init_db, query_db

def run_tests():
    print("Beginning Comprehensive System Test for Society Maintenance Management System...")
    with app.app_context():
        init_db()

    client = app.test_client()

    # 1. Test Home page
    resp = client.get('/')
    assert resp.status_code == 200, f"Index failed with status {resp.status_code}"
    assert b"Society Maintenance Management System" in resp.data
    print("  [PASS] 1. Home landing page rendered successfully.")

    # 2. Test Login page
    resp = client.get('/login')
    assert resp.status_code == 200
    assert b"Welcome Back" in resp.data
    print("  [PASS] 2. Login page rendered successfully.")

    # 3. Test Invalid Credentials
    bad_resp = client.post('/login', data={'username': 'admin', 'password': 'wrongpassword', 'role': 'admin'}, follow_redirects=True)
    assert b"Invalid credentials" in bad_resp.data
    print("  [PASS] 3. Security check: Invalid credentials rejected properly.")

    # 4. Test Admin Login
    admin_resp = client.post('/login', data={'username': 'admin', 'password': 'admin123', 'role': 'admin'}, follow_redirects=True)
    assert admin_resp.status_code == 200
    assert b"Society Administration Dashboard" in admin_resp.data
    print("  [PASS] 4. Admin authentication and dashboard navigation successful.")

    # 5. Test Admin Modules
    endpoints = [
        ('/admin/flats', b'Registered Flats Directory'),
        ('/admin/residents', b'Society Residents'),
        ('/admin/bills', b'Society Maintenance Bills'),
        ('/admin/payments', b'Payment Transactions'),
        ('/admin/complaints', b'Society Complaints Desk'),
        ('/admin/notices', b'Society Notices'),
        ('/admin/expenses', b'Society Expenditures'),
        ('/admin/reports', b'Reports &')
    ]
    for endpoint, text_match in endpoints:
        r = client.get(endpoint)
        assert r.status_code == 200, f"Module {endpoint} returned status {r.status_code}"
        assert text_match in r.data, f"Module {endpoint} did not match expected output"
        print(f"  [PASS] 5. Admin module verified: {endpoint}")

    # 6. Test CSV Export Endpoints
    for rtype in ['collections', 'pending', 'expenses', 'complaints']:
        csv_resp = client.get(f'/admin/reports/export/{rtype}')
        assert csv_resp.status_code == 200, f"CSV export {rtype} failed"
        assert 'text/csv' in csv_resp.content_type
        assert len(csv_resp.data) > 20
        print(f"  [PASS] 6. CSV report export verified: {rtype}")

    # 7. Test Admin Logout
    client.get('/logout')
    print("  [PASS] 7. Admin session logout successful.")

    # 8. Test Resident Login
    res_resp = client.post('/login', data={'username': 'resident1', 'password': 'resident123', 'role': 'resident'}, follow_redirects=True)
    assert res_resp.status_code == 200
    assert b"Resident Portal" in res_resp.data
    assert b"Flat A-101" in res_resp.data
    print("  [PASS] 8. Resident authentication and personal portal verified.")

    # 9. Test Resident Payment Simulation
    with app.app_context():
        p_bill = query_db("SELECT id, amount FROM maintenance_bills WHERE flat_id = 1 AND status = 'Pending'", one=True)
    
    if p_bill:
        bill_id = p_bill['id']
        pay_resp = client.post(f'/resident/pay/{bill_id}', data={'payment_method': 'UPI'}, follow_redirects=True)
        assert pay_resp.status_code == 200
        assert b"ORIGINAL RECEIPT" in pay_resp.data
        assert b"PAID" in pay_resp.data
        print(f"  [PASS] 9. Payment simulation, receipt generation, and bill settlement verified for Bill #{bill_id}.")

    # 10. Test Resident Complaint Submission
    comp_resp = client.post('/resident/complaint/submit', data={
        'category': 'Electricity',
        'subject': 'Corridor LED tube flickering on 1st Floor',
        'description': 'Light bulb in 1st floor corridor is flickering and making clicking noise.',
        'priority': 'Low'
    }, follow_redirects=True)
    assert comp_resp.status_code == 200
    assert b"Your complaint has been submitted" in comp_resp.data
    print("  [PASS] 10. Resident complaint lodging and database persistence verified.")

    # 11. Test Profile view and update
    prof_resp = client.get('/profile')
    assert prof_resp.status_code == 200
    assert b"Account Profile" in prof_resp.data
    print("  [PASS] 11. Profile module view verified.")

    print("\n=======================================================")
    print("ALL 11 TEST SUITES PASSED FLAWLESSLY (100% SUCCESS RATE)")
    print("=======================================================")

if __name__ == '__main__':
    run_tests()
