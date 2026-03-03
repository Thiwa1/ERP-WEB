import time
import os
import sys

# setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import mocked env
import tests.mock_env
import app

from unittest.mock import patch, MagicMock

def benchmark_loop():
    # simulate 1000 payments
    payments = [{'id': str(i), 'amount': 100.0} for i in range(1000)]

    # Mock cursor
    mock_cursor = MagicMock()
    # mock fetchone to return 500 for outstanding
    mock_cursor.fetchone.return_value = (500,)

    # 4. Process Individual Payments (Update Outstanding)
    start_time = time.time()
    for p in payments:
        mock_cursor.execute("SELECT suppliers_invoice_oustanding FROM suppliers_invoice_data WHERE s_i_id = %s", (p['id'],))
        res = mock_cursor.fetchone()
        current_outstanding = app.parse_float(res[0] or 0)

        # Call Stored Procedure
        mock_cursor.execute("CALL vender_settele(%s, %s, %s)", (current_outstanding, p['amount'], p['id']))

        net_payment = 900
        total_payment = 1000
        net_item_amount = p['amount']
        if total_payment > 0:
            net_item_amount = p['amount'] * (net_payment / total_payment)

        mock_cursor.execute("""
            INSERT INTO cash_book_recode (
                cash_book_recode_dr, cash_book_recode_cr, cash_book_recode_accont_name,
                cash_book_recode_naration, cash_book_recode_suplier_oustanding_id,
                cash_book_recode_suplier_name, jv_numbers_jv_id,
                cash_book_po_no, cash_book_suplier_oustanding_id,
                cash_book_recod_voucher_no, User_Enter, Payment_Date
            ) VALUES (0, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s)
        """, (
            net_item_amount, "cash_account", "narration",
            p['id'], "supplier_name", "jv_no",
            p['id'], "new_voucher", "current_user_pk", "payment_date"
        ))

    end_time = time.time()
    print(f"Time taken for N+1 queries: {end_time - start_time:.4f} seconds")


def benchmark_optimized_loop():
    payments = [{'id': str(i), 'amount': 100.0} for i in range(1000)]

    # Mock cursor
    mock_cursor = MagicMock()
    # mock fetchall to return a list of tuples for outstanding
    mock_cursor.fetchall.return_value = [(str(i), 500.0) for i in range(1000)]

    # 4. Process Individual Payments (Update Outstanding)
    start_time = time.time()

    if payments:
        inv_ids = [p['id'] for p in payments]
        format_strings = ','.join(['%s'] * len(inv_ids))
        mock_cursor.execute(f"SELECT s_i_id, suppliers_invoice_oustanding FROM suppliers_invoice_data WHERE s_i_id IN ({format_strings})", tuple(inv_ids))

        outstanding_map = {}
        for row in mock_cursor.fetchall():
            outstanding_map[str(row[0])] = app.parse_float(row[1] or 0)

        call_params = []
        insert_params = []

        net_payment = 900
        total_payment = 1000

        for p in payments:
            current_outstanding = outstanding_map.get(str(p['id']), 0.0)
            call_params.append((current_outstanding, p['amount'], p['id']))

            net_item_amount = p['amount']
            if total_payment > 0:
                net_item_amount = p['amount'] * (net_payment / total_payment)

            insert_params.append((
                net_item_amount, "cash_account", "narration",
                p['id'], "supplier_name", "jv_no",
                p['id'], "new_voucher", "current_user_pk", "payment_date"
            ))

        mock_cursor.executemany("CALL vender_settele(%s, %s, %s)", call_params)

        mock_cursor.executemany("""
            INSERT INTO cash_book_recode (
                cash_book_recode_dr, cash_book_recode_cr, cash_book_recode_accont_name,
                cash_book_recode_naration, cash_book_recode_suplier_oustanding_id,
                cash_book_recode_suplier_name, jv_numbers_jv_id,
                cash_book_po_no, cash_book_suplier_oustanding_id,
                cash_book_recod_voucher_no, User_Enter, Payment_Date
            ) VALUES (0, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s)
        """, insert_params)

    end_time = time.time()
    print(f"Time taken for optimized bulk queries: {end_time - start_time:.4f} seconds")


if __name__ == '__main__':
    benchmark_loop()
    benchmark_optimized_loop()
