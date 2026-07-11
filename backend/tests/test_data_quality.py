import pytest
import pandas as pd
import numpy as np
import io
import joblib
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from analysis.data_quality import analyze_data_quality
from audits.models import AuditJob

User = get_user_model()


def test_analyze_data_quality_math():
    """
    Unit test for the custom pandas data quality logic.
    Evaluates:
    - 30% missing values in float column
    - 1 duplicate row (out of 10 rows total, so 10%)
    - 1 IQR outlier in column C (value 100)
    """
    # Create synthetic dataset
    # 10 rows total
    data = {
        'A': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],                     # Integers
        'B': [1.5, 2.0, np.nan, 4.0, np.nan, 6.0, np.nan, 8.0, 9.0, 10.0], # Floats, 3 missing (30%)
        'C': [10, 11, 10, 11, 12, 10, 11, 12, 10, 100],           # Outlier: 100
    }
    
    df = pd.DataFrame(data)
    
    # Let's duplicate row index 0 (so index 10 is a duplicate of index 0)
    duplicate_row = pd.DataFrame([df.iloc[0]])
    df = pd.concat([df, duplicate_row], ignore_index=True)
    
    # Run quality checker
    metrics = analyze_data_quality(df, target_column='A')
    
    # Assertions
    assert metrics['total_rows'] == 11
    assert metrics['total_columns'] == 3
    assert metrics['target_column'] == 'A'
    
    # Check duplicates: row index 10 is identical to row index 0
    assert metrics['duplicates']['count'] == 1
    # 1/11 = 9.09%
    assert abs(metrics['duplicates']['percentage'] - 9.09) < 0.1
    
    # Check missing values in B: 3 missing out of 11 rows -> 3/11 = 27.27%
    assert metrics['missing_data']['B']['count'] == 3
    assert abs(metrics['missing_data']['B']['percentage'] - 27.27) < 0.1
    assert metrics['missing_data']['A']['count'] == 0
    
    # Check IQR outliers in C: 100 is far above upper bound
    assert metrics['outliers']['C']['count'] == 1
    assert metrics['outliers']['C']['percentage'] > 0.0
    
    # Check types inference
    assert metrics['column_types']['A'] == 'Integer'
    assert metrics['column_types']['B'] == 'Float'
    assert metrics['column_types']['C'] == 'Integer'


@pytest.mark.django_db
def test_upload_api_validation_errors(client):
    """
    Integration API test to verify upload validation.
    Checks:
    - Missing files (returns 400)
    - Wrong dataset file extension (returns 400)
    - Corrupt sklearn model file (returns 400)
    - Target column missing from dataset (returns 400)
    """
    # 1. Create and authenticate user
    username = "auditor_user"
    password = "secure_pass_123"
    user = User.objects.create_user(username=username, password=password)
    
    # Authenticate client
    token_url = reverse('token_obtain_pair')
    resp = client.post(token_url, {"username": username, "password": password})
    access_token = resp.data["access"]
    headers = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
    
    upload_url = reverse('audit-list') # Viewset list URL represents POST endpoint
    
    # 2. Test missing files entirely
    response = client.post(upload_url, {}, **headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "model_file" in response.data
    assert "dataset_file" in response.data
    assert "target_column" in response.data
    
    # 3. Test wrong dataset format (upload .txt instead of .csv)
    model_buffer = io.BytesIO()
    # Write a valid mock joblib classifier dump
    from sklearn.dummy import DummyClassifier
    clf = DummyClassifier(strategy="most_frequent")
    clf.fit([[1]], [1])
    joblib.dump(clf, model_buffer)
    model_buffer.seek(0)
    
    mock_model = SimpleUploadedFile("model.joblib", model_buffer.read(), content_type="application/octet-stream")
    mock_txt_dataset = SimpleUploadedFile("dataset.txt", b"id,val\n1,10", content_type="text/plain")
    
    payload = {
        "model_file": mock_model,
        "dataset_file": mock_txt_dataset,
        "target_column": "val"
    }
    
    response = client.post(upload_url, payload, format='multipart', **headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "dataset format" in response.data["error"].lower()
    
    # 4. Test corrupt model file (upload arbitrary text data as model)
    model_buffer.seek(0)
    mock_csv_dataset = SimpleUploadedFile("dataset.csv", b"id,val\n1,10", content_type="text/csv")
    corrupt_model = SimpleUploadedFile("model.joblib", b"this is raw text, not joblib binary", content_type="application/octet-stream")
    
    payload = {
        "model_file": corrupt_model,
        "dataset_file": mock_csv_dataset,
        "target_column": "val"
    }
    
    response = client.post(upload_url, payload, format='multipart', **headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "failed to load model" in response.data["error"].lower()

    # 5. Test missing target column in dataset
    # Regenerate fresh file buffers
    model_buffer = io.BytesIO()
    joblib.dump(clf, model_buffer)
    model_buffer.seek(0)
    mock_model = SimpleUploadedFile("model.joblib", model_buffer.read(), content_type="application/octet-stream")
    mock_csv_dataset = SimpleUploadedFile("dataset.csv", b"id,val\n1,10", content_type="text/csv")
    
    payload = {
        "model_file": mock_model,
        "dataset_file": mock_csv_dataset,
        "target_column": "non_existent_column"
    }
    
    response = client.post(upload_url, payload, format='multipart', **headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "target column" in response.data["error"].lower()
