"""
Unit tests for JSON memory functionality.

Tests the JSONMemory class for proper file operations, data persistence,
and error handling.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from src.agent.memory.json_memory import JSONMemory, JSONMemoryError, create_memory


class TestJSONMemory:
    """Test suite for JSONMemory class."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.memory = JSONMemory(self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory after tests."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test memory initialization creates required files."""
        assert self.memory.data_dir == Path(self.temp_dir)
        assert self.memory.preferences_file.exists()
        assert self.memory.history_file.exists()
    
    def test_default_preferences_structure(self):
        """Test default preferences contain required keys."""
        preferences = self.memory.get_preferences()
        
        required_keys = [
            "preferred_regions",
            "naming_pattern", 
            "cost_preference",
            "default_performance_tier",
            "default_replication",
            "use_case_patterns"
        ]
        
        for key in required_keys:
            assert key in preferences
        
        # Check specific default values
        assert preferences["preferred_regions"] == ["eastus", "westus2"]
        assert preferences["naming_pattern"] == "descriptive"
        assert preferences["cost_preference"] == "optimized"
        assert preferences["default_performance_tier"] == "Standard"
        assert preferences["default_replication"] == "LRS"
        
        # Check use case patterns structure
        patterns = preferences["use_case_patterns"]
        assert "images" in patterns
        assert "backups" in patterns
        assert "logs" in patterns
    
    def test_default_history_structure(self):
        """Test default history structure."""
        history_data = self.memory._read_json_file(self.memory.history_file)
        
        assert "conversations" in history_data
        assert "last_updated" in history_data
        assert isinstance(history_data["conversations"], list)
        assert len(history_data["conversations"]) == 0
    
    def test_get_set_preference(self):
        """Test getting and setting individual preferences."""
        # Test getting existing preference
        regions = self.memory.get_preference("preferred_regions")
        assert regions == ["eastus", "westus2"]
        
        # Test getting with default
        custom_key = self.memory.get_preference("custom_key", "default_value")
        assert custom_key == "default_value"
        
        # Test setting preference
        self.memory.set_preference("test_key", "test_value")
        assert self.memory.get_preference("test_key") == "test_value"
    
    def test_update_preferences(self):
        """Test updating multiple preferences at once."""
        updates = {
            "cost_preference": "performance",
            "custom_setting": "custom_value"
        }
        
        self.memory.update_preferences(updates)
        
        assert self.memory.get_preference("cost_preference") == "performance"
        assert self.memory.get_preference("custom_setting") == "custom_value"
        
        # Ensure other preferences unchanged
        assert self.memory.get_preference("naming_pattern") == "descriptive"
    
    def test_use_case_patterns(self):
        """Test use case pattern management."""
        # Test getting existing pattern
        images_pattern = self.memory.get_use_case_pattern("images")
        assert images_pattern is not None
        assert images_pattern["tier"] == "Hot"
        assert images_pattern["replication"] == "LRS"
        
        # Test getting non-existent pattern
        custom_pattern = self.memory.get_use_case_pattern("custom_use_case")
        assert custom_pattern is None
        
        # Test adding new pattern
        new_pattern = {"tier": "Cool", "replication": "GRS"}
        self.memory.add_use_case_pattern("analytics", new_pattern)
        
        retrieved_pattern = self.memory.get_use_case_pattern("analytics")
        assert retrieved_pattern == new_pattern
    
    def test_conversation_history(self):
        """Test conversation history management."""
        # Initially empty
        history = self.memory.get_conversation_history()
        assert len(history) == 0
        
        # Add conversation entry
        entry1 = {
            "user_input": "I need storage for images",
            "agent_response": "I suggest Hot tier storage",
            "type": "conversation"
        }
        
        self.memory.add_conversation_entry(entry1)
        
        history = self.memory.get_conversation_history()
        assert len(history) == 1
        assert history[0]["user_input"] == "I need storage for images"
        assert "timestamp" in history[0]  # Timestamp should be added
        
        # Add another entry
        entry2 = {
            "user_input": "Make it cheaper",
            "agent_response": "Switching to Cool tier",
            "type": "conversation"
        }
        
        self.memory.add_conversation_entry(entry2)
        
        history = self.memory.get_conversation_history()
        assert len(history) == 2
    
    def test_recent_conversations(self):
        """Test getting recent conversations with limit."""
        # Add multiple entries
        for i in range(15):
            entry = {
                "user_input": f"Message {i}",
                "type": "test"
            }
            self.memory.add_conversation_entry(entry)
        
        # Test default limit
        recent = self.memory.get_recent_conversations()
        assert len(recent) == 10
        assert recent[-1]["user_input"] == "Message 14"  # Most recent
        
        # Test custom limit
        recent_5 = self.memory.get_recent_conversations(5)
        assert len(recent_5) == 5
        assert recent_5[-1]["user_input"] == "Message 14"
    
    def test_conversation_history_limit(self):
        """Test that conversation history is limited to prevent file bloat."""
        # Add more than 100 entries
        for i in range(105):
            entry = {"user_input": f"Message {i}", "type": "test"}
            self.memory.add_conversation_entry(entry)
        
        history = self.memory.get_conversation_history()
        assert len(history) == 100  # Should be limited to 100
        assert history[0]["user_input"] == "Message 5"  # First 5 should be removed
        assert history[-1]["user_input"] == "Message 104"
    
    def test_clear_conversation_history(self):
        """Test clearing conversation history."""
        # Add some entries
        for i in range(3):
            entry = {"user_input": f"Message {i}", "type": "test"}
            self.memory.add_conversation_entry(entry)
        
        assert len(self.memory.get_conversation_history()) == 3
        
        # Clear history
        self.memory.clear_conversation_history()
        
        history = self.memory.get_conversation_history()
        assert len(history) == 0
    
    def test_backup_data(self):
        """Test data backup functionality."""
        # Add some test data
        self.memory.set_preference("test_pref", "test_value")
        self.memory.add_conversation_entry({"test": "entry"})
        
        # Create backup
        backup_dir = Path(self.temp_dir) / "test_backups"
        backup_files = self.memory.backup_data(str(backup_dir))
        
        assert "preferences" in backup_files
        assert "history" in backup_files
        
        # Verify backup files exist and contain data
        pref_backup = Path(backup_files["preferences"])
        assert pref_backup.exists()
        
        with open(pref_backup, 'r') as f:
            backup_prefs = json.load(f)
            assert backup_prefs["test_pref"] == "test_value"
        
        hist_backup = Path(backup_files["history"])
        assert hist_backup.exists()
        
        with open(hist_backup, 'r') as f:
            backup_hist = json.load(f)
            assert len(backup_hist["conversations"]) == 1
    
    def test_file_corruption_handling(self):
        """Test handling of corrupted JSON files."""
        # Corrupt the preferences file
        with open(self.memory.preferences_file, 'w') as f:
            f.write("invalid json {")
        
        # Should raise JSONMemoryError
        with pytest.raises(JSONMemoryError) as exc_info:
            self.memory.get_preferences()
        
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_missing_file_handling(self):
        """Test handling of missing files."""
        # Remove preferences file
        self.memory.preferences_file.unlink()
        
        with pytest.raises(JSONMemoryError) as exc_info:
            self.memory.get_preferences()
        
        assert "File not found" in str(exc_info.value)
    
    def test_create_memory_factory(self):
        """Test factory function."""
        temp_dir2 = tempfile.mkdtemp()
        try:
            memory = create_memory(temp_dir2)
            assert isinstance(memory, JSONMemory)
            assert memory.data_dir == Path(temp_dir2)
            assert memory.preferences_file.exists()
        finally:
            if Path(temp_dir2).exists():
                shutil.rmtree(temp_dir2)
    
    def test_timestamp_addition(self):
        """Test that timestamps are added to conversation entries."""
        entry_without_timestamp = {
            "user_input": "Test message",
            "type": "test"
        }
        
        self.memory.add_conversation_entry(entry_without_timestamp)
        
        history = self.memory.get_conversation_history()
        assert "timestamp" in history[0]
        
        # Verify timestamp format
        timestamp_str = history[0]["timestamp"]
        # Should be able to parse as ISO format
        datetime.fromisoformat(timestamp_str)
    
    def test_entry_with_existing_timestamp(self):
        """Test that existing timestamps are preserved."""
        custom_timestamp = "2023-01-01T12:00:00"
        entry_with_timestamp = {
            "user_input": "Test message",
            "type": "test",
            "timestamp": custom_timestamp
        }
        
        self.memory.add_conversation_entry(entry_with_timestamp)
        
        history = self.memory.get_conversation_history()
        assert history[0]["timestamp"] == custom_timestamp