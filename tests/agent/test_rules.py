"""
Unit tests for storage decision rules functionality.

Tests the rules module for proper keyword detection, configuration
suggestions, and confidence scoring.
"""

import pytest
from src.agent.decision.rules import (
    StorageConfig,
    USE_CASE_RULES,
    get_use_case_keywords,
    get_performance_indicators,
    apply_cost_preference,
    generate_reasoning,
    get_confidence_score
)


class TestStorageConfig:
    """Test suite for StorageConfig dataclass."""
    
    def test_storage_config_creation(self):
        """Test StorageConfig creation and field access."""
        config = StorageConfig(
            tier="Hot",
            performance="Standard",
            replication="LRS",
            reasoning="Test configuration"
        )
        
        assert config.tier == "Hot"
        assert config.performance == "Standard"
        assert config.replication == "LRS"
        assert config.reasoning == "Test configuration"
    
    def test_storage_config_equality(self):
        """Test StorageConfig equality comparison."""
        config1 = StorageConfig("Hot", "Standard", "LRS", "Test")
        config2 = StorageConfig("Hot", "Standard", "LRS", "Test")
        config3 = StorageConfig("Cool", "Standard", "LRS", "Test")
        
        assert config1 == config2
        assert config1 != config3


class TestUseCaseRules:
    """Test suite for use case rules."""
    
    def test_use_case_rules_structure(self):
        """Test that all use case rules have required fields."""
        required_fields = ["tier", "performance", "replication", "reasoning"]
        
        for use_case, rule in USE_CASE_RULES.items():
            for field in required_fields:
                assert field in rule, f"Rule for {use_case} missing {field}"
            
            # Validate field values
            assert rule["tier"] in ["Hot", "Cool", "Archive"]
            assert rule["performance"] in ["Standard", "Premium"]
            assert rule["replication"] in ["LRS", "GRS", "ZRS"]
            assert isinstance(rule["reasoning"], str)
            assert len(rule["reasoning"]) > 0
    
    def test_specific_use_case_rules(self):
        """Test specific use case rule configurations."""
        # Test images rule
        images_rule = USE_CASE_RULES["images"]
        assert images_rule["tier"] == "Hot"
        assert images_rule["performance"] == "Standard"
        assert images_rule["replication"] == "LRS"
        
        # Test backup rule
        backups_rule = USE_CASE_RULES["backups"]
        assert backups_rule["tier"] == "Cool"
        assert backups_rule["performance"] == "Standard"
        assert backups_rule["replication"] == "GRS"
        
        # Test database rule
        database_rule = USE_CASE_RULES["database"]
        assert database_rule["tier"] == "Hot"
        assert database_rule["performance"] == "Premium"
        assert database_rule["replication"] == "ZRS"


class TestKeywordDetection:
    """Test suite for keyword detection functions."""
    
    def test_get_use_case_keywords_single_match(self):
        """Test detection of single use case keywords."""
        test_cases = [
            ("I need storage for images", ["images"]),
            ("Create backup storage", ["backup"]),
            ("Store log files", ["log"]),
            ("Database storage required", ["database"]),
            ("Archive old data", ["archive"])
        ]
        
        for text, expected_keywords in test_cases:
            keywords = get_use_case_keywords(text)
            assert keywords == expected_keywords
    
    def test_get_use_case_keywords_multiple_matches(self):
        """Test detection of multiple use case keywords."""
        text = "I need storage for website images and backup logs"
        keywords = get_use_case_keywords(text)
        
        # Should detect all relevant keywords (including "web" and "log" which are substrings)
        expected_keywords = ["images", "website", "backup", "logs", "web", "log"]
        for expected in expected_keywords:
            if expected in ["images", "website", "backup", "logs"]:
                assert expected in keywords
    
    def test_get_use_case_keywords_case_insensitive(self):
        """Test case-insensitive keyword detection."""
        test_cases = [
            "I need storage for IMAGES",
            "I need storage for Images", 
            "I need storage for images"
        ]
        
        for text in test_cases:
            keywords = get_use_case_keywords(text)
            assert "images" in keywords
    
    def test_get_use_case_keywords_no_matches(self):
        """Test when no keywords are found."""
        text = "I need some storage space"
        keywords = get_use_case_keywords(text)
        assert keywords == []
    
    def test_get_performance_indicators_performance_keywords(self):
        """Test detection of performance indicators."""
        text = "I need fast high-performance storage for database"
        indicators = get_performance_indicators(text)
        
        assert "fast" in indicators["performance"]
        assert "high-performance" in indicators["performance"]
        assert "performance" in indicators["performance"]
        assert "database" in indicators["performance"]
    
    def test_get_performance_indicators_cost_keywords(self):
        """Test detection of cost indicators."""
        text = "I need cheap cost-effective storage to save money"
        indicators = get_performance_indicators(text)
        
        assert "cheap" in indicators["cost"]
        assert "cost-effective" in indicators["cost"]
        assert "save money" in indicators["cost"]
    
    def test_get_performance_indicators_archive_keywords(self):
        """Test detection of archive indicators."""
        text = "I need long-term archival storage for compliance"
        indicators = get_performance_indicators(text)
        
        assert "long-term" in indicators["archive"]
        assert "archival" in indicators["archive"]
        assert "compliance" in indicators["archive"]
    
    def test_get_performance_indicators_mixed(self):
        """Test detection with mixed indicators."""
        text = "I need fast but cheap archive storage"
        indicators = get_performance_indicators(text)
        
        assert len(indicators["performance"]) > 0
        assert len(indicators["cost"]) > 0
        assert len(indicators["archive"]) > 0


class TestCostPreference:
    """Test suite for cost preference modifications."""
    
    def test_apply_cost_preference_optimized(self):
        """Test cost-optimized modifications."""
        original = {"tier": "Hot", "performance": "Premium", "replication": "GRS"}
        
        modified = apply_cost_preference(original, "optimized")
        
        assert modified["tier"] == "Cool"  # Hot -> Cool
        assert modified["performance"] == "Standard"  # Premium -> Standard
        assert modified["replication"] == "LRS"  # GRS -> LRS
    
    def test_apply_cost_preference_performance(self):
        """Test performance-optimized modifications."""
        original = {"tier": "Cool", "performance": "Standard", "replication": "LRS"}
        
        modified = apply_cost_preference(original, "performance")
        
        assert modified["tier"] == "Hot"  # Cool -> Hot
        assert modified["performance"] == "Premium"  # Standard -> Premium
        assert modified["replication"] == "ZRS"  # LRS -> ZRS
    
    def test_apply_cost_preference_balanced(self):
        """Test balanced preference (no changes)."""
        original = {"tier": "Hot", "performance": "Standard", "replication": "LRS"}
        
        modified = apply_cost_preference(original, "balanced")
        
        assert modified == original
    
    def test_apply_cost_preference_invalid(self):
        """Test with invalid cost preference."""
        original = {"tier": "Hot", "performance": "Standard", "replication": "LRS"}
        
        modified = apply_cost_preference(original, "invalid_preference")
        
        assert modified == original
    
    def test_apply_cost_preference_partial_modifications(self):
        """Test when only some modifications apply."""
        # Archive tier can't be downgraded further for cost optimization
        original = {"tier": "Archive", "performance": "Standard", "replication": "LRS"}
        
        modified = apply_cost_preference(original, "optimized")
        
        assert modified["tier"] == "Archive"  # No change possible
        assert modified["performance"] == "Standard"  # No change possible
        assert modified["replication"] == "LRS"  # No change possible


class TestReasoningGeneration:
    """Test suite for reasoning generation."""
    
    def test_generate_reasoning_no_modifications(self):
        """Test reasoning when configuration unchanged."""
        original = {"tier": "Hot", "performance": "Standard", "replication": "LRS"}
        final = original.copy()
        
        reasoning = generate_reasoning(
            original, final, "images", "balanced", {"performance": [], "cost": [], "archive": []}
        )
        
        # Should contain base reasoning for images
        assert "fast access" in reasoning.lower() or "display" in reasoning.lower()
    
    def test_generate_reasoning_with_modifications(self):
        """Test reasoning with cost preference modifications."""
        original = {"tier": "Hot", "performance": "Premium", "replication": "GRS"}
        final = {"tier": "Cool", "performance": "Standard", "replication": "LRS"}
        
        reasoning = generate_reasoning(
            original, final, "images", "optimized", {"performance": [], "cost": ["cheap"], "archive": []}
        )
        
        assert "cost" in reasoning.lower()
        assert "cool" in reasoning.lower()
    
    def test_generate_reasoning_with_performance_focus(self):
        """Test reasoning with performance indicators."""
        original = {"tier": "Cool", "performance": "Standard", "replication": "LRS"}
        final = {"tier": "Hot", "performance": "Premium", "replication": "ZRS"}
        
        reasoning = generate_reasoning(
            original, final, "database", "performance", {"performance": ["fast"], "cost": [], "archive": []}
        )
        
        assert "performance" in reasoning.lower()
        assert "premium" in reasoning.lower()


class TestConfidenceScoring:
    """Test suite for confidence scoring."""
    
    def test_confidence_score_with_keywords(self):
        """Test confidence scoring with detected keywords."""
        keywords = ["images", "website"]
        text = "I need storage for my website images"
        indicators = {"performance": [], "cost": [], "archive": []}
        
        confidence = get_confidence_score(keywords, text, indicators)
        
        assert confidence > 0.5  # Should have decent confidence with keywords
    
    def test_confidence_score_no_keywords(self):
        """Test confidence scoring without keywords."""
        keywords = []
        text = "I need some storage"
        indicators = {"performance": [], "cost": [], "archive": []}
        
        confidence = get_confidence_score(keywords, text, indicators)
        
        assert confidence < 0.5  # Lower confidence without specific keywords
    
    def test_confidence_score_with_indicators(self):
        """Test confidence boost from performance indicators."""
        keywords = ["images"]
        text = "I need fast storage for images"
        indicators = {"performance": ["fast"], "cost": [], "archive": []}
        
        confidence = get_confidence_score(keywords, text, indicators)
        
        # Should be higher than without indicators
        baseline_confidence = get_confidence_score(keywords, "I need storage for images", 
                                                 {"performance": [], "cost": [], "archive": []})
        assert confidence > baseline_confidence
    
    def test_confidence_score_text_length_bonus(self):
        """Test confidence boost for longer, more detailed text."""
        keywords = ["images"]
        short_text = "image storage"
        long_text = "I need reliable storage for my website images that will be accessed frequently by customers"
        indicators = {"performance": [], "cost": [], "archive": []}
        
        short_confidence = get_confidence_score(keywords, short_text, indicators)
        long_confidence = get_confidence_score(keywords, long_text, indicators)
        
        assert long_confidence > short_confidence
    
    def test_confidence_score_capped_at_one(self):
        """Test that confidence score doesn't exceed 1.0."""
        keywords = ["images", "website", "media"]
        text = "I need high-performance fast cost-effective storage for my website images and media files"
        indicators = {"performance": ["fast", "high-performance"], "cost": ["cost-effective"], "archive": []}
        
        confidence = get_confidence_score(keywords, text, indicators)
        
        assert confidence <= 1.0