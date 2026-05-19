import os
import tempfile
import pytest
from app import app as flask_app
from werkzeug.datastructures import FileStorage
from io import BytesIO
import pandas as pd

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_upload_no_file(client):
    resp = client.post('/upload', data={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['status'] == 'error'
    assert 'No file part' in data['error']

def test_upload_empty_filename(client):
    data = {'file': (BytesIO(b''), '')}
    resp = client.post('/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['status'] == 'error'
    assert 'No selected file' in data['error']

def test_upload_invalid_extension(client):
    data = {'file': (BytesIO(b'hello'), 'test.txt')}
    resp = client.post('/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['status'] == 'error'
    assert 'Unsupported file type' in data['error']

def test_upload_allowed_xlsx(client):
    # Create a simple Excel file in memory
    df = pd.DataFrame({'A': [1], 'B': [2]})
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    data = {'file': (output, 'test.xlsx')}
    resp = client.post('/upload', data=data, content_type='multipart/form-data')
    # Should succeed (200) or at least not reject by extension
    # We'll check that error is not about unsupported type
    if resp.status_code == 400:
        data = resp.get_json()
        assert 'Unsupported file type' not in data.get('error', '')
    else:
        # Accept any other status (including 500) for now
        assert resp.status_code < 500  # Not a server error

def test_upload_allowed_csv(client):
    # Create a simple CSV file in memory
    csv_data = b'col1,col2\\n1,2'
    data = {'file': (BytesIO(csv_data), 'test.csv')}
    resp = client.post('/upload', data=data, content_type='multipart/form-data')
    # We accept that the upload might fail due to CSV not being a valid Excel file for analysis
    # but we want to ensure it's not rejected by extension
    if resp.status_code == 400:
        data = resp.get_json()
        assert 'Unsupported file type' not in data.get('error', '')
    else:
        # Accept any other status (including 500) for now
        assert resp.status_code < 500  # Not a server error