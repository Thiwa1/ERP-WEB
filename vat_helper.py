class VATReportGenerator:
    def __init__(self, db, from_date, to_date):
        self.db = db
        self.from_date = from_date
        self.to_date = to_date

    def check_vat_registered(self):
        """Checks if the company is VAT Registered."""
        comp_res = self.db.execute_query("SELECT vat_registered FROM company LIMIT 1")
        if comp_res and comp_res[0].get('vat_registered') == 1:
            return True
        return False

    def generate_schedule_01(self):
        """Schedule 01 - Output Tax (Sales)"""
        schedule_01 = []
        total_output_value = 0
        total_output_vat = 0

        # A. Credit Sales
        query_credit_sales = """
            SELECT
                io.invoice_date as date,
                io.invoice_number as invoice_no,
                s.customer_name as purchaser,
                s.customer_code as tin,
                io.invoice_total_oustanding as total,
                io.VAT_rate as rate
            FROM Invoice_Oustanding io
            JOIN customer s ON io.invoice_buinding_Customer = s.id
            WHERE io.invoice_date BETWEEN %s AND %s AND io.VAT_rate > 0
        """
        credit_sales = self.db.execute_query(query_credit_sales, (self.from_date, self.to_date))

        for r in credit_sales:
            rate = float(r['rate'] or 0)
            total = float(r['total'] or 0)
            net = total / (1 + (rate / 100))
            vat = total - net

            schedule_01.append({
                'date': str(r['date']),
                'invoice_no': r['invoice_no'],
                'purchaser': r['purchaser'],
                'tin': r['tin'],
                'description': 'Credit Sale',
                'value': net,
                'vat': vat
            })
            total_output_value += net
            total_output_vat += vat

        # B. POS Sales
        query_pos_vat = """
            SELECT
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_CR as vat_amount,
                (SELECT SUM(Total_Value) FROM pos_sales_invoice_01 WHERE jv = ed.entry_jv) as gross_total,
                (SELECT Invoice_No FROM pos_sales_invoice_01 WHERE jv = ed.entry_jv LIMIT 1) as invoice_no
            FROM entry_details ed
            WHERE ed.account_name = 'VAT Control'
            AND ed.enty_values_CR > 0
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE 'VAT%%POS%%'
        """
        pos_sales = self.db.execute_query(query_pos_vat, (self.from_date, self.to_date))

        for r in pos_sales:
            vat = float(r['vat_amount'] or 0)
            gross = float(r['gross_total'] or 0)
            net = gross - vat

            schedule_01.append({
                'date': str(r['date']),
                'invoice_no': r['invoice_no'] or 'POS',
                'purchaser': 'Cash Customer',
                'tin': '-',
                'description': 'POS Sale',
                'value': net,
                'vat': vat
            })
            total_output_value += net
            total_output_vat += vat

        return {
            'rows': schedule_01,
            'total_value': total_output_value,
            'total_vat': total_output_vat
        }

    def generate_schedule_02(self):
        """Schedule 02 - Input Tax (Purchases)"""
        schedule_02 = []
        total_input_value = 0
        total_input_vat = 0

        # Credit Purchases
        query_purchases = """
            SELECT
                sid.suppliers_invoice_date as date,
                sid.suppliers_invoice_number as invoice_no,
                s.supplier_name as supplier,
                s.suppliers_TIN as tin,
                sid.suppliers_invoice_total_oustanding as total,
                sid.suppliers_VAT_rate as rate,
                sid.suppliers_invoice_JV
            FROM suppliers_invoice_data sid
            JOIN suppliers s ON sid.suppliers_invoice_buinding_supplier = s.sup_id
            WHERE sid.suppliers_invoice_date BETWEEN %s AND %s AND sid.suppliers_VAT_rate > 0
        """
        credit_purchases = self.db.execute_query(query_purchases, (self.from_date, self.to_date))

        covered_jvs = []

        for r in credit_purchases:
            rate = float(r['rate'] or 0)
            total = float(r['total'] or 0)
            net = total / (1 + (rate / 100))
            vat = total - net

            if r['suppliers_invoice_JV']:
                covered_jvs.append(str(r['suppliers_invoice_JV']))

            schedule_02.append({
                'date': str(r['date']),
                'invoice_no': r['invoice_no'],
                'supplier': r['supplier'],
                'tin': r['tin'],
                'description': 'Purchase',
                'value': net,
                'vat': vat,
                'disallowed_vat': 0.0
            })
            total_input_value += net
            total_input_vat += vat

        # Other/Direct Input Tax (GL)
        query_other_input = """
            SELECT
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_DR as vat_amount,
                ed.entry_jv
            FROM entry_details ed
            WHERE ed.account_name = 'VAT Control'
            AND ed.enty_values_DR > 0
            AND ed.entry_effective_date BETWEEN %s AND %s
        """
        params_other = [self.from_date, self.to_date]

        if covered_jvs:
            placeholders = ','.join(['%s'] * len(covered_jvs))
            query_other_input += f" AND ed.entry_jv NOT IN ({placeholders})"
            params_other.extend(covered_jvs)

        query_other_input += " AND ed.entry_naration NOT LIKE '%%Import%%' AND ed.entry_naration NOT LIKE '%%Amendment%%'"

        other_inputs = self.db.execute_query(query_other_input, tuple(params_other))

        for r in other_inputs:
            vat = float(r['vat_amount'] or 0)
            schedule_02.append({
                'date': str(r['date']),
                'invoice_no': f"JV-{r['entry_jv']}",
                'supplier': 'Other/Direct',
                'tin': '-',
                'description': r['narration'],
                'value': 0,
                'vat': vat,
                'disallowed_vat': 0.0
            })
            total_input_vat += vat

        return {
            'rows': schedule_02,
            'total_value': total_input_value,
            'total_vat': total_input_vat
        }

    def generate_schedule_03(self):
        """Schedule 03 - Input Schedule for Imports"""
        query_sched03 = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as cusdec_no,
                ed.entry_job_number as serial_id,
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_DR as vat_upfront
            FROM entry_details ed
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            WHERE ed.account_name = 'VAT Control'
            AND ed.enty_values_DR > 0
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE '%%Import%%'
            AND ed.entry_naration NOT LIKE '%%Amendment%%'
        """
        sched03_rows = self.db.execute_query(query_sched03, (self.from_date, self.to_date))
        schedule_03 = []
        total_sched03_vat = 0

        for i, r in enumerate(sched03_rows):
            vat = float(r['vat_upfront'] or 0)
            schedule_03.append({
                'serial_no': i + 1,
                'cusdec_date': str(r['date']),
                'cusdec_no': r['cusdec_no'],
                'cusdec_serial_id': r['serial_id'] or '-',
                'cusdec_reg_date': str(r['date']),
                'cusdec_office_id': '-',
                'vat_deferred': 0.0,
                'vat_upfront': vat,
                'disallowed': 0.0
            })
            total_sched03_vat += vat

        return {
            'rows': schedule_03,
            'total_vat': total_sched03_vat
        }

    def generate_schedule_04(self):
        """Schedule 04 - Credit/Debit Notes"""
        schedule_04 = []
        total_sched04_value = 0
        total_sched04_vat = 0

        # A. POS Reversals (Credit Notes)
        query_pos_reversals = """
            SELECT
                p.AcctionDate as date,
                p.Invoice_No as invoice_no,
                p.Total_Value as total,
                p.jv,
                (SELECT rate FROM tax_rates WHERE tax_name LIKE '%VAT%' AND active=1 LIMIT 1) as rate
            FROM pos_sales_invoice_01 p
            WHERE p.Revers = 1
            AND p.AcctionDate BETWEEN %s AND %s
        """
        pos_reversals = self.db.execute_query(query_pos_reversals, (self.from_date, self.to_date))

        for r in pos_reversals:
            rate = 18.0
            if r['rate']: rate = float(r['rate'])

            total = float(r['total'] or 0)
            net = total / (1 + (rate / 100))
            vat = total - net

            schedule_04.append({
                'tin': '-',
                'invoice_date': str(r['date']),
                'invoice_no': r['invoice_no'],
                'type': 'Credit Note',
                'note_date': str(r['date']),
                'note_no': f"CN-{r['jv']}",
                'value': net,
                'vat': vat,
                'issued_by_me': True
            })
            total_sched04_value += net
            total_sched04_vat += vat

        return {
            'rows': schedule_04,
            'total_value': total_sched04_value,
            'total_vat': total_sched04_vat
        }

    def generate_schedule_05(self):
        """Schedule 05 - Deemed Input"""
        schedule_05 = []
        total_sched05_liable = 0
        total_sched05_non_liable = 0
        total_sched05_credit = 0

        # Get standard VAT rate
        rate_res = self.db.execute_query("SELECT rate FROM tax_rates WHERE tax_name LIKE '%VAT%' AND active=1 LIMIT 1")
        std_rate = float(rate_res[0]['rate']) if rate_res else 18.0
        deemed_factor = std_rate / (100 + std_rate)

        query_deemed = """
            SELECT
                sid.suppliers_invoice_date as date,
                sid.suppliers_invoice_number as invoice_no,
                s.supplier_name as supplier,
                s.suppliers_NIC as nic,
                s.suppliers_vat_regidter_no as tax_file,
                sid.suppliers_invoice_total_oustanding as total
            FROM suppliers_invoice_data sid
            JOIN suppliers s ON sid.suppliers_invoice_buinding_supplier = s.sup_id
            WHERE sid.suppliers_invoice_date BETWEEN %s AND %s
            AND (s.suppliers_vat_regidter_no IS NULL OR s.suppliers_vat_regidter_no = '')
        """
        deemed_purchases = self.db.execute_query(query_deemed, (self.from_date, self.to_date))

        for r in deemed_purchases:
            total = float(r['total'] or 0)
            cost_liable = total
            cost_non_liable = 0
            deemed_credit = cost_liable * deemed_factor

            schedule_05.append({
                'date': str(r['date']),
                'invoice_no': r['invoice_no'],
                'nic': r['nic'],
                'brc': '',
                'tax_file': r['tax_file'],
                'supplier': r['supplier'],
                'cost_liable': cost_liable,
                'cost_non_liable': cost_non_liable,
                'deemed_credit': deemed_credit,
                'disallowed': 0.0
            })

            total_sched05_liable += cost_liable
            total_sched05_non_liable += cost_non_liable
            total_sched05_credit += deemed_credit

        return {
            'rows': schedule_05,
            'total_liable': total_sched05_liable,
            'total_non_liable': total_sched05_non_liable,
            'total_credit': total_sched05_credit
        }

    def generate_schedule_07(self):
        """Schedule 07 - Service Export Schedule"""
        schedule_07 = []
        query_sched07 = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as invoice_no,
                ed.entry_effective_date as date,
                ed.entry_naration as description,
                ed.fc_amount,
                ed.currency_code,
                ed.exchange_rate,
                ed.enty_values_CR as lkr_value
            FROM entry_details ed
            JOIN new_account_table acc ON ed.account_name = acc.account_name
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            WHERE acc.account_income = 1
            AND ed.currency_code IS NOT NULL
            AND ed.currency_code != 'LKR'
            AND ed.entry_effective_date BETWEEN %s AND %s
        """
        sched07_rows = self.db.execute_query(query_sched07, (self.from_date, self.to_date))

        for r in sched07_rows:
            nrfc_acc = ""
            payment_date = ""

            dr_res = self.db.execute_query("SELECT account_name FROM entry_details WHERE entry_jv = %s AND enty_values_DR > 0", (r['entry_jv'],))

            for dr in dr_res:
                chk_bank = self.db.execute_query("SELECT bank_bookcol_account_number FROM bank_book WHERE bank_bookcol_account_number = %s", (dr['account_name'],))
                if chk_bank:
                    nrfc_acc = dr['account_name']
                    payment_date = str(r['date'])
                    break

            if not nrfc_acc:
                payment_date = "Receivable"

            schedule_07.append({
                'invoice_no': r['invoice_no'],
                'date': str(r['date']),
                'description': r['description'],
                'fc_value': float(r['fc_amount'] or 0),
                'currency': r['currency_code'],
                'rate': float(r['exchange_rate'] or 1),
                'lkr_value': float(r['lkr_value'] or 0),
                'nrfc_account': nrfc_acc,
                'payment_date': payment_date
            })

        return {
            'rows': schedule_07
        }

    def _generate_amendment_01(self):
        """Schedule 01 Amendment (Output Tax)"""
        query_amd = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as invoice_no,
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_CR as vat_amount
            FROM entry_details ed
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            WHERE ed.account_name = 'VAT Control'
            AND ed.enty_values_CR > 0
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE '%%Amendment%%'
        """
        amd_rows = self.db.execute_query(query_amd, (self.from_date, self.to_date))
        schedule_01_amendment = []
        total_sched01_amd_value = 0
        total_sched01_amd_vat = 0

        for r in amd_rows:
            vat = float(r['vat_amount'] or 0)

            income_res = self.db.execute_query("""
                SELECT SUM(enty_values_CR) as income_val
                FROM entry_details ed
                JOIN new_account_table na ON ed.account_name = na.account_name
                WHERE ed.entry_jv = %s AND na.account_income = 1
            """, (r['entry_jv'],))

            value = 0
            if income_res and income_res[0]['income_val']:
                value = float(income_res[0]['income_val'])
            else:
                value = vat / 0.18

            schedule_01_amendment.append({
                'indicator': 'A',
                'date': str(r['date']),
                'invoice_no': r['invoice_no'],
                'tin': '-',
                'purchaser': 'Manual Amendment',
                'description': r['narration'],
                'value': value,
                'vat': vat
            })
            total_sched01_amd_value += value
            total_sched01_amd_vat += vat

        return {
            'schedule_01_amendment': schedule_01_amendment,
            'total_sched01_amd_value': total_sched01_amd_value,
            'total_sched01_amd_vat': total_sched01_amd_vat
        }

    def _generate_amendment_02(self):
        """Schedule 02 Amendment (Input Tax)"""
        query_amd_input = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as invoice_no,
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_DR as vat_amount
            FROM entry_details ed
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            WHERE ed.account_name = 'VAT Control'
            AND ed.enty_values_DR > 0
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE '%%Amendment%%'
            AND ed.entry_naration NOT LIKE '%%Import%%'
        """
        amd_input_rows = self.db.execute_query(query_amd_input, (self.from_date, self.to_date))
        schedule_02_amendment = []
        total_sched02_amd_value = 0
        total_sched02_amd_vat = 0

        for r in amd_input_rows:
            vat = float(r['vat_amount'] or 0)

            exp_res = self.db.execute_query("""
                SELECT SUM(enty_values_DR) as exp_val
                FROM entry_details ed
                JOIN new_account_table na ON ed.account_name = na.account_name
                WHERE ed.entry_jv = %s AND (na.account_expenses = 1 OR na.account_assets = 1)
            """, (r['entry_jv'],))

            value = 0
            if exp_res and exp_res[0]['exp_val']:
                value = float(exp_res[0]['exp_val'])
            else:
                value = vat / 0.18

            schedule_02_amendment.append({
                'indicator': 'A',
                'date': str(r['date']),
                'invoice_no': r['invoice_no'],
                'tin': '-',
                'supplier': 'Manual Amendment',
                'description': r['narration'],
                'value': value,
                'vat': vat,
                'disallowed_vat': 0.0
            })
            total_sched02_amd_value += value
            total_sched02_amd_vat += vat

        return {
            'schedule_02_amendment': schedule_02_amendment,
            'total_sched02_amd_value': total_sched02_amd_value,
            'total_sched02_amd_vat': total_sched02_amd_vat
        }

    def _generate_amendment_03(self):
        """Schedule 03 Amendment (Imports)"""
        query_sched03_amd = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as cusdec_no,
                ed.entry_job_number as serial_id,
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_DR as vat_upfront
            FROM entry_details ed
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            WHERE ed.account_name = 'VAT Control'
            AND ed.enty_values_DR > 0
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE '%%Amendment%%'
            AND ed.entry_naration LIKE '%%Import%%'
        """
        sched03_amd_rows = self.db.execute_query(query_sched03_amd, (self.from_date, self.to_date))
        schedule_03_amendment = []
        total_sched03_amd_vat = 0

        for i, r in enumerate(sched03_amd_rows):
            vat = float(r['vat_upfront'] or 0)
            schedule_03_amendment.append({
                'indicator': 'A',
                'serial_no': i + 1,
                'cusdec_date': str(r['date']),
                'cusdec_no': r['cusdec_no'],
                'cusdec_serial_id': r['serial_id'] or '-',
                'cusdec_reg_date': str(r['date']),
                'cusdec_office_id': '-',
                'vat_deferred': 0.0,
                'vat_upfront': vat,
                'disallowed': 0.0
            })
            total_sched03_amd_vat += vat

        return {
            'schedule_03_amendment': schedule_03_amendment,
            'total_sched03_amd_vat': total_sched03_amd_vat
        }

    def _generate_amendment_04(self):
        """Schedule 04 Amendment (Credit/Debit Notes)"""
        query_sched04_amd = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as ref_no,
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_DR as dr,
                ed.enty_values_CR as cr
            FROM entry_details ed
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            WHERE ed.account_name = 'VAT Control'
            AND (ed.enty_values_DR > 0 OR ed.enty_values_CR > 0)
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE '%%Amendment%%'
            AND (ed.entry_naration LIKE '%%Credit Note%%' OR ed.entry_naration LIKE '%%Debit Note%%')
        """
        sched04_amd_rows = self.db.execute_query(query_sched04_amd, (self.from_date, self.to_date))
        schedule_04_amendment = []
        total_sched04_amd_value = 0
        total_sched04_amd_vat = 0

        for r in sched04_amd_rows:
            dr = float(r['dr'] or 0)
            cr = float(r['cr'] or 0)
            vat = dr + cr

            note_type = "Credit Note"
            if "Debit Note" in r['narration']: note_type = "Debit Note"
            elif "Credit Note" in r['narration']: note_type = "Credit Note"

            value = vat / 0.18
            issued_by_me = True

            schedule_04_amendment.append({
                'type': note_type,
                'date': str(r['date']),
                'note_no': f"{note_type} - {r['ref_no']} (Amd)",
                'value': value,
                'vat': vat,
                'issued_by_me': issued_by_me
            })
            total_sched04_amd_value += value
            total_sched04_amd_vat += vat

        return {
            'schedule_04_amendment': schedule_04_amendment,
            'total_sched04_amd_value': total_sched04_amd_value,
            'total_sched04_amd_vat': total_sched04_amd_vat
        }

    def _generate_amendment_05(self):
        """Schedule 05 Amendment (Deemed Input)"""
        rate_res = self.db.execute_query("SELECT rate FROM tax_rates WHERE tax_name LIKE '%VAT%' AND active=1 LIMIT 1")
        std_rate = float(rate_res[0]['rate']) if rate_res else 18.0
        calc_factor = (100 + std_rate) / std_rate if std_rate > 0 else 0

        query_sched05_amd = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as ref_no,
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_DR as vat_amount
            FROM entry_details ed
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            WHERE ed.account_name = 'VAT Control'
            AND ed.enty_values_DR > 0
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE '%%Amendment%%'
            AND ed.entry_naration LIKE '%%Deemed%%'
        """
        sched05_amd_rows = self.db.execute_query(query_sched05_amd, (self.from_date, self.to_date))
        schedule_05_amendment = []
        total_sched05_amd_credit = 0

        for r in sched05_amd_rows:
            vat = float(r['vat_amount'] or 0)
            cost_liable = vat * calc_factor

            schedule_05_amendment.append({
                'indicator': 'A',
                'serial_no': r['ref_no'],
                'date': str(r['date']),
                'invoice_no': '-',
                'nic': '-',
                'brc': '-',
                'tax_file': '-',
                'supplier': 'Manual Amendment',
                'description': r['narration'],
                'cost_liable': cost_liable,
                'cost_non_liable': 0.0,
                'deemed_credit': vat,
                'disallowed': 0.0
            })
            total_sched05_amd_credit += vat

        return {
            'schedule_05_amendment': schedule_05_amendment,
            'total_sched05_amd_credit': total_sched05_amd_credit
        }

    def _generate_amendment_06(self):
        """Schedule 06 Amendment (Goods Export)"""
        query_sched06_amd = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as ref_no,
                ed.entry_effective_date as date,
                ed.entry_naration as narration,
                ed.enty_values_CR as lkr_value
            FROM entry_details ed
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            JOIN new_account_table acc ON ed.account_name = acc.account_name
            WHERE acc.account_income = 1
            AND ed.enty_values_CR > 0
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE '%%Amendment%%'
            AND ed.entry_naration LIKE '%%Export%%'
            AND ed.entry_naration LIKE '%%Goods%%'
        """
        sched06_amd_rows = self.db.execute_query(query_sched06_amd, (self.from_date, self.to_date))
        schedule_06_amendment = []

        for i, r in enumerate(sched06_amd_rows):
            val = float(r['lkr_value'] or 0)
            schedule_06_amendment.append({
                'indicator': 'A',
                'serial_no': i + 1,
                'date': str(r['date']),
                'cusdec_no': '-',
                'office_id': '-',
                'serial_id': '-',
                'mass': 0.0,
                'value': val,
                'nrfc': '-',
                'payment_date': '-'
            })

        return {
            'schedule_06_amendment': schedule_06_amendment
        }

    def _generate_amendment_07(self):
        """Schedule 07 Amendment (Service Export)"""
        query_sched07_amd = """
            SELECT
                ed.entry_jv,
                jv.jv_user_code as invoice_no,
                ed.entry_effective_date as date,
                ed.entry_naration as description,
                ed.fc_amount,
                ed.currency_code,
                ed.exchange_rate,
                ed.enty_values_CR as lkr_value
            FROM entry_details ed
            JOIN new_account_table acc ON ed.account_name = acc.account_name
            JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
            WHERE acc.account_income = 1
            AND ed.currency_code IS NOT NULL
            AND ed.currency_code != 'LKR'
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_naration LIKE '%%Amendment%%'
        """
        sched07_amd_rows = self.db.execute_query(query_sched07_amd, (self.from_date, self.to_date))
        schedule_07_amendment = []

        for r in sched07_amd_rows:
            nrfc_acc = ""
            payment_date = ""

            dr_res = self.db.execute_query("SELECT account_name FROM entry_details WHERE entry_jv = %s AND enty_values_DR > 0", (r['entry_jv'],))
            for dr in dr_res:
                chk_bank = self.db.execute_query("SELECT bank_bookcol_account_number FROM bank_book WHERE bank_bookcol_account_number = %s", (dr['account_name'],))
                if chk_bank:
                    nrfc_acc = dr['account_name']
                    payment_date = str(r['date'])
                    break

            if not nrfc_acc:
                payment_date = "Receivable"

            schedule_07_amendment.append({
                'indicator': 'A',
                'serial_no': r['entry_jv'],
                'invoice_no': r['invoice_no'],
                'date': str(r['date']),
                'description': r['description'],
                'fc_value': float(r['fc_amount'] or 0),
                'currency': r['currency_code'],
                'rate': float(r['exchange_rate'] or 1),
                'lkr_value': float(r['lkr_value'] or 0),
                'nrfc_account': nrfc_acc,
                'payment_date': payment_date
            })

        return {
            'schedule_07_amendment': schedule_07_amendment
        }

    def generate_amendments(self):
        """Generates all Amendment Schedules (01-07)"""
        amendments = {}
        amendments.update(self._generate_amendment_01())
        amendments.update(self._generate_amendment_02())
        amendments.update(self._generate_amendment_03())
        amendments.update(self._generate_amendment_04())
        amendments.update(self._generate_amendment_05())
        amendments.update(self._generate_amendment_06())
        amendments.update(self._generate_amendment_07())
        return amendments

    def generate_reconciliation(self, net_vat):
        """13. Reconciliation (GL vs Schedules)"""
        # GL Movement (Credit - Debit) for the period should match Net VAT (Output - Input)
        query_gl_mvmt = """
            SELECT SUM(enty_values_CR) - SUM(enty_values_DR) as movement
            FROM entry_details
            WHERE account_name = 'VAT Control'
            AND entry_effective_date BETWEEN %s AND %s
            AND entry_deleted = 0
        """
        mvmt_res = self.db.execute_query(query_gl_mvmt, (self.from_date, self.to_date))
        gl_movement = float(mvmt_res[0]['movement'] or 0) if mvmt_res else 0.0

        # Fetch Closing Balance for reference
        query_gl_bal = """
            SELECT SUM(enty_values_CR) - SUM(enty_values_DR) as balance
            FROM entry_details
            WHERE account_name = 'VAT Control'
            AND entry_effective_date <= %s
            AND entry_deleted = 0
        """
        bal_res = self.db.execute_query(query_gl_bal, (self.to_date,))
        gl_balance = float(bal_res[0]['balance'] or 0) if bal_res else 0.0

        reconciliation = {
            'gl_movement': gl_movement,
            'gl_balance': gl_balance,
            'schedule_net': net_vat,
            'difference': gl_movement - net_vat
        }
        return reconciliation

    def generate(self):
        """Generates the full VAT Report Data"""
        s01 = self.generate_schedule_01()
        s02 = self.generate_schedule_02()
        s03 = self.generate_schedule_03()
        s04 = self.generate_schedule_04()
        s05 = self.generate_schedule_05()
        s07 = self.generate_schedule_07()
        amendments = self.generate_amendments()

        # Calculate Net VAT
        # Net VAT = (Output VAT + Output Amd VAT) - (Input VAT + Input Amd VAT + Import VAT + Import Amd VAT) - (Credit Note VAT + CN Amd VAT) - (Deemed Credit + Deemed Amd Credit)

        # Note: In app.py calculation:
        # 'net_vat': total_output_vat + total_sched01_amd_vat - (total_input_vat + total_sched02_amd_vat + total_sched03_vat + total_sched03_amd_vat) - (total_sched04_vat + total_sched04_amd_vat) - (total_sched05_credit + total_sched05_amd_credit)

        total_output_vat = s01['total_vat']
        total_sched01_amd_vat = amendments['total_sched01_amd_vat']

        total_input_vat = s02['total_vat']
        total_sched02_amd_vat = amendments['total_sched02_amd_vat']
        total_sched03_vat = s03['total_vat']
        total_sched03_amd_vat = amendments['total_sched03_amd_vat']

        total_sched04_vat = s04['total_vat']
        total_sched04_amd_vat = amendments['total_sched04_amd_vat']

        total_sched05_credit = s05['total_credit']
        total_sched05_amd_credit = amendments['total_sched05_amd_credit']

        net_vat = (total_output_vat + total_sched01_amd_vat) \
                  - (total_input_vat + total_sched02_amd_vat + total_sched03_vat + total_sched03_amd_vat) \
                  - (total_sched04_vat + total_sched04_amd_vat) \
                  - (total_sched05_credit + total_sched05_amd_credit)

        summary = {
            'total_output_value': s01['total_value'],
            'total_output_vat': total_output_vat,
            'total_input_value': s02['total_value'],
            'total_input_vat': total_input_vat,
            'net_vat': net_vat,
            'total_sched03_vat': total_sched03_vat,
            'total_sched04_value': s04['total_value'],
            'total_sched04_vat': total_sched04_vat,
            'total_sched05_liable': s05['total_liable'],
            'total_sched05_non_liable': s05['total_non_liable'],
            'total_sched05_credit': total_sched05_credit,

            'total_sched01_amd_value': amendments['total_sched01_amd_value'],
            'total_sched01_amd_vat': total_sched01_amd_vat,
            'total_sched02_amd_value': amendments['total_sched02_amd_value'],
            'total_sched02_amd_vat': total_sched02_amd_vat,
            'total_sched03_amd_vat': total_sched03_amd_vat,
            'total_sched04_amd_value': amendments['total_sched04_amd_value'],
            'total_sched04_amd_vat': total_sched04_amd_vat,
            'total_sched05_amd_credit': total_sched05_amd_credit
        }

        reconciliation = self.generate_reconciliation(net_vat)

        return {
            'from_date': self.from_date,
            'to_date': self.to_date,
            'reconciliation': reconciliation,
            'schedule_01': s01['rows'],
            'schedule_02': s02['rows'],
            'schedule_03': s03['rows'],
            'schedule_04': s04['rows'],
            'schedule_05': s05['rows'],
            'schedule_07': s07['rows'],
            'schedule_01_amendment': amendments['schedule_01_amendment'],
            'schedule_02_amendment': amendments['schedule_02_amendment'],
            'schedule_03_amendment': amendments['schedule_03_amendment'],
            'schedule_04_amendment': amendments['schedule_04_amendment'],
            'schedule_05_amendment': amendments['schedule_05_amendment'],
            'schedule_06_amendment': amendments['schedule_06_amendment'],
            'schedule_07_amendment': amendments['schedule_07_amendment'],
            'summary': summary,
            'vat_enabled': True
        }
