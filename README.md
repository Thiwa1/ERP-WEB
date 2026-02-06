# Suwin Accounting ERP System

A comprehensive web-based ERP system converted from C# WPF to Python Flask. This system manages General Ledger, Accounts Payable/Receivable, Inventory, POS, and Banking.

## Prerequisites

1.  **Python 3.8+**: Ensure Python is installed on your system.
2.  **MySQL Server**: You need a running MySQL instance (e.g., MySQL Community Server or XAMPP).

## Installation Steps

### 1. Clone the Repository
Extract the project files to a directory on your computer.

### 2. Set Up Virtual Environment (Recommended)
It is good practice to run Python applications in an isolated environment.

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install the required Python packages using `pip`.

```bash
pip install -r requirements.txt
```

### 4. Database Setup
1.  Open your MySQL client (Workbench, phpMyAdmin, or Command Line).
2.  Create a new database named `Book_keeping` (or simply import the script which creates it).
3.  Import the provided schema file `database_schema.sql`.
4.  Import the fixed assets schema file `fixed_assets.sql`.

**Command Line Example:**
```bash
mysql -u root -p < database_schema.sql
mysql -u root -p < fixed_assets.sql
```

### 5. Configuration
Open `app.py` and update the `db_config` dictionary at the top of the file to match your MySQL credentials.

```python
db_config = {
    'user': 'root',      # Your MySQL Username
    'password': '',      # Your MySQL Password
    'host': 'localhost',
    'database': 'Book_keeping',
    'raise_on_warnings': True
}
```

*Note: For production, consider using environment variables for sensitive data.*

### 6. Run the Application
Start the Flask development server.

```bash
python app.py
```

You should see output indicating the server is running, typically at `http://127.0.0.1:5000`.

## First Time Login

*   **URL**: Open `http://127.0.0.1:5000` in your web browser.
*   **Default Credentials**:
    *   **Username**: `admin`
    *   **Password**: `123`

*The system automatically creates this admin user and essential General Ledger accounts on the first run if the database is empty.*

## Features Overview

*   **Dashboard**: Tile-based access to all modules.
*   **POS**: Point of Sale system with barcode support and receipt printing.
*   **Inventory**: GRN entry, Stock Cards, and Trend Analysis.
*   **Accounting**: Cash/Bank Payments, Receipts, Journal Vouchers.
*   **Reports**: Balance Sheet, Profit & Loss, Trial Balance, Aging Reports.
*   **Admin**: User management and access control.
