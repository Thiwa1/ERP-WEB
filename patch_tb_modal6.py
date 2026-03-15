import pytest
from playwright.sync_api import sync_playwright

def verify_tb_modal():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate directly to a simulated HTML file or mock route
        import os
        from urllib.parse import urljoin

        # Set up a local test server or just mock
        import subprocess
        import time
        server = subprocess.Popen(['python', '-m', 'http.server', '3000'])
        time.sleep(2)

        try:
            # Create a mock html file
            with open('templates/bulk_upload_tb_review.html', 'r') as f:
                content = f.read()

            # replace basic stuff
            content = content.replace('{% extends "base.html" %}', '')
            content = content.replace('{% block content %}', '')
            content = content.replace('{% endblock %}', '')
            content = content.replace('{{ url_for(\'bulk_upload_tb\') }}', '#')
            content = content.replace('{{ url_for(\'bulk_upload_gl\') }}', '#')
            content = content.replace('{% set missing_count = rows|selectattr(\'status\', \'equalto\', \'Missing\')|list|length %}', '')
            content = content.replace('{% if missing_count > 0 %}', '')
            content = content.replace('{{ missing_count }}', '2')
            content = content.replace('{% endif %}', '')
            content = content.replace('{% for row in rows %}', '')
            content = content.replace('{% if row.status == \'Missing\' %}', '')
            content = content.replace('{{ row.name }}', 'Test Account')
            content = content.replace('{{ "{:,.2f}".format(row.dr) }}', '100.00')
            content = content.replace('{{ "{:,.2f}".format(row.cr) }}', '0.00')
            content = content.replace('{% else %}', '')
            content = content.replace('{% set diff = (total_dr - total_cr) | abs %}', '')
            content = content.replace('{% if diff > 0.01 %}', '')
            content = content.replace('{{ "{:,.2f}".format(total_dr) }}', '100.00')
            content = content.replace('{{ "{:,.2f}".format(total_cr) }}', '100.00')
            content = content.replace('{{ "{:,.2f}".format(total_dr - total_cr) }}', '0.00')
            content = content.replace('{% set is_disabled = missing_count > 0 or diff > 0.01 %}', '')
            content = content.replace('{% if is_disabled %}', '')

            with open('test_tb_modal6.html', 'w') as f:
                f.write(content)

        finally:
            server.terminate()

if __name__ == "__main__":
    verify_tb_modal()
