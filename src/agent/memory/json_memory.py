"""
Simple JSON-based memory system for the Azure Storage Agent.

Provides file-based storage for user preferences and conversation history
without requiring external databases.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class JSONMemoryError(Exception):
    """Exception raised for JSON memory operations."""
    pass


class JSONMemory:
    """
    Simple JSON file-based memory system for storing user data locally.
    
    Handles user preferences and conversation history with automatic
    file creation and error handling.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize JSON memory with specified data directory.
        
        Args:
            data_dir (str): Directory path for storing JSON files.
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.preferences_file = self.data_dir / "user_preferences.json"
        self.history_file = self.data_dir / "conversation_history.json"
        
        # Initialize files if they don't exist
        self._ensure_files_exist()
    
    def _ensure_files_exist(self) -> None:
        """Create JSON files with default structure if they don't exist."""
        if not self.preferences_file.exists():
            default_preferences = {
                "preferred_regions": ["eastus", "westus2"],
                "naming_pattern": "descriptive",
                "cost_preference": "optimized",
                "default_performance_tier": "Standard",
                "default_replication": "LRS",
                "use_case_patterns": {
                    "images": {"tier": "Hot", "replication": "LRS"},
                    "backups": {"tier": "Cool", "replication": "GRS"},
                    "logs": {"tier": "Cool", "replication": "LRS"}
                }
            }
            self._write_json_file(self.preferences_file, default_preferences)
        
        if not self.history_file.exists():
            default_history = {
                "conversations": [],
                "last_updated": datetime.now().isoformat()
            }
            self._write_json_file(self.history_file, default_history)
    
    def _read_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Safely read JSON file with error handling.
        
        Args:
            file_path (Path): Path to JSON file.
            
        Returns:
            Dict[str, Any]: Parsed JSON data.
            
        Raises:
            JSONMemoryError: If file reading or parsing fails.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise JSONMemoryError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise JSONMemoryError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise JSONMemoryError(f"Error reading {file_path}: {e}")
    
    def _write_json_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Safely write JSON file with error handling.
        
        Args:
            file_path (Path): Path to JSON file.
            data (Dict[str, Any]): Data to write.
            
        Raises:
            JSONMemoryError: If file writing fails.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise JSONMemoryError(f"Error writing {file_path}: {e}")
    
    def get_preferences(self) -> Dict[str, Any]:
        """
        Get current user preferences.
        
        Returns:
            Dict[str, Any]: User preferences dictionary.
        """
        return self._read_json_file(self.preferences_file)
    
    def update_preferences(self, updates: Dict[str, Any]) -> None:
        """
        Update user preferences with new values.
        
        Args:
            updates (Dict[str, Any]): Preference updates to apply.
        """
        preferences = self.get_preferences()
        preferences.update(updates)
        self._write_json_file(self.preferences_file, preferences)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get specific preference value.
        
        Args:
            key (str): Preference key.
            default (Any): Default value if key not found.
            
        Returns:
            Any: Preference value or default.
        """
        preferences = self.get_preferences()
        return preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Set specific preference value.
        
        Args:
            key (str): Preference key.
            value (Any): Preference value.
        """
        self.update_preferences({key: value})
    
    def add_use_case_pattern(self, use_case: str, config: Dict[str, str]) -> None:
        """
        Add or update use case configuration pattern.
        
        Args:
            use_case (str): Use case name (e.g., "images", "backups").
            config (Dict[str, str]): Storage configuration for use case.
        """
        preferences = self.get_preferences()
        if "use_case_patterns" not in preferences:
            preferences["use_case_patterns"] = {}
        
        preferences["use_case_patterns"][use_case] = config
        self._write_json_file(self.preferences_file, preferences)
    
    def get_use_case_pattern(self, use_case: str) -> Optional[Dict[str, str]]:
        """
        Get storage configuration pattern for use case.
        
        Args:
            use_case (str): Use case name.
            
        Returns:
            Optional[Dict[str, str]]: Configuration pattern or None.
        """
        preferences = self.get_preferences()
        patterns = preferences.get("use_case_patterns", {})
        return patterns.get(use_case)
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Returns:
            List[Dict[str, Any]]: List of conversation entries.
        """
        history_data = self._read_json_file(self.history_file)
        return history_data.get("conversations", [])
    
    def add_conversation_entry(self, entry: Dict[str, Any]) -> None:
        """
        Add new conversation entry to history.
        
        Args:
            entry (Dict[str, Any]): Conversation entry with timestamp, user input, etc.
        """
        history_data = self._read_json_file(self.history_file)
        
        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()
        
        history_data["conversations"].append(entry)
        history_data["last_updated"] = datetime.now().isoformat()
        
        # Keep only last 100 conversations to prevent file bloat
        if len(history_data["conversations"]) > 100:
            history_data["conversations"] = history_data["conversations"][-100:]
        
        self._write_json_file(self.history_file, history_data)
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent conversations.
        
        Args:
            limit (int): Maximum number of conversations to return.
            
        Returns:
            List[Dict[str, Any]]: Recent conversation entries.
        """
        conversations = self.get_conversation_history()
        return conversations[-limit:] if conversations else []
    
    def clear_conversation_history(self) -> None:
        """Clear all conversation history."""
        history_data = {
            "conversations": [],
            "last_updated": datetime.now().isoformat()
        }
        self._write_json_file(self.history_file, history_data)
    
    def backup_data(self, backup_dir: str = "backups") -> Dict[str, str]:
        """
        Create backup of all memory data.
        
        Args:
            backup_dir (str): Directory for backup files.
            
        Returns:
            Dict[str, str]: Paths of created backup files.
        """
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_files = {}
        
        # Backup preferences
        pref_backup = backup_path / f"user_preferences_{timestamp}.json"
        preferences = self.get_preferences()
        self._write_json_file(pref_backup, preferences)
        backup_files["preferences"] = str(pref_backup)
        
        # Backup history
        hist_backup = backup_path / f"conversation_history_{timestamp}.json"
        history = self._read_json_file(self.history_file)
        self._write_json_file(hist_backup, history)
        backup_files["history"] = str(hist_backup)
        
        return backup_files


def create_memory(data_dir: str = "data") -> JSONMemory:
    """
    Factory function to create JSONMemory instance.
    
    Args:
        data_dir (str): Directory for storing JSON files.
        
    Returns:
        JSONMemory: Configured memory instance.
    """
    return JSONMemory(data_dir)