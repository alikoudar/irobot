"""Tests for authentication endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.core.security import get_password_hash


class TestLogin:
    """Tests for login endpoint."""
    
    def test_login_success(self, client: TestClient, admin_user):
        """Test successful login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "matricule": "ADMIN001",
                "password": "TestPassword123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
        assert data["user"]["matricule"] == "ADMIN001"
        assert data["user"]["role"] == "ADMIN"
    
    def test_login_invalid_matricule(self, client: TestClient):
        """Test login with non-existent matricule."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "matricule": "INVALID001",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "Matricule ou mot de passe incorrect" in response.json()["detail"]
    
    def test_login_invalid_password(self, client: TestClient, admin_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "matricule": "ADMIN001",
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "Matricule ou mot de passe incorrect" in response.json()["detail"]
    
    def test_login_inactive_user(self, client: TestClient, db_session):
        """Test login with inactive user account."""
        from app.models.user import User
        
        # Create inactive user
        inactive_user = User(
            id="00000000-0000-0000-0000-000000000099",
            matricule="INACTIVE001",
            email="inactive@test.com",
            nom="Inactive",
            prenom="User",
            hashed_password=get_password_hash("TestPassword123!"),
            role="USER",
            is_active=False,  # Compte désactivé
            is_verified=True
        )
        db_session.add(inactive_user)
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "matricule": "INACTIVE001",
                "password": "TestPassword123!"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_missing_fields(self, client: TestClient):
        """Test login with missing required fields."""
        # Missing password
        response = client.post(
            "/api/v1/auth/login",
            json={"matricule": "ADMIN001"}
        )
        assert response.status_code == 422
        
        # Missing matricule
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "TestPassword123!"}
        )
        assert response.status_code == 422


class TestRefreshToken:
    """Tests for token refresh endpoint."""
    
    def test_refresh_token_success(self, client: TestClient, admin_user):
        """Test successful token refresh."""
        # First, login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "matricule": "ADMIN001",
                "password": "TestPassword123!"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh the access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_refresh_token_missing(self, client: TestClient):
        """Test refresh without token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={}
        )
        
        assert response.status_code == 422


class TestChangePassword:
    """Tests for change password endpoint."""
    
    def test_change_password_success(self, client: TestClient, admin_user, admin_headers):
        """Test successful password change."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=admin_headers,
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 200
        assert "Mot de passe changé avec succès" in response.json()["message"]
        
        # Verify new password works
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "matricule": "ADMIN001",
                "password": "NewPassword123!"
            }
        )
        assert login_response.status_code == 200
    
    def test_change_password_wrong_current(self, client: TestClient, admin_headers):
        """Test password change with wrong current password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=admin_headers,
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 400
    
    def test_change_password_weak_new(self, client: TestClient, admin_headers):
        """Test password change with weak new password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=admin_headers,
            json={
                "current_password": "TestPassword123!",
                "new_password": "weak"  # Trop faible
            }
        )
        
        assert response.status_code == 422
    
    def test_change_password_unauthorized(self, client: TestClient):
        """Test password change without authentication."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 401


class TestForgotPassword:
    """Tests for forgot password endpoint."""
    
    def test_forgot_password_with_matricule(self, client: TestClient, admin_user):
        """Test forgot password with matricule."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"identifier": "ADMIN001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "email" in data
        # En dev, le token doit être retourné
        assert "reset_token" in data
    
    def test_forgot_password_with_email(self, client: TestClient, admin_user):
        """Test forgot password with email."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"identifier": "admin@test.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "email" in data
    
    def test_forgot_password_nonexistent_user(self, client: TestClient):
        """Test forgot password with non-existent user."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"identifier": "NONEXISTENT001"}
        )
        
        assert response.status_code == 404
    
    def test_forgot_password_inactive_user(self, client: TestClient, db_session):
        """Test forgot password with inactive user."""
        from app.models.user import User
        
        # Create inactive user
        inactive_user = User(
            id="00000000-0000-0000-0000-000000000098",
            matricule="INACTIVE002",
            email="inactive2@test.com",
            nom="Inactive",
            prenom="User",
            hashed_password=get_password_hash("TestPassword123!"),
            role="USER",
            is_active=False,
            is_verified=True
        )
        db_session.add(inactive_user)
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"identifier": "INACTIVE002"}
        )
        
        assert response.status_code == 403


class TestProfile:
    """Tests for profile endpoints."""
    
    def test_get_current_user(self, client: TestClient, admin_headers):
        """Test getting current user info."""
        response = client.get(
            "/api/v1/auth/me",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["matricule"] == "ADMIN001"
        assert data["role"] == "ADMIN"
        assert data["is_active"] is True
    
    def test_update_profile_success(self, client: TestClient, admin_headers):
        """Test successful profile update."""
        response = client.put(
            "/api/v1/auth/profile",
            headers=admin_headers,
            json={
                "nom": "Updated",
                "prenom": "Name",
                "email": "updated@test.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["nom"] == "Updated"
        assert data["prenom"] == "Name"
        assert data["email"] == "updated@test.com"
    
    def test_update_profile_partial(self, client: TestClient, admin_headers):
        """Test partial profile update."""
        response = client.put(
            "/api/v1/auth/profile",
            headers=admin_headers,
            json={"nom": "OnlyName"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["nom"] == "OnlyName"
        # Autres champs inchangés
        assert data["matricule"] == "ADMIN001"
    
    def test_update_profile_duplicate_email(self, client: TestClient, admin_headers, manager_user):
        """Test profile update with email already used."""
        response = client.put(
            "/api/v1/auth/profile",
            headers=admin_headers,
            json={"email": "manager@test.com"}  # Email du manager
        )
        
        assert response.status_code == 400
        assert "déjà utilisé" in response.json()["detail"]
    
    def test_update_profile_unauthorized(self, client: TestClient):
        """Test profile update without authentication."""
        response = client.put(
            "/api/v1/auth/profile",
            json={"nom": "Test"}
        )
        
        assert response.status_code == 401


class TestLogout:
    """Tests for logout endpoint."""
    
    def test_logout_success(self, client: TestClient, admin_headers):
        """Test successful logout."""
        response = client.post(
            "/api/v1/auth/logout",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "Déconnexion réussie" in response.json()["message"]
    
    def test_logout_unauthorized(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401