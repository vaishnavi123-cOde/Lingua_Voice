import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_ocr_text():
    return """Microsoft Teams
SQL DATABASE
What is SQL Server?
It is a software, developed by Microsoft.
Gaurav Mehta
ENG
02.23 PM
Sunny
IN"""


@pytest.fixture
def clean_sql_text():
    return "What is SQL Server?\nIt is a software, developed by Microsoft."


@pytest.fixture
def app_client():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        yield client
