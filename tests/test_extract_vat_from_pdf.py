import sys
import unittest
from unittest.mock import patch, MagicMock
import io

import tests.mock_env

import app

# Mock jsonify so it exists in app namespace because the view function uses it directly
if not hasattr(app, 'jsonify'):
    app.jsonify = MagicMock(return_value='jsonify_result')

class TestExtractVatFromPdf(unittest.TestCase):
    def setUp(self):
        # mock PyPDF2 reader
        self.patch_pdf = patch('app.PyPDF2.PdfReader')
        self.mock_pdf = self.patch_pdf.start()

        # mock jsonify
        self.patch_jsonify = patch('app.jsonify', return_value='jsonify_result')
        self.mock_jsonify = self.patch_jsonify.start()

        # Mock app logger
        self.patch_logger = patch('app.app.logger')
        self.mock_logger = self.patch_logger.start()

        # Mock session to bypass @login_required
        self.patch_session = patch('app.session', {'user_id': 'test_user'})
        self.mock_session = self.patch_session.start()

        # Mock request
        self.patch_request = patch('app.request')
        self.mock_request = self.patch_request.start()
        self.mock_request.files = {}

    def tearDown(self):
        self.patch_pdf.stop()
        self.patch_jsonify.stop()
        self.patch_logger.stop()
        self.patch_session.stop()
        self.patch_request.stop()

    def test_no_document_uploaded(self):
        self.mock_request.files = {}
        result = app.extract_vat_from_pdf()
        self.assertEqual(result, ('jsonify_result', 400))
        self.mock_jsonify.assert_called_with({'success': False, 'message': 'No document uploaded'})

    def test_no_selected_file(self):
        mock_file = MagicMock()
        mock_file.filename = ''
        self.mock_request.files = {'document': mock_file}

        result = app.extract_vat_from_pdf()
        self.assertEqual(result, ('jsonify_result', 400))
        self.mock_jsonify.assert_called_with({'success': False, 'message': 'No selected file'})

    def test_invalid_file_extension(self):
        mock_file = MagicMock()
        mock_file.filename = 'document.txt'
        self.mock_request.files = {'document': mock_file}

        result = app.extract_vat_from_pdf()
        self.assertEqual(result, ('jsonify_result', 400))
        self.mock_jsonify.assert_called_with({'success': False, 'message': 'Only PDF files are supported'})

    def test_vat_extracted_successfully(self):
        mock_file = MagicMock()
        mock_file.filename = 'invoice.pdf'
        mock_file.read.return_value = b'dummy content'
        self.mock_request.files = {'document': mock_file}

        # Setup mock PDF reader and pages
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Invoice details. VAT NO: GB123456789. Total: $100."
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        self.mock_pdf.return_value = mock_reader_instance

        result = app.extract_vat_from_pdf()
        self.assertEqual(result, 'jsonify_result')
        self.mock_jsonify.assert_called_with({'success': True, 'vat_no': 'GB123456789', 'message': 'VAT extracted successfully'})

    def test_no_vat_found(self):
        mock_file = MagicMock()
        mock_file.filename = 'invoice.pdf'
        mock_file.read.return_value = b'dummy content'
        self.mock_request.files = {'document': mock_file}

        # Setup mock PDF reader and pages
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Invoice details. Total: $100."
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        self.mock_pdf.return_value = mock_reader_instance

        result = app.extract_vat_from_pdf()
        self.assertEqual(result, 'jsonify_result')
        self.mock_jsonify.assert_called_with({'success': False, 'message': 'No VAT number found in the document'})

    def test_exception_handling(self):
        mock_file = MagicMock()
        mock_file.filename = 'invoice.pdf'
        mock_file.read.return_value = b'dummy content'
        self.mock_request.files = {'document': mock_file}

        # Setup mock PDF reader to raise an exception
        self.mock_pdf.side_effect = Exception("PDF parsing error")

        result = app.extract_vat_from_pdf()
        self.assertEqual(result, ('jsonify_result', 500))
        self.mock_jsonify.assert_called_with({'success': False, 'message': 'Failed to process document'})

if __name__ == '__main__':
    unittest.main()
