import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
def test_user_jwt_flow(client):
    """
    Test the standard authentication flow:
    1. Register/create a custom User.
    2. Try accessing a protected endpoint (should fail with 401).
    3. Obtain a JWT token pair (access & refresh) using credentials.
    4. Access the protected endpoint with the bearer token (should succeed).
    5. Refresh the access token using the refresh token (should succeed).
    """
    # 1. Create a user
    username = "testuser"
    password = "testpassword123"
    email = "test@example.com"
    user = User.objects.create_user(username=username, password=password, email=email)
    
    # Check that our custom user model works
    assert user.__class__.__name__ == "User"
    assert user.username == username
    
    # 2. Query protected endpoint without token (should fail)
    health_check_url = reverse('health_check')
    response = client.get(health_check_url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # 3. Obtain token
    token_url = reverse('token_obtain_pair')
    response = client.post(token_url, {
        "username": username,
        "password": password
    })
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data
    
    access_token = response.data["access"]
    refresh_token = response.data["refresh"]
    
    # 4. Access protected endpoint with token (should succeed)
    headers = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
    response = client.get(health_check_url, **headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "healthy"
    assert response.data["user"]["username"] == username
    assert response.data["user"]["email"] == email
    
    # 5. Refresh token
    refresh_url = reverse('token_refresh')
    response = client.post(refresh_url, {
        "refresh": refresh_token
    })
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
