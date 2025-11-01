# tests/integration/database/test_database_setup.py
import pytest
from voice_agent.database_service import Database
from voice_agent.database.migrations import DatabaseMigrations
import tempfile
import os

@pytest.mark.asyncio
async def test_database_connection_lifecycle():
    """Test basic database connection creation and cleanup"""
    
    # Use temporary file for test database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = Database()
        
        # Test connection initialization
        await db.init_db(db_path)
        assert db.connection is not None
        assert db.email_repo is not None
        assert db.etl_repo is not None
        
        # Test that we can query the database
        cursor = await db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = await cursor.fetchall()
        table_names = [row[0] for row in tables]
        
        assert 'emails' in table_names
        assert 'etl_jobs' in table_names
        
        # Test cleanup
        await db.close()
        
    finally:
        # Clean up test database file
        if os.path.exists(db_path):
            os.unlink(db_path)
