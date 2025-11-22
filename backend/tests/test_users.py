"""Tests for users management endpoints."""
import pytest
from fastapi.testclient import TestClient
from io import BytesIO
import openpyxl


class TestGetUsers:
    """Tests for GET /users endpoint."""
    
    def test_get_users_admin(self, client: TestClient, admin_headers, admin_user, manager_user):
        """Test getting users list as admin."""
        response = client.get(
            "/api/v1/users",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 2  # Au moins admin et manager
        assert len(data["users"]) >= 2
    
    def test_get_users_pagination(self, client: TestClient, admin_headers):
        """Test users list pagination."""
        response = client.get(
            "/api/v1/users?skip=0&limit=1",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["users"]) <= 1
        assert data["page_size"] == 1
    
    def test_get_users_search(self, client: TestClient, admin_headers, admin_user):
        """Test users search."""
        response = client.get(
            "/api/v1/users?search=ADMIN",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        # Vérifier que le résultat contient bien "ADMIN"
        assert any("ADMIN" in user["matricule"] for user in data["users"])
    
    def test_get_users_filter_role(self, client: TestClient, admin_headers):
        """Test filtering users by role."""
        response = client.get(
            "/api/v1/users?role=ADMIN",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Tous les résultats doivent être ADMIN
        assert all(user["role"] == "ADMIN" for user in data["users"])
    
    def test_get_users_filter_active(self, client: TestClient, admin_headers):
        """Test filtering users by active status."""
        response = client.get(
            "/api/v1/users?is_active=true",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Tous les résultats doivent être actifs
        assert all(user["is_active"] is True for user in data["users"])
    
    def test_get_users_unauthorized(self, client: TestClient):
        """Test getting users without authentication."""
        response = client.get("/api/v1/users")
        
        assert response.status_code == 401
    
    def test_get_users_forbidden_non_admin(self, client: TestClient, regular_user):
        """Test getting users as regular user (forbidden)."""
        from app.core.security import create_access_token
        
        token = create_access_token({"sub": str(regular_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/users", headers=headers)
        
        assert response.status_code == 403


class TestCreateUser:
    """Tests for POST /users endpoint."""
    
    def test_create_user_success(self, client: TestClient, admin_headers):
        """Test successful user creation."""
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "matricule": "TEST001",
                "email": "test@example.com",
                "nom": "Test",
                "prenom": "User",
                "password": "TestPassword123!",
                "role": "USER",
                "is_active": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["matricule"] == "TEST001"
        assert data["email"] == "test@example.com"
        assert data["role"] == "USER"
        assert data["is_active"] is True
    
    def test_create_user_duplicate_matricule(self, client: TestClient, admin_headers, admin_user):
        """Test creating user with duplicate matricule."""
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "matricule": "ADMIN001",  # Déjà existant
                "email": "new@example.com",
                "nom": "Test",
                "prenom": "User",
                "password": "TestPassword123!",
                "role": "USER"
            }
        )
        
        assert response.status_code == 400
        assert "déjà utilisé" in response.json()["detail"]
    
    def test_create_user_duplicate_email(self, client: TestClient, admin_headers, admin_user):
        """Test creating user with duplicate email."""
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "matricule": "NEW001",
                "email": "admin@test.com",  # Déjà existant
                "nom": "Test",
                "prenom": "User",
                "password": "TestPassword123!",
                "role": "USER"
            }
        )
        
        assert response.status_code == 400
    
    def test_create_user_weak_password(self, client: TestClient, admin_headers):
        """Test creating user with weak password."""
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "matricule": "TEST002",
                "email": "test2@example.com",
                "nom": "Test",
                "prenom": "User",
                "password": "weak",  # Trop faible
                "role": "USER"
            }
        )
        
        assert response.status_code == 422
    
    def test_create_user_missing_fields(self, client: TestClient, admin_headers):
        """Test creating user with missing required fields."""
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "matricule": "TEST003",
                # Manque email, nom, prenom, password
                "role": "USER"
            }
        )
        
        assert response.status_code == 422
    
    def test_create_user_unauthorized(self, client: TestClient):
        """Test creating user without authentication."""
        response = client.post(
            "/api/v1/users",
            json={
                "matricule": "TEST004",
                "email": "test4@example.com",
                "nom": "Test",
                "prenom": "User",
                "password": "TestPassword123!",
                "role": "USER"
            }
        )
        
        assert response.status_code == 401


class TestGetUser:
    """Tests for GET /users/{id} endpoint."""
    
    def test_get_user_success(self, client: TestClient, admin_headers, admin_user):
        """Test getting specific user."""
        response = client.get(
            f"/api/v1/users/{admin_user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(admin_user.id)
        assert data["matricule"] == "ADMIN001"
    
    def test_get_user_not_found(self, client: TestClient, admin_headers):
        """Test getting non-existent user."""
        fake_uuid = "00000000-0000-0000-0000-000000000999"
        response = client.get(
            f"/api/v1/users/{fake_uuid}",
            headers=admin_headers
        )
        
        assert response.status_code == 404


class TestUpdateUser:
    """Tests for PUT /users/{id} endpoint."""
    
    def test_update_user_success(self, client: TestClient, admin_headers, regular_user):
        """Test successful user update."""
        response = client.put(
            f"/api/v1/users/{regular_user.id}",
            headers=admin_headers,
            json={
                "nom": "Updated",
                "prenom": "Name",
                "email": "updated@example.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["nom"] == "Updated"
        assert data["prenom"] == "Name"
        assert data["email"] == "updated@example.com"
    
    def test_update_user_role(self, client: TestClient, admin_headers, regular_user):
        """Test updating user role."""
        response = client.put(
            f"/api/v1/users/{regular_user.id}",
            headers=admin_headers,
            json={"role": "MANAGER"}
        )
        
        assert response.status_code == 200
        assert response.json()["role"] == "MANAGER"
    
    def test_update_user_activate_deactivate(self, client: TestClient, admin_headers, regular_user):
        """Test activating/deactivating user."""
        # Désactiver
        response = client.put(
            f"/api/v1/users/{regular_user.id}",
            headers=admin_headers,
            json={"is_active": False}
        )
        
        assert response.status_code == 200
        assert response.json()["is_active"] is False
        
        # Réactiver
        response = client.put(
            f"/api/v1/users/{regular_user.id}",
            headers=admin_headers,
            json={"is_active": True}
        )
        
        assert response.status_code == 200
        assert response.json()["is_active"] is True
    
    def test_update_user_not_found(self, client: TestClient, admin_headers):
        """Test updating non-existent user."""
        fake_uuid = "00000000-0000-0000-0000-000000000999"
        response = client.put(
            f"/api/v1/users/{fake_uuid}",
            headers=admin_headers,
            json={"nom": "Test"}
        )
        
        assert response.status_code == 404


class TestDeleteUser:
    """Tests for DELETE /users/{id} endpoint."""
    
    def test_delete_user_success(self, client: TestClient, admin_headers, db_session):
        """Test successful user deletion."""
        from app.models.user import User
        from app.core.security import get_password_hash
        
        # Créer utilisateur à supprimer
        user_to_delete = User(
            id="00000000-0000-0000-0000-000000000088",
            matricule="DELETE001",
            email="delete@test.com",
            nom="Delete",
            prenom="Me",
            hashed_password=get_password_hash("TestPassword123!"),
            role="USER",
            is_active=True
        )
        db_session.add(user_to_delete)
        db_session.commit()
        
        response = client.delete(
            f"/api/v1/users/{user_to_delete.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        # Vérifier que l'utilisateur n'existe plus
        get_response = client.get(
            f"/api/v1/users/{user_to_delete.id}",
            headers=admin_headers
        )
        assert get_response.status_code == 404
    
    def test_delete_user_not_found(self, client: TestClient, admin_headers):
        """Test deleting non-existent user."""
        fake_uuid = "00000000-0000-0000-0000-000000000999"
        response = client.delete(
            f"/api/v1/users/{fake_uuid}",
            headers=admin_headers
        )
        
        assert response.status_code == 404


class TestImportExcel:
    """Tests for Excel import endpoint."""
    
    def test_import_excel_success(self, client: TestClient, admin_headers):
        """Test successful Excel import."""
        # Créer fichier Excel de test
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["matricule", "email", "nom", "prenom", "role", "password"])
        ws.append(["IMP001", "import1@test.com", "Import", "User1", "USER", "ImportPassword123!"])
        ws.append(["IMP002", "import2@test.com", "Import", "User2", "MANAGER", "ImportPassword123!"])
        
        # Sauvegarder en mémoire
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        response = client.post(
            "/api/v1/users/import-excel",
            headers=admin_headers,
            files={"file": ("users.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success_count"] == 2
        assert data["error_count"] == 0
        assert len(data["created_users"]) == 2
    
    def test_import_excel_partial_errors(self, client: TestClient, admin_headers, admin_user):
        """Test Excel import with some errors."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["matricule", "email", "nom", "prenom", "role", "password"])
        ws.append(["IMP003", "import3@test.com", "Import", "User3", "USER", "ImportPassword123!"])
        ws.append(["ADMIN001", "duplicate@test.com", "Dup", "User", "USER", "ImportPassword123!"])  # Matricule dupliqué
        
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        response = client.post(
            "/api/v1/users/import-excel",
            headers=admin_headers,
            files={"file": ("users.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success_count"] == 1
        assert data["error_count"] == 1
        assert len(data["errors"]) == 1
    
    def test_import_excel_invalid_file(self, client: TestClient, admin_headers):
        """Test import with invalid file."""
        # Fichier texte au lieu d'Excel
        fake_file = BytesIO(b"not an excel file")
        
        response = client.post(
            "/api/v1/users/import-excel",
            headers=admin_headers,
            files={"file": ("invalid.txt", fake_file, "text/plain")}
        )
        
        assert response.status_code == 400
    
    def test_import_excel_unauthorized(self, client: TestClient):
        """Test import without authentication."""
        excel_file = BytesIO()
        
        response = client.post(
            "/api/v1/users/import-excel",
            files={"file": ("users.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 401


class TestResetPassword:
    """Tests for password reset endpoint."""
    
    def test_reset_password_success(self, client: TestClient, admin_headers, regular_user):
        """Test successful password reset by admin."""
        response = client.post(
            f"/api/v1/users/{regular_user.id}/reset-password",
            headers=admin_headers,
            json={
                "new_password": "ResetPassword123!",
                "force_change": True
            }
        )
        
        assert response.status_code == 200
        
        # Vérifier que le nouveau mot de passe fonctionne
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "matricule": "USR001",
                "password": "ResetPassword123!"
            }
        )
        assert login_response.status_code == 200
    
    def test_reset_password_weak(self, client: TestClient, admin_headers, regular_user):
        """Test reset with weak password."""
        response = client.post(
            f"/api/v1/users/{regular_user.id}/reset-password",
            headers=admin_headers,
            json={
                "new_password": "weak",
                "force_change": True
            }
        )
        
        assert response.status_code == 422
    
    def test_reset_password_not_found(self, client: TestClient, admin_headers):
        """Test reset for non-existent user."""
        fake_uuid = "00000000-0000-0000-0000-000000000999"
        response = client.post(
            f"/api/v1/users/{fake_uuid}/reset-password",
            headers=admin_headers,
            json={
                "new_password": "ResetPassword123!",
                "force_change": True
            }
        )
        
        assert response.status_code == 404


class TestUserStats:
    """Tests for user statistics endpoint."""
    
    def test_get_stats(self, client: TestClient, admin_headers, admin_user, manager_user, regular_user):
        """Test getting user statistics."""
        response = client.get(
            "/api/v1/users/stats/overview",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_users" in data
        assert "active_users" in data
        assert "inactive_users" in data
        assert "users_by_role" in data
        assert "recent_logins" in data
        
        assert data["total_users"] >= 3
        assert "ADMIN" in data["users_by_role"]
        assert "MANAGER" in data["users_by_role"]
        assert "USER" in data["users_by_role"]