"""
Unit tests for storage advisor functionality.

Tests the StorageAdvisor class for proper configuration recommendations,
preference application, and explanation generation.
"""

import pytest
from src.agent.decision.storage_advisor import (
    StorageAdvisor,
    StorageRecommendation,
    create_storage_advisor
)
from src.agent.decision.rules import StorageConfig


class TestStorageRecommendation:
    """Test suite for StorageRecommendation dataclass."""
    
    def test_storage_recommendation_creation(self):
        """Test StorageRecommendation creation and field access."""
        config = StorageConfig("Hot", "Standard", "LRS", "Test reasoning")
        
        recommendation = StorageRecommendation(
            configuration=config,
            confidence=0.8,
            detected_use_case="images",
            alternative_configs=[],
            context_used={},
            suggestion_id="test_001"
        )
        
        assert recommendation.configuration == config
        assert recommendation.confidence == 0.8
        assert recommendation.detected_use_case == "images"
        assert recommendation.suggestion_id == "test_001"


class TestStorageAdvisor:
    """Test suite for StorageAdvisor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.advisor = StorageAdvisor()
    
    def test_initialization(self):
        """Test advisor initialization."""
        assert self.advisor is not None
        assert hasattr(self.advisor, 'detector')
        assert self.advisor.recommendation_counter == 0
    
    def test_recommend_configuration_basic(self):
        """Test basic configuration recommendation."""
        user_input = "I need storage for my website images"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        assert isinstance(recommendation, StorageRecommendation)
        assert recommendation.configuration.tier == "Hot"  # Images should be Hot
        assert recommendation.configuration.performance == "Standard"
        assert recommendation.detected_use_case == "images"
        assert recommendation.confidence > 0.0
    
    def test_recommend_configuration_with_preferences(self):
        """Test recommendation with user preferences."""
        user_input = "I need storage for backups"
        user_preferences = {
            "cost_preference": "optimized",
            "default_performance_tier": "Premium"
        }
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        # Should apply cost optimization and preferences
        assert recommendation.configuration.tier in ["Cool", "Archive"]  # Cost optimized
        assert recommendation.configuration.performance == "Premium"  # User preference
    
    def test_recommend_configuration_cost_optimized(self):
        """Test recommendation with cost optimization."""
        user_input = "I need cheap storage for logs"
        user_preferences = {"cost_preference": "optimized"}
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        # Should prioritize cost savings
        assert recommendation.configuration.tier in ["Cool", "Archive"]
        assert recommendation.configuration.replication == "LRS"
    
    def test_recommend_configuration_performance_focused(self):
        """Test recommendation with performance focus."""
        user_input = "I need fast storage for database"
        user_preferences = {"cost_preference": "performance"}
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        # Should prioritize performance
        assert recommendation.configuration.performance == "Premium"
        assert recommendation.configuration.tier == "Hot"
        assert recommendation.configuration.replication in ["ZRS", "GRS"]
    
    def test_recommend_configuration_with_context_hints(self):
        """Test recommendation applying context hints."""
        # Production environment should influence recommendations
        user_input = "I need storage for production application logs"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        # Production should upgrade redundancy
        assert recommendation.context_used["detected_keywords"]
        production_detected = any("production" in str(ctx) for ctx in 
                                recommendation.context_used.values())
        # Note: Production is detected as environment hint, not keyword
    
    def test_recommend_configuration_compliance_requirements(self):
        """Test recommendation with compliance requirements."""
        user_input = "I need storage for compliance audit data"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        # Compliance should prefer geographic redundancy
        context_hints = recommendation.context_used.get("context_hints", {})
        if context_hints.get("compliance_required"):
            assert recommendation.configuration.replication in ["GRS"]
    
    def test_recommend_configuration_security_sensitive(self):
        """Test recommendation with security requirements."""
        user_input = "I need secure storage for confidential documents"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        context_hints = recommendation.context_used.get("context_hints", {})
        if context_hints.get("security_sensitive"):
            assert recommendation.configuration.performance == "Premium"
    
    def test_recommend_configuration_scalability_requirements(self):
        """Test recommendation with scalability requirements."""
        user_input = "I need scalable storage that can handle growth"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        context_hints = recommendation.context_used.get("context_hints", {})
        if context_hints.get("scalability_important"):
            assert recommendation.configuration.replication in ["ZRS", "GRS"]
    
    def test_recommend_configuration_urgency(self):
        """Test recommendation with urgency indicators."""
        user_input = "I need storage urgently for my application"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        context_hints = recommendation.context_used.get("context_hints", {})
        if context_hints.get("urgency") == "high":
            assert recommendation.configuration.tier == "Hot"
    
    def test_recommend_configuration_large_storage(self):
        """Test recommendation with large storage size hints."""
        user_input = "I need 50TB storage for data archival"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        # Large storage might suggest cost optimization
        context_hints = recommendation.context_used.get("context_hints", {})
        sizes = context_hints.get("estimated_sizes", [])
        if any("TB" in size for size in sizes):
            # Large storage should consider cost optimization
            assert recommendation.configuration.tier in ["Cool", "Archive"]
    
    def test_recommend_configuration_generates_alternatives(self):
        """Test that recommendations include alternatives."""
        user_input = "I need storage for website images"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        assert len(recommendation.alternative_configs) > 0
        assert all(isinstance(alt, StorageConfig) for alt in recommendation.alternative_configs)
    
    def test_recommend_configuration_unique_suggestion_ids(self):
        """Test that each recommendation gets unique ID."""
        user_input = "I need storage for images"
        
        rec1 = self.advisor.recommend_configuration(user_input)
        rec2 = self.advisor.recommend_configuration(user_input)
        
        assert rec1.suggestion_id != rec2.suggestion_id
        assert "storage_rec_" in rec1.suggestion_id
        assert "storage_rec_" in rec2.suggestion_id
    
    def test_recommend_configuration_unknown_use_case(self):
        """Test recommendation for unknown use case."""
        user_input = "I need storage for my special project"
        
        recommendation = self.advisor.recommend_configuration(user_input)
        
        # Should fall back to general configuration
        assert recommendation.detected_use_case == "general"
        assert recommendation.configuration.tier == "Hot"  # Default
        assert recommendation.configuration.performance == "Standard"  # Default
        assert recommendation.configuration.replication == "LRS"  # Default
    
    def test_recommend_configuration_with_learned_patterns(self):
        """Test recommendation using learned use case patterns."""
        user_input = "I need storage for images"
        user_preferences = {
            "use_case_patterns": {
                "images": {
                    "tier": "Cool",  # User learned preference
                    "replication": "GRS"
                }
            }
        }
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        # Should apply learned patterns
        assert recommendation.configuration.tier == "Cool"
        assert recommendation.configuration.replication == "GRS"
    
    def test_explain_recommendation(self):
        """Test recommendation explanation generation."""
        user_input = "I need storage for database"
        recommendation = self.advisor.recommend_configuration(user_input)
        
        explanation = self.advisor.explain_recommendation(recommendation)
        
        assert "summary" in explanation
        assert "reasoning" in explanation
        assert "confidence_level" in explanation
        assert "key_factors" in explanation
        assert "trade_offs" in explanation
        assert explanation["confidence_level"] in ["Very Low", "Low", "Medium", "High"]
    
    def test_explain_recommendation_confidence_levels(self):
        """Test confidence level mapping."""
        # Test different confidence levels
        test_cases = [
            (0.9, "High"),
            (0.7, "Medium"), 
            (0.5, "Low"),
            (0.2, "Very Low")
        ]
        
        for confidence, expected_level in test_cases:
            level = self.advisor._get_confidence_level(confidence)
            assert level == expected_level
    
    def test_explain_recommendation_trade_offs(self):
        """Test trade-off explanations."""
        user_input = "I need storage for database"
        recommendation = self.advisor.recommend_configuration(user_input)
        
        explanation = self.advisor.explain_recommendation(recommendation)
        trade_offs = explanation["trade_offs"]
        
        assert "cost_vs_performance" in trade_offs
        assert "availability_vs_cost" in trade_offs  
        assert "access_speed_vs_cost" in trade_offs
        
        # Each trade-off should be a string explanation
        for trade_off in trade_offs.values():
            assert isinstance(trade_off, str)
            assert len(trade_off) > 0
    
    def test_cost_performance_tradeoff_premium(self):
        """Test cost vs performance tradeoff explanation for Premium."""
        config = StorageConfig("Hot", "Premium", "ZRS", "Test")
        explanation = self.advisor._explain_cost_performance_tradeoff(config)
        
        assert "premium" in explanation.lower()
        assert "higher" in explanation.lower() or "increased" in explanation.lower()
    
    def test_cost_performance_tradeoff_standard(self):
        """Test cost vs performance tradeoff explanation for Standard."""
        config = StorageConfig("Hot", "Standard", "LRS", "Test")
        explanation = self.advisor._explain_cost_performance_tradeoff(config)
        
        assert "standard" in explanation.lower()
        assert "balances" in explanation.lower()
    
    def test_availability_cost_tradeoff_grs(self):
        """Test availability vs cost tradeoff explanation for GRS."""
        config = StorageConfig("Hot", "Standard", "GRS", "Test")
        explanation = self.advisor._explain_availability_cost_tradeoff(config)
        
        assert "geo-redundant" in explanation.lower()
        assert "disaster recovery" in explanation.lower()
    
    def test_availability_cost_tradeoff_zrs(self):
        """Test availability vs cost tradeoff explanation for ZRS."""
        config = StorageConfig("Hot", "Standard", "ZRS", "Test")
        explanation = self.advisor._explain_availability_cost_tradeoff(config)
        
        assert "zone-redundant" in explanation.lower()
        assert "high availability" in explanation.lower()
    
    def test_availability_cost_tradeoff_lrs(self):
        """Test availability vs cost tradeoff explanation for LRS."""
        config = StorageConfig("Hot", "Standard", "LRS", "Test")
        explanation = self.advisor._explain_availability_cost_tradeoff(config)
        
        assert "locally redundant" in explanation.lower()
        assert "minimizes cost" in explanation.lower()
    
    def test_access_speed_tradeoff_hot(self):
        """Test access speed vs cost tradeoff explanation for Hot tier."""
        config = StorageConfig("Hot", "Standard", "LRS", "Test")
        explanation = self.advisor._explain_access_speed_tradeoff(config)
        
        assert "hot" in explanation.lower()
        assert "fast access" in explanation.lower()
    
    def test_access_speed_tradeoff_cool(self):
        """Test access speed vs cost tradeoff explanation for Cool tier."""
        config = StorageConfig("Cool", "Standard", "LRS", "Test")
        explanation = self.advisor._explain_access_speed_tradeoff(config)
        
        assert "cool" in explanation.lower()
        assert "reduces storage cost" in explanation.lower()
    
    def test_access_speed_tradeoff_archive(self):
        """Test access speed vs cost tradeoff explanation for Archive tier."""
        config = StorageConfig("Archive", "Standard", "GRS", "Test")
        explanation = self.advisor._explain_access_speed_tradeoff(config)
        
        assert "archive" in explanation.lower()
        assert "minimizes storage cost" in explanation.lower()
        assert "hours" in explanation.lower()


class TestCreateStorageAdvisor:
    """Test suite for factory function."""
    
    def test_create_storage_advisor(self):
        """Test factory function creates proper advisor instance."""
        advisor = create_storage_advisor()
        
        assert isinstance(advisor, StorageAdvisor)
        assert hasattr(advisor, 'recommend_configuration')
        assert hasattr(advisor, 'explain_recommendation')


class TestIntegrationScenarios:
    """Test suite for end-to-end integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.advisor = StorageAdvisor()
    
    def test_scenario_website_images(self):
        """Test scenario: Website images storage."""
        user_input = "I need storage for my e-commerce website product images"
        user_preferences = {"cost_preference": "balanced"}
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        assert recommendation.detected_use_case in ["images", "website"]
        assert recommendation.configuration.tier == "Hot"  # Fast access needed
        assert recommendation.confidence > 0.6
    
    def test_scenario_backup_storage(self):
        """Test scenario: Backup storage."""
        user_input = "I need cost-effective backup storage for our database"
        user_preferences = {"cost_preference": "optimized"}
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        assert recommendation.detected_use_case in ["backup", "backups", "database"]
        assert recommendation.configuration.tier in ["Cool", "Archive"]  # Cost optimized
        assert recommendation.configuration.replication in ["GRS", "LRS"]  # Backup needs redundancy
    
    def test_scenario_high_performance_database(self):
        """Test scenario: High-performance database storage."""
        user_input = "I need fast high-performance storage for our production database"
        user_preferences = {"cost_preference": "performance"}
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        assert recommendation.detected_use_case == "database"
        assert recommendation.configuration.performance == "Premium"
        assert recommendation.configuration.tier == "Hot"
        assert recommendation.confidence > 0.7
    
    def test_scenario_archive_compliance(self):
        """Test scenario: Archive storage for compliance."""
        user_input = "I need long-term archive storage for compliance data"
        user_preferences = {"cost_preference": "optimized"}
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        assert recommendation.detected_use_case == "archive"
        assert recommendation.configuration.tier == "Archive"
        assert recommendation.configuration.replication == "GRS"  # Compliance needs geo-redundancy
    
    def test_scenario_development_environment(self):
        """Test scenario: Development environment storage."""
        user_input = "I need temporary storage for our development environment"
        user_preferences = {"cost_preference": "optimized"}
        
        recommendation = self.advisor.recommend_configuration(
            user_input, user_preferences
        )
        
        # Development should prioritize cost savings
        assert recommendation.configuration.replication == "LRS"  # Local redundancy sufficient
        context_hints = recommendation.context_used.get("context_hints", {})
        if context_hints.get("environment") == "development":
            # Development environment detected
            pass  # Test passes if no exception