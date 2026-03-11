import sys
import os
import pytest
import datetime
from tests import mock_env
import app
from app import db
from unittest.mock import patch

def test_inventory_trend_route():
    with patch('app.check_permission', return_value=True), \
         patch('app.db.execute_query') as mock_db, \
         patch('app.render_template') as mock_render, \
         app.app.test_request_context('/inventory_trend_analysis'):
        app.session['user_id'] = 'ADM001'
        app.session['user_pk'] = 1

        # Mocks env sets `app.request.args = MagicMock()` which returns True for `item_name`
        # We need to override that specifically for this test
        app.request.args = {}

        mock_db.return_value = [{'inventoy_name': 'Item A'}]
        mock_render.return_value = 'Mock HTML'

        res = app.inventory_trend_analysis()
        assert res == 'Mock HTML'

def test_inventory_trend_route_with_item():
    with patch('app.check_permission', return_value=True), \
         patch('app.db.execute_query') as mock_db, \
         patch('app.render_template') as mock_render, \
         app.app.test_request_context('/inventory_trend_analysis?item_name=Item+A&months=6'):
        app.session['user_id'] = 'ADM001'
        app.session['user_pk'] = 1

        app.request.args = {'item_name': 'Item A', 'months': '6'}

        mock_db.side_effect = [
            [{'inventoy_name': 'Item A'}], # items
            [{'Year': 2023, 'Month': 1, 'MonthlySales': 100},
             {'Year': 2023, 'Month': 2, 'MonthlySales': 120}] # raw_data
        ]
        mock_render.return_value = 'Mock HTML'
        res = app.inventory_trend_analysis()
        assert res == 'Mock HTML'
