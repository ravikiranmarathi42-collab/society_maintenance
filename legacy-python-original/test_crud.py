import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from utils.database import query_db

def test_crud_operations():
    print("Testing CRUD operations...")
    with app.app_context():
        from utils.database import execute_db
        execute_db("DELETE FROM residents WHERE email = 'suresh.raina@example.com'")
        execute_db("DELETE FROM users WHERE username = 'suresh'")
        execute_db("DELETE FROM maintenance_bills WHERE flat_id IN (SELECT id FROM flats WHERE flat_number = 'D-401')")
        execute_db("DELETE FROM flats WHERE flat_number = 'D-401'")
        execute_db("DELETE FROM notices WHERE title = 'Diwali Lighting Ceremony'")
        execute_db("DELETE FROM expenses WHERE description LIKE '%water tanker%'")

    client = app.test_client()

    # Login as Admin
    client.post('/login', data={'username': 'admin', 'password': 'admin123', 'role': 'admin'}, follow_redirects=True)

    # 1. Add Flat
    r = client.post('/admin/flats/add', data={
        'flat_number': 'D-401',
        'building_block': 'D',
        'floor': 4,
        'flat_type': '3 BHK',
        'maintenance_rate': 4800.0,
        'status': 'Vacant'
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        flat = query_db("SELECT * FROM flats WHERE flat_number = 'D-401'", one=True)
        assert flat is not None
        print(f"  [PASS] Added Flat D-401 (ID: {flat['id']})")

    # 2. Edit Flat
    r = client.post(f"/admin/flats/edit/{flat['id']}", data={
        'flat_number': 'D-401',
        'building_block': 'D',
        'floor': 4,
        'flat_type': '3 BHK',
        'maintenance_rate': 5000.0,
        'status': 'Vacant'
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        updated_flat = query_db(f"SELECT maintenance_rate FROM flats WHERE id = {flat['id']}", one=True)
        assert updated_flat['maintenance_rate'] == 5000.0
        print("  [PASS] Edited Flat D-401 maintenance rate to 5000.0")

    # 3. Add Resident to D-401
    r = client.post('/admin/residents/add', data={
        'full_name': 'Suresh Raina',
        'phone': '+91 98989 12345',
        'email': 'suresh.raina@example.com',
        'flat_id': flat['id'],
        'joining_date': '2026-10-24',
        'emergency_contact': 'Priyanka (+91 98989 99999)',
        'username': 'suresh',
        'password': 'resident123'
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        res = query_db("SELECT * FROM residents WHERE email = 'suresh.raina@example.com'", one=True)
        assert res is not None
        assert res['flat_id'] == flat['id']
        flat_occ = query_db(f"SELECT status FROM flats WHERE id = {flat['id']}", one=True)
        assert flat_occ['status'] == 'Occupied'
        print(f"  [PASS] Added Resident Suresh Raina (ID: {res['id']}), flat auto-marked Occupied")

    # 4. Generate Single Bill
    r = client.post('/admin/bills/generate-single', data={
        'flat_id': flat['id'],
        'billing_month': '2026-12',
        'due_date': '2026-12-15',
        'amount': 5000.0,
        'notes': 'Advance December Maintenance'
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        bill = query_db(f"SELECT * FROM maintenance_bills WHERE flat_id = {flat['id']} AND billing_month = '2026-12'", one=True)
        assert bill is not None
        print(f"  [PASS] Generated Bill #{bill['bill_no']}")

    # 5. Record Offline Payment
    r = client.post('/admin/payments/record', data={
        'bill_id': bill['id'],
        'amount': 5000.0,
        'payment_method': 'Cash',
        'transaction_id': 'CASH-OFFICE-REC',
        'payment_date': '2026-10-24'
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        paid_bill = query_db(f"SELECT status FROM maintenance_bills WHERE id = {bill['id']}", one=True)
        assert paid_bill['status'] == 'Paid'
        print(f"  [PASS] Admin recorded Cash payment, Bill #{bill['bill_no']} updated to Paid")

    # 6. Bulk Generate Bills for next month
    r = client.post('/admin/bills/generate-bulk', data={
        'billing_month': '2027-01',
        'due_date': '2027-01-15',
        'notes': 'January 2027 Society Maintenance'
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        jan_count = query_db("SELECT COUNT(*) as c FROM maintenance_bills WHERE billing_month = '2027-01'", one=True)['c']
        assert jan_count > 0
        print(f"  [PASS] Bulk bill generation created {jan_count} bills for 2027-01")

    # 7. Add Notice
    r = client.post('/admin/notices/add', data={
        'title': 'Diwali Lighting Ceremony',
        'category': 'Event',
        'published_date': '2026-10-24',
        'expiry_date': '2026-11-05',
        'message': 'All residents are invited to the lighting ceremony.'
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        notice = query_db("SELECT * FROM notices WHERE title = 'Diwali Lighting Ceremony'", one=True)
        assert notice is not None
        print(f"  [PASS] Published notice: {notice['title']}")

    # 8. Add Expense
    r = client.post('/admin/expenses/add', data={
        'category': 'Water Supply & Tanker',
        'description': 'Emergency water tanker delivery (10,000L)',
        'amount': 2500.0,
        'expense_date': '2026-10-24',
        'paid_to': 'Shiv Water Suppliers',
        'payment_method': 'UPI',
        'receipt_ref': 'TANKER-9912'
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        exp = query_db("SELECT * FROM expenses WHERE description LIKE '%water tanker%'", one=True)
        assert exp is not None
        print(f"  [PASS] Recorded expense voucher: #{exp['expense_no']} (INR {exp['amount']})")

    # 9. Clean up test resident and flat
    client.post(f"/admin/residents/delete/{res['id']}", follow_redirects=True)
    client.post(f"/admin/flats/delete/{flat['id']}", follow_redirects=True)
    print("  [PASS] Cleaned up temporary test records.")

    print("\nALL CRUD OPERATIONS VALIDATED WITH 100% INTEGRITY!")

if __name__ == '__main__':
    test_crud_operations()
