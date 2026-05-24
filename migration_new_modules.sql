-- ============================================================
-- Suwin ERP — New Modules Migration
-- Modules: HR, Payroll, CRM, Email Integration
-- Run once on the target database
-- ============================================================

-- ── EMPLOYEES ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employees (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    emp_no            VARCHAR(20)  NOT NULL UNIQUE,
    first_name        VARCHAR(100) NOT NULL,
    last_name         VARCHAR(100) NOT NULL DEFAULT '',
    nic               VARCHAR(20)  DEFAULT '',
    email             VARCHAR(150) DEFAULT '',
    mobile            VARCHAR(20)  DEFAULT '',
    department        VARCHAR(100) DEFAULT '',
    designation       VARCHAR(100) DEFAULT '',
    date_of_joining   DATE         DEFAULT NULL,
    date_of_birth     DATE         DEFAULT NULL,
    gender            ENUM('Male','Female','Other') DEFAULT 'Male',
    employment_type   ENUM('Permanent','Contract','Probation','Part-Time') DEFAULT 'Permanent',
    basic_salary      DECIMAL(12,2) DEFAULT 0.00,
    epf_no            VARCHAR(50)  DEFAULT '',
    etf_no            VARCHAR(50)  DEFAULT '',
    bank_name         VARCHAR(100) DEFAULT '',
    bank_account_no   VARCHAR(50)  DEFAULT '',
    bank_branch       VARCHAR(100) DEFAULT '',
    is_active         TINYINT(1)   DEFAULT 1,
    created_by        VARCHAR(100) DEFAULT '',
    created_at        DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── PAYROLL COMPONENTS (Allowances / Deductions) ───────────
CREATE TABLE IF NOT EXISTS payroll_components (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    component_name   VARCHAR(100) NOT NULL,
    component_type   ENUM('Allowance','Deduction') NOT NULL DEFAULT 'Allowance',
    is_taxable       TINYINT(1)   DEFAULT 0,
    is_active        TINYINT(1)   DEFAULT 1,
    created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Default components
INSERT IGNORE INTO payroll_components (id, component_name, component_type, is_taxable) VALUES
(1, 'Basic Salary',       'Allowance', 0),
(2, 'Transport Allowance','Allowance', 0),
(3, 'Medical Allowance',  'Allowance', 0),
(4, 'Overtime',           'Allowance', 1),
(5, 'Absence Deduction',  'Deduction', 0),
(6, 'Loan Deduction',     'Deduction', 0);

-- ── EMPLOYEE SALARY STRUCTURE ──────────────────────────────
CREATE TABLE IF NOT EXISTS employee_salary_structure (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    employee_id   INT           NOT NULL,
    component_id  INT           NOT NULL,
    amount        DECIMAL(12,2) DEFAULT 0.00,
    effective_from DATE         DEFAULT NULL,
    FOREIGN KEY (employee_id)  REFERENCES employees(id)           ON DELETE CASCADE,
    FOREIGN KEY (component_id) REFERENCES payroll_components(id)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── PAYROLL RUNS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payroll_runs (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    pay_period_month    INT           NOT NULL,
    pay_period_year     INT           NOT NULL,
    run_date            DATE          DEFAULT NULL,
    status              ENUM('Draft','Processed','Paid') DEFAULT 'Draft',
    total_gross         DECIMAL(14,2) DEFAULT 0.00,
    total_deductions    DECIMAL(14,2) DEFAULT 0.00,
    total_net           DECIMAL(14,2) DEFAULT 0.00,
    created_by          VARCHAR(100)  DEFAULT '',
    created_at          DATETIME      DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_run (pay_period_month, pay_period_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── PAYROLL RUN LINES (individual payslips) ────────────────
CREATE TABLE IF NOT EXISTS payroll_run_lines (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    payroll_run_id   INT           NOT NULL,
    employee_id      INT           NOT NULL,
    basic_salary     DECIMAL(12,2) DEFAULT 0.00,
    total_allowances DECIMAL(12,2) DEFAULT 0.00,
    total_deductions DECIMAL(12,2) DEFAULT 0.00,
    epf_employee     DECIMAL(12,2) DEFAULT 0.00,
    epf_employer     DECIMAL(12,2) DEFAULT 0.00,
    etf_employer     DECIMAL(12,2) DEFAULT 0.00,
    gross_salary     DECIMAL(12,2) DEFAULT 0.00,
    net_salary       DECIMAL(12,2) DEFAULT 0.00,
    status           ENUM('Pending','Paid') DEFAULT 'Pending',
    FOREIGN KEY (payroll_run_id) REFERENCES payroll_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id)    REFERENCES employees(id)    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── LEAVE TYPES ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leave_types (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    leave_name    VARCHAR(100) NOT NULL,
    days_per_year INT          DEFAULT 0,
    is_paid       TINYINT(1)   DEFAULT 1,
    is_active     TINYINT(1)   DEFAULT 1,
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO leave_types (id, leave_name, days_per_year, is_paid) VALUES
(1, 'Annual Leave',    14, 1),
(2, 'Sick Leave',       7, 1),
(3, 'Casual Leave',     6, 1),
(4, 'Maternity Leave', 84, 1),
(5, 'No Pay Leave',     0, 0);

-- ── LEAVE APPLICATIONS ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS leave_applications (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    employee_id      INT           NOT NULL,
    leave_type_id    INT           NOT NULL,
    start_date       DATE          NOT NULL,
    end_date         DATE          NOT NULL,
    days_requested   DECIMAL(4,1)  NOT NULL DEFAULT 1,
    reason           TEXT,
    status           ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
    approved_by      VARCHAR(100)  DEFAULT NULL,
    approved_at      DATETIME      DEFAULT NULL,
    created_at       DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id)   REFERENCES employees(id)   ON DELETE CASCADE,
    FOREIGN KEY (leave_type_id) REFERENCES leave_types(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM LEADS ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crm_leads (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    lead_name            VARCHAR(200) NOT NULL,
    company_name         VARCHAR(200) DEFAULT '',
    email                VARCHAR(150) DEFAULT '',
    mobile               VARCHAR(20)  DEFAULT '',
    source               ENUM('Website','Referral','Cold Call','Walk-in','Social Media','Other') DEFAULT 'Other',
    status               ENUM('New','Contacted','Qualified','Proposal','Won','Lost') DEFAULT 'New',
    assigned_to          VARCHAR(100) DEFAULT '',
    expected_value       DECIMAL(14,2) DEFAULT 0.00,
    expected_close_date  DATE          DEFAULT NULL,
    notes                TEXT,
    created_by           VARCHAR(100)  DEFAULT '',
    created_at           DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── CRM ACTIVITIES ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crm_activities (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    lead_id        INT           NOT NULL,
    activity_type  ENUM('Call','Email','Meeting','Demo','Follow-up','Note') NOT NULL DEFAULT 'Note',
    subject        VARCHAR(200)  DEFAULT '',
    notes          TEXT,
    activity_date  DATETIME      DEFAULT NULL,
    next_follow_up DATE          DEFAULT NULL,
    created_by     VARCHAR(100)  DEFAULT '',
    created_at     DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES crm_leads(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── EMAIL SETTINGS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_settings (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    smtp_host      VARCHAR(200) DEFAULT '',
    smtp_port      INT          DEFAULT 587,
    smtp_username  VARCHAR(200) DEFAULT '',
    smtp_password  VARCHAR(200) DEFAULT '',
    sender_name    VARCHAR(200) DEFAULT '',
    sender_email   VARCHAR(200) DEFAULT '',
    use_tls        TINYINT(1)   DEFAULT 1,
    is_active      TINYINT(1)   DEFAULT 0,
    updated_at     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── EMAIL LOG ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_log (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    recipient_email  VARCHAR(200) DEFAULT '',
    subject          VARCHAR(500) DEFAULT '',
    body             TEXT,
    status           ENUM('Sent','Failed') DEFAULT 'Sent',
    error_message    TEXT         DEFAULT NULL,
    sent_at          DATETIME     DEFAULT CURRENT_TIMESTAMP,
    related_type     VARCHAR(50)  DEFAULT NULL,
    related_id       INT          DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
