CREATE DATABASE IF NOT EXISTS society_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE society_management;

CREATE TABLE IF NOT EXISTS users (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 username VARCHAR(80) NOT NULL UNIQUE,
 email VARCHAR(190) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL,
 role ENUM('admin','resident') NOT NULL,
 full_name VARCHAR(160) NOT NULL,
 phone VARCHAR(40) NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS flats (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 flat_number VARCHAR(30) NOT NULL UNIQUE,
 building_block VARCHAR(30) NOT NULL,
 floor INT NOT NULL DEFAULT 0,
 flat_type VARCHAR(30) NOT NULL DEFAULT '2 BHK',
 maintenance_rate DECIMAL(10,2) NOT NULL DEFAULT 2500,
 status ENUM('Vacant','Occupied') NOT NULL DEFAULT 'Vacant',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS residents (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id INT UNSIGNED NULL UNIQUE,
 flat_id INT UNSIGNED NOT NULL,
 full_name VARCHAR(160) NOT NULL,
 phone VARCHAR(40) NOT NULL,
 email VARCHAR(190) NOT NULL,
 joining_date DATE NOT NULL,
 emergency_contact VARCHAR(160) NULL,
 status ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT fk_resident_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL,
 CONSTRAINT fk_resident_flat FOREIGN KEY(flat_id) REFERENCES flats(id) ON DELETE RESTRICT
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS maintenance_bills (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 bill_no VARCHAR(50) NOT NULL UNIQUE,
 flat_id INT UNSIGNED NOT NULL,
 billing_month CHAR(7) NOT NULL,
 amount DECIMAL(10,2) NOT NULL,
 due_date DATE NOT NULL,
 penalty DECIMAL(10,2) NOT NULL DEFAULT 0,
 status ENUM('Pending','Paid','Overdue') NOT NULL DEFAULT 'Pending',
 notes TEXT NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_flat_month(flat_id,billing_month),
 FOREIGN KEY(flat_id) REFERENCES flats(id) ON DELETE CASCADE,
 INDEX idx_bill_status(status)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS payments (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 receipt_no VARCHAR(50) NOT NULL UNIQUE,
 bill_id INT UNSIGNED NOT NULL,
 resident_id INT UNSIGNED NULL,
 amount DECIMAL(10,2) NOT NULL,
 payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 payment_method ENUM('UPI','Cash','Bank Transfer','Credit/Debit Card','Cheque') NOT NULL DEFAULT 'UPI',
 transaction_id VARCHAR(100) NULL,
 remarks TEXT NULL,
 status ENUM('Success','Failed','Pending') NOT NULL DEFAULT 'Success',
 FOREIGN KEY(bill_id) REFERENCES maintenance_bills(id) ON DELETE CASCADE,
 FOREIGN KEY(resident_id) REFERENCES residents(id) ON DELETE SET NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS staff (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 full_name VARCHAR(160) NOT NULL,
 phone VARCHAR(40) NULL,
 role_title VARCHAR(100) NULL,
 status ENUM('Active','Inactive') NOT NULL DEFAULT 'Active'
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS complaints (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 resident_id INT UNSIGNED NOT NULL,
 flat_id INT UNSIGNED NOT NULL,
 category VARCHAR(80) NOT NULL,
 subject VARCHAR(190) NOT NULL,
 description TEXT NOT NULL,
 priority ENUM('Low','Medium','High','Emergency') NOT NULL DEFAULT 'Medium',
 status ENUM('Submitted','Assigned','In Progress','Resolved','Closed') NOT NULL DEFAULT 'Submitted',
 assigned_staff_id INT UNSIGNED NULL,
 admin_remarks TEXT NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 resolved_at DATETIME NULL,
 FOREIGN KEY(resident_id) REFERENCES residents(id) ON DELETE CASCADE,
 FOREIGN KEY(flat_id) REFERENCES flats(id) ON DELETE CASCADE,
 FOREIGN KEY(assigned_staff_id) REFERENCES staff(id) ON DELETE SET NULL,
 INDEX idx_complaint_status(status)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS notices (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 title VARCHAR(190) NOT NULL,
 message TEXT NOT NULL,
 category VARCHAR(60) NOT NULL DEFAULT 'General',
 published_date DATE NOT NULL,
 expiry_date DATE NULL,
 is_active TINYINT(1) NOT NULL DEFAULT 1,
 created_by INT UNSIGNED NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS expenses (
 id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 expense_no VARCHAR(50) NOT NULL UNIQUE,
 category VARCHAR(100) NOT NULL,
 description TEXT NOT NULL,
 amount DECIMAL(10,2) NOT NULL,
 expense_date DATE NOT NULL,
 paid_to VARCHAR(190) NOT NULL,
 payment_method ENUM('Bank Transfer','UPI','Cheque','Cash') NOT NULL DEFAULT 'Bank Transfer',
 receipt_ref VARCHAR(100) NULL,
 created_by INT UNSIGNED NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;
