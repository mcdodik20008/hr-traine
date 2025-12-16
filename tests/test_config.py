"""Tests for configuration module"""
import pytest
import os
from unittest.mock import patch
from app.config import Config


class TestConfig:
    """Test configuration class"""
    
    def test_config_initialization(self):
        """Test that config can be initialized"""
        config = Config()
        assert config is not None
    
    def test_database_url_property(self):
        """Test DATABASE_URL property generation"""
        config = Config()
        url = config.DATABASE_URL
        assert url.startswith("postgresql+asyncpg://")
        assert "postgres" in url
        assert "hr_traine" in url
    
    def test_database_url_with_custom_values(self, monkeypatch):
        """Test DATABASE_URL with custom environment variables"""
        monkeypatch.setenv("POSTGRES_USER", "custom_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "custom_pass")
        monkeypatch.setenv("POSTGRES_DB", "custom_db")
        monkeypatch.setenv("POSTGRES_HOST", "custom_host")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        
        # Reload config
        import importlib
        from app import config
        importlib.reload(config)
        
        url = config.config.DATABASE_URL
        assert "custom_user" in url
        assert "custom_pass" in url
        assert "custom_db" in url
        assert "custom_host" in url
        assert ":5433" in url

