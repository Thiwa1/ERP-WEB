# Book Keeping ERP System Database Schema

This repository contains the database schema for a Book Keeping ERP system. The schema is designed for MySQL.

## Overview

The database `Book_keeping` handles various aspects of an ERP system including:
- General Ledger (Accounts, Entries)
- Accounts Payable (Suppliers, Invoices)
- Accounts Receivable (Customers, Invoices)
- Cash and Bank Management (Cash Book, Bank Book, Reconciliation)
- Inventory Management (Items, Categories, Locations, Movements)
- Point of Sale (POS)
- User Management and Rights

## Key Tables

### General Ledger & Setup
- **`company`**: Stores company details.
- **`new_account_table`**: The Chart of Accounts. It categorizes accounts into Income, Expenses, Assets, Liabilities, and Equity.
- **`balance_sheet_category`**: Categories for Balance Sheet accounts.
- **`p&l_category`**: Categories for Profit & Loss accounts.
- **`entry_details`**: Stores individual accounting entries (debits/credits).
- **`jv_numbers`**: Manages Journal Voucher numbers and metadata.

### Cash & Bank
- **`cash_book`**: Defines cash book accounts.
- **`cash_book_recode`**: Records transactions in the cash book.
- **`bank_book`**: Defines bank accounts.
- **`bank_book_recod`**: Records transactions in the bank book.
- **`bank_reconciliation_recodes`** & **`BankReconciliiationDitails`**: For bank reconciliation processes.

### Inventory
- **`inventoy_items`**: Master table for inventory items.
- **`inventory_carogory`**: Categories for inventory items.
- **`inventory_locations`**: Locations/Warehouses for inventory.
- **`inventory_recod`**: Transaction table for inventory movements (In/Out).
- **`inventory_price_recod`**: Pricing history for items.

### Suppliers (AP) & Customers (AR)
- **`suppliers`**: Supplier master data.
- **`suppliers_invoice_data`**: Supplier invoices and outstanding balances.
- **`customer`**: Customer master data.
- **`customer_invoice_data`**: Customer invoices and outstanding balances.
- **`Invoice_Oustanding`**: Tracks outstanding invoices.

### Sales & POS
- **`POS_Sales_Invoice_01`**: Sales transactions from Point of Sale.
- **`Pose_Setting_Table`**: Settings for the POS system.

### User Management
- **`Login_Table`**: User credentials.
- **`User_Rights`**: Permissions for users.

## Stored Procedures

The schema includes numerous stored procedures for business logic, such as:
- **`Bank_Transaction Revesale`**: Reversing bank transactions.
- **`Inventory_Delete`**: Handling inventory deletions.
- **`bank_book_balance`**: Calculating bank book balances.
- **`closing_inventory`**: Calculating closing inventory value.
- **`cost_goods`**: Calculating Cost of Goods Sold (COGS).
- **`income`**, **`expenses`**: Reporting procedures.

## Triggers

- **`new_account_table_BEFORE_INSERT` / `UPDATE`**: Automatically sets the account basement (DR/CR) based on the account type (Income, Expense, Asset, Liability, Equity).

## File Structure

- `database_schema.sql`: The full MySQL Forward Engineering script.
- `README.md`: This documentation.
