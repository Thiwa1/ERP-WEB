with open("app.py", "r") as f:
    lines = f.readlines()

new_code = """def extract_vat_from_pdf():
    import io
    import re
    import PyPDF2

    if 'document' not in request.files:
        return jsonify({'success': False, 'message': 'No document uploaded'}), 400

    file = request.files['document']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Only PDF files are supported'}), 400

    try:
        # Read PDF content
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "

        # "AI" Regex to find VAT Numbers
        # Matches common VAT formats (e.g., VAT NO: 123456789, VAT: GB123456789)
        vat_pattern = r'(?i)VAT\\s*(?:NO|NUMBER|#)?\\s*[:\\-\\s]?\\s*([A-Z0-9]{8,15})'
        matches = re.findall(vat_pattern, text)

        if matches:
            # Return first distinct match
            vat_no = matches[0].strip()
            return jsonify({'success': True, 'vat_no': vat_no, 'message': 'VAT extracted successfully'})
        else:
            return jsonify({'success': False, 'message': 'No VAT number found in the document'})

    except Exception as e:
        app.logger.error(f"Error extracting VAT: {e}")
        return jsonify({'success': False, 'message': 'Failed to process document'}), 500
"""

for i, line in enumerate(lines):
    if "def extract_vat_from_pdf():" in line:
        start_idx = i
        break

for i in range(start_idx, len(lines)):
    if "def add_supplier():" in lines[i]:
        end_idx = i - 2
        break

with open("app.py", "w") as f:
    f.writelines(lines[:start_idx] + [new_code] + lines[end_idx:])
