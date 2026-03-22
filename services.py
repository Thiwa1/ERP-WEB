
from datetime import date

def create_grn(db, current_user, supplier_info, invoice_info, items):
    """
    Creates a Goods Received Note (GRN) transaction.

    Args:
        db: Database instance
        current_user: User ID creating the GRN
        supplier_info: dict containing 'code' and 'id'
        invoice_info: dict containing invoice details
        items: list of item dictionaries

    Returns:
        int: The generated JV number
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    conn.start_transaction()

    try:
        # A. Generate JV Number
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)",
                       ('JV FROM GRN', invoice_info['narration']))
        jv_no = cursor.lastrowid

        # B. Insert Invoice Record
        query_inv = """
            INSERT INTO suppliers_invoice_data (
                suppliers_code, suppliers_invoice_number, suppliers_invoice_date,
                suppliers_invoice_total_oustanding, suppliers_invoice_final_date,
                suppliers_invoice_buinding_supplier, suppliers_invoice_JV, suppliers_VAT_rate, suppliers_invoice_total_payment
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
        """
        cursor.execute(query_inv, (
            supplier_info['code'],
            invoice_info['no'],
            invoice_info['date'],
            invoice_info['grand_total'],
            invoice_info['due_date'],
            supplier_info['id'],
            jv_no,
            invoice_info['vat_rate']
        ))

        # C. Journal Entries
        # C1. Credit Account Payable (Grand Total)
        job_no = invoice_info['job_no'] if invoice_info['job_no'] else None

        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_job_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Account Payable', invoice_info['grand_total'], invoice_info['date'], date.today(), invoice_info['narration'], current_user, jv_no, job_no))

        # C2. Debit Inventory (Total Value)
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_job_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Inventory', invoice_info['total_value'], invoice_info['date'], date.today(), invoice_info['narration'], current_user, jv_no, job_no))

        # C3. Debit VAT Control (if applicable)
        if invoice_info['vat_amount'] > 0:
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_DR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv, entry_job_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, ('VAT Control', invoice_info['vat_amount'], invoice_info['date'], date.today(), invoice_info['narration'], current_user, jv_no, job_no))

        # D. Inventory Records
        for item in items:
            query_ir = """
                INSERT INTO inventory_recod (
                    inventoy_name, inventoy_code, inventory_recod_mesrmet,
                    inventory_recod_unit_price, inventory_recod_moument_in, inventory_recod_movment_out,
                    inventory_recod_suplier_iv_no, inventory_recod_user_id, inventory_recod_user_recod_date,
                    inventory_recod_location, inventory_recod_link_invoice, inventory_recod_action_date, JV_No
                ) VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_ir, (
                item['name'], item['code'], item['unit'], item['cost'], item['qty'],
                invoice_info['no'], current_user, date.today(), invoice_info['location'], jv_no, invoice_info['date'], jv_no
            ))

        conn.commit()
        return jv_no

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
