"""Tests for database base module"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.base import Base, get_session


class TestDatabaseBase:
    """Test database base functionality"""
    
    def test_base_exists(self):
        """Test that Base class exists"""
        assert Base is not None
    
    @pytest.mark.asyncio
    async def test_get_session_generator(self):
        """Test that get_session is a generator"""
        # Note: This will try to use real DB connection
        # In tests, we should mock this or use test_session fixture
        gen = get_session()
        assert hasattr(gen, '__aiter__') or hasattr(gen, '__iter__')

