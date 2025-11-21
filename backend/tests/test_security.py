"""Tests for security functions."""
import pytest
from datetime import timedelta

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    """Tests for password hashing."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash
        assert len(hashed) == 60  # bcrypt hash length
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password("WrongPassword", hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "MySecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT tokens."""
    
    def test_create_access_token(self):
        """Test creating access token."""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_custom_expiry(self):
        """Test creating access token with custom expiry."""
        data = {"sub": "user@example.com"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=expires_delta)
        
        assert token is not None
        
        # Decode and check expiry
        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """Test creating refresh token."""
        data = {"sub": "user@example.com"}
        token = create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Test decoding valid token."""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user@example.com"
        assert payload["user_id"] == "123"
        assert "exp" in payload
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token."""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)
        
        assert payload is None
    
    def test_decode_expired_token(self):
        """Test decoding expired token."""
        data = {"sub": "user@example.com"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expires_delta)
        
        payload = decode_token(token)
        
        # Should return None for expired token
        assert payload is None
    
    def test_token_contains_expiry(self):
        """Test that token contains expiry claim."""
        data = {"sub": "user@example.com"}
        token = create_access_token(data)
        payload = decode_token(token)
        
        assert payload is not None
        assert "exp" in payload
        assert isinstance(payload["exp"], int)


class TestPasswordComplexity:
    """Tests for password complexity requirements."""
    
    def test_hash_short_password(self):
        """Test that short passwords can be hashed."""
        # Note: Password policy should be enforced at API level, not hashing level
        password = "Short1!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_hash_long_password(self):
        """Test hashing long password."""
        password = "A" * 71 + "1!"  # 73 chars (bcrypt max is 72)
        hashed = get_password_hash(password[:72])  # Truncate to 72
        
        assert verify_password(password[:72], hashed) is True
    
    def test_hash_special_characters(self):
        """Test hashing password with special characters."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_hash_unicode_password(self):
        """Test hashing password with unicode characters."""
        password = "Pässwörd123!éè"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True