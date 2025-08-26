"""
Unit tests for user profile functionality.

Tests the UserProfile class for preference management, learning capabilities,
and context generation.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from src.agent.memory.user_profile import UserProfile, create_user_profile
from src.agent.memory.json_memory import JSONMemory


class TestUserProfile:
    """Test suite for UserProfile class."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.memory = JSONMemory(self.temp_dir)
        self.profile = UserProfile(self.memory)
    
    def teardown_method(self):
        """Clean up temporary directory after tests."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_default_preferences(self):
        """Test default preference values."""
        assert self.profile.get_preferred_regions() == ["eastus", "westus2"]
        assert self.profile.get_naming_pattern() == "descriptive"
        assert self.profile.get_cost_preference() == "optimized"
        assert self.profile.get_default_performance_tier() == "Standard"
        assert self.profile.get_default_replication() == "LRS"
    
    def test_set_preferred_regions(self):
        """Test setting preferred regions."""
        new_regions = ["westus", "centralus", "eastus2"]
        self.profile.set_preferred_regions(new_regions)
        
        assert self.profile.get_preferred_regions() == new_regions
    
    def test_set_naming_pattern(self):
        """Test setting naming pattern with validation."""
        # Valid patterns
        self.profile.set_naming_pattern("short")
        assert self.profile.get_naming_pattern() == "short"
        
        self.profile.set_naming_pattern("company")
        assert self.profile.get_naming_pattern() == "company"
        
        # Invalid pattern should raise error
        with pytest.raises(ValueError) as exc_info:
            self.profile.set_naming_pattern("invalid_pattern")
        
        assert "Invalid naming pattern" in str(exc_info.value)
    
    def test_set_cost_preference(self):
        """Test setting cost preference with validation."""
        # Valid preferences
        self.profile.set_cost_preference("performance")
        assert self.profile.get_cost_preference() == "performance"
        
        self.profile.set_cost_preference("balanced")
        assert self.profile.get_cost_preference() == "balanced"
        
        # Invalid preference should raise error
        with pytest.raises(ValueError) as exc_info:
            self.profile.set_cost_preference("invalid_preference")
        
        assert "Invalid cost preference" in str(exc_info.value)
    
    def test_set_performance_tier(self):
        """Test setting performance tier with validation."""
        self.profile.set_default_performance_tier("Premium")
        assert self.profile.get_default_performance_tier() == "Premium"
        
        # Invalid tier should raise error
        with pytest.raises(ValueError) as exc_info:
            self.profile.set_default_performance_tier("Invalid")
        
        assert "Invalid performance tier" in str(exc_info.value)
    
    def test_set_replication(self):
        """Test setting replication with validation."""
        self.profile.set_default_replication("GRS")
        assert self.profile.get_default_replication() == "GRS"
        
        self.profile.set_default_replication("ZRS")
        assert self.profile.get_default_replication() == "ZRS"
        
        # Invalid replication should raise error
        with pytest.raises(ValueError) as exc_info:
            self.profile.set_default_replication("Invalid")
        
        assert "Invalid replication type" in str(exc_info.value)
    
    def test_use_case_config_learning(self):
        """Test learning and retrieving use case configurations."""
        # Initially no custom config
        analytics_config = self.profile.get_use_case_config("analytics")
        assert analytics_config is None
        
        # Learn new configuration
        new_config = {"tier": "Cool", "replication": "GRS", "performance": "Standard"}
        self.profile.learn_use_case_config("analytics", new_config)
        
        # Retrieve learned configuration
        learned_config = self.profile.get_use_case_config("analytics")
        assert learned_config == new_config
        
        # Test getting existing default config
        images_config = self.profile.get_use_case_config("images")
        assert images_config is not None
        assert images_config["tier"] == "Hot"
    
    def test_storage_name_suggestions_descriptive(self):
        """Test storage name suggestions with descriptive pattern."""
        self.profile.set_naming_pattern("descriptive")
        
        # Test with known use cases
        assert self.profile.suggest_storage_name("images") == "webapp-images-storage"
        assert self.profile.suggest_storage_name("backups") == "database-backup-storage"
        assert self.profile.suggest_storage_name("logs") == "application-logs-storage"
        
        # Test with unknown use case
        assert self.profile.suggest_storage_name("custom") == "custom-storage"
        
        # Test with base name provided
        custom_name = self.profile.suggest_storage_name("images", "my-custom-name")
        assert custom_name == "my-custom-name"
    
    def test_storage_name_suggestions_short(self):
        """Test storage name suggestions with short pattern."""
        self.profile.set_naming_pattern("short")
        
        # Test with known use cases (should include timestamp)
        images_name = self.profile.suggest_storage_name("images")
        assert "imgstore" in images_name
        assert len(images_name) > len("imgstore")  # Should have timestamp
        
        backups_name = self.profile.suggest_storage_name("backups")
        assert "bkpstore" in backups_name
    
    def test_storage_name_suggestions_company(self):
        """Test storage name suggestions with company pattern."""
        self.profile.set_naming_pattern("company")
        
        # Test with default company prefix
        images_name = self.profile.suggest_storage_name("images")
        assert images_name == "companyimagesstorage"
        
        # Test with custom company prefix
        self.memory.set_preference("company_prefix", "acme")
        logs_name = self.profile.suggest_storage_name("logs")
        assert logs_name == "acmelogsstorage"
    
    def test_deployment_history_tracking(self):
        """Test tracking deployment history for learning."""
        deployment = {
            "success": True,
            "use_case": "images",
            "access_tier": "Hot",
            "replication_type": "LRS",
            "performance_tier": "Standard",
            "storage_name": "test-images-storage"
        }
        
        self.profile.add_deployment_history(deployment)
        
        # Should learn from successful deployment
        learned_config = self.profile.get_use_case_config("images")
        assert learned_config["tier"] == "Hot"
        assert learned_config["replication"] == "LRS"
        assert learned_config["performance"] == "Standard"
        
        # Check conversation history was updated
        conversations = self.memory.get_conversation_history()
        assert len(conversations) == 1
        assert conversations[0]["type"] == "deployment"
    
    def test_feedback_learning_cost_optimization(self):
        """Test learning from cost-related feedback."""
        # Initially optimized preference
        assert self.profile.get_cost_preference() == "optimized"
        
        # Change to balanced and test cost feedback
        self.profile.set_cost_preference("balanced")
        
        feedback = {
            "type": "suggestion_rejected",
            "reason": "too expensive for my budget",
            "suggestion": {"tier": "Hot", "performance": "Premium"}
        }
        
        self.profile.add_feedback(feedback)
        
        # Should learn to prefer cost optimization
        assert self.profile.get_cost_preference() == "optimized"
    
    def test_feedback_learning_performance(self):
        """Test learning from performance-related feedback."""
        # Start with optimized preference
        assert self.profile.get_cost_preference() == "optimized"
        
        feedback = {
            "type": "suggestion_rejected",
            "reason": "too slow, need better performance",
            "suggestion": {"tier": "Hot", "performance": "Standard"}
        }
        
        self.profile.add_feedback(feedback)
        
        # Should learn to prefer performance
        assert self.profile.get_cost_preference() == "performance"
    
    def test_context_for_conversation(self):
        """Test generating conversation context."""
        # Add some deployment history
        deployment1 = {
            "success": True,
            "use_case": "images",
            "access_tier": "Hot",
            "storage_name": "images-storage-1"
        }
        deployment2 = {
            "success": True,
            "use_case": "backups",
            "access_tier": "Cool",
            "storage_name": "backup-storage-1"
        }
        
        self.profile.add_deployment_history(deployment1)
        self.profile.add_deployment_history(deployment2)
        
        context = self.profile.get_context_for_conversation()
        
        # Check user preferences are included
        assert "user_preferences" in context
        prefs = context["user_preferences"]
        assert prefs["preferred_regions"] == ["eastus", "westus2"]
        assert prefs["cost_preference"] == "optimized"
        
        # Check recent deployments are included
        assert "recent_deployments" in context
        assert len(context["recent_deployments"]) == 2
        
        # Check learned patterns are included
        assert "learned_patterns" in context
        patterns = context["learned_patterns"]
        assert "images" in patterns  # Should have learned from deployment
    
    def test_profile_summary(self):
        """Test generating profile summary."""
        # Add some activity
        self.profile.add_deployment_history({
            "success": True,
            "use_case": "images",
            "access_tier": "Hot"
        })
        self.profile.add_deployment_history({
            "success": False,
            "use_case": "logs",
            "error": "timeout"
        })
        
        summary = self.profile.get_summary()
        
        assert "preferences" in summary
        assert "learned_patterns" in summary
        assert "stats" in summary
        assert "recent_activity" in summary
        
        stats = summary["stats"]
        assert stats["total_conversations"] == 2  # 2 deployment entries
        assert stats["total_deployments"] == 2
        assert stats["successful_deployments"] == 1
    
    def test_create_user_profile_factory(self):
        """Test factory function."""
        temp_dir2 = tempfile.mkdtemp()
        try:
            profile = create_user_profile(temp_dir2)
            assert isinstance(profile, UserProfile)
            assert profile.get_preferred_regions() == ["eastus", "westus2"]
        finally:
            if Path(temp_dir2).exists():
                shutil.rmtree(temp_dir2)
    
    def test_failed_deployment_no_learning(self):
        """Test that failed deployments don't trigger learning."""
        failed_deployment = {
            "success": False,
            "use_case": "images",
            "access_tier": "Hot",
            "error": "deployment failed"
        }
        
        # Get initial pattern
        initial_pattern = self.profile.get_use_case_config("images")
        
        self.profile.add_deployment_history(failed_deployment)
        
        # Pattern should not change from failed deployment
        final_pattern = self.profile.get_use_case_config("images") 
        assert final_pattern == initial_pattern
    
    def test_deployment_without_use_case_no_learning(self):
        """Test that deployments without use case don't trigger learning."""
        deployment_no_use_case = {
            "success": True,
            "access_tier": "Hot",
            "storage_name": "test-storage"
            # Missing use_case
        }
        
        self.profile.add_deployment_history(deployment_no_use_case)
        
        # Should not create new learned patterns
        context = self.profile.get_context_for_conversation()
        learned_patterns = context["learned_patterns"]
        
        # Should only have default patterns, no new ones learned
        default_keys = ["images", "backups", "logs"]
        for key in learned_patterns.keys():
            assert key in default_keys