import os

class Config:
    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Secret Key for session signing
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'society-maintenance-secret-key-mca-project-2026'
    
    # SQLite Database configuration
    DATABASE = os.path.join(BASE_DIR, 'database', 'society.db')
    
    # Society Profile Details for Bills and Receipts
    SOCIETY_NAME = "Greenfield Heights Co-operative Housing Society"
    SOCIETY_TAGLINE = "Registered under Co-operative Societies Act"
    SOCIETY_REG_NO = "CHS/MUM/2020/7890"
    SOCIETY_ADDRESS = "Plot 42, Royal Palm Avenue, Sector 15, Navi Mumbai - 400614"
    SOCIETY_PHONE = "+91 98765 43210"
    SOCIETY_EMAIL = "admin@greenfieldheights.org"
    CURRENCY_SYMBOL = "₹"
