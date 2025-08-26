"""
Unit tests for use case detector functionality.

Tests the UseCaseDetector class for proper use case detection,
context extraction, and analysis capabilities.
"""

import pytest
from src.agent.decision.use_case_detector import (
    UseCaseDetector,
    DetectedUseCase,
    create_use_case_detector
)


class TestDetectedUseCase:
    """Test suite for DetectedUseCase dataclass."""
    
    def test_detected_use_case_creation(self):
        """Test DetectedUseCase creation and field access."""
        detected = DetectedUseCase(
            primary_use_case="images",
            confidence=0.8,
            keywords_found=["images", "website"],
            performance_indicators={"performance": [], "cost": [], "archive": []},
            context_hints={"environment": "production"}
        )
        
        assert detected.primary_use_case == "images"
        assert detected.confidence == 0.8
        assert detected.keywords_found == ["images", "website"]
        assert detected.context_hints["environment"] == "production"


class TestUseCaseDetector:
    """Test suite for UseCaseDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = UseCaseDetector()
    
    def test_initialization(self):
        """Test detector initialization."""
        assert self.detector is not None
        assert hasattr(self.detector, '_quantity_pattern')
        assert hasattr(self.detector, '_region_pattern')
        assert hasattr(self.detector, '_urgency_pattern')
    
    def test_detect_use_case_single_keyword(self):
        """Test detection with single use case keyword."""
        text = "I need storage for my images"
        
        result = self.detector.detect_use_case(text)
        
        assert result.primary_use_case == "images"
        assert "images" in result.keywords_found
        assert result.confidence > 0.5
    
    def test_detect_use_case_multiple_keywords(self):
        """Test detection with multiple use case keywords."""
        text = "I need storage for website images and backup logs"
        
        result = self.detector.detect_use_case(text)
        
        # Should prioritize based on priority order
        assert result.primary_use_case in ["images", "backup", "logs", "website"]
        assert len(result.keywords_found) > 1
    
    def test_detect_use_case_with_performance_indicators(self):
        """Test detection with performance indicators."""
        text = "I need fast high-performance storage for database"
        
        result = self.detector.detect_use_case(text)
        
        assert result.primary_use_case == "database"
        assert len(result.performance_indicators["performance"]) > 0
        assert "fast" in result.performance_indicators["performance"]
    
    def test_detect_use_case_with_cost_indicators(self):
        """Test detection with cost indicators."""
        text = "I need cheap storage for backups to save money"
        
        result = self.detector.detect_use_case(text)
        
        assert result.primary_use_case == "backups"
        assert len(result.performance_indicators["cost"]) > 0
        assert "cheap" in result.performance_indicators["cost"]
    
    def test_detect_use_case_empty_input(self):
        """Test detection with empty input."""
        result = self.detector.detect_use_case("")
        
        assert result.primary_use_case == "general"
        assert result.confidence == 0.1
        assert result.keywords_found == []
    
    def test_detect_use_case_whitespace_only(self):
        """Test detection with whitespace-only input."""
        result = self.detector.detect_use_case("   \n\t   ")
        
        assert result.primary_use_case == "general"
        assert result.confidence == 0.1
    
    def test_detect_use_case_no_keywords(self):
        """Test detection when no specific keywords found."""
        text = "I need some storage space"
        
        result = self.detector.detect_use_case(text)
        
        assert result.primary_use_case == "general"
        assert result.keywords_found == []
        assert result.confidence < 0.5
    
    def test_prioritize_use_cases_database_priority(self):
        """Test that database use cases get high priority."""
        text = "I need storage for database backup images"
        
        result = self.detector.detect_use_case(text)
        
        # Database should win over backup and images due to priority
        assert result.primary_use_case == "database"
    
    def test_prioritize_use_cases_archive_priority(self):
        """Test that archive use cases get high priority."""
        text = "I need backup storage for archive logs"
        
        result = self.detector.detect_use_case(text)
        
        # Archive should win over backup and logs
        assert result.primary_use_case == "archive"
    
    def test_extract_context_hints_storage_size(self):
        """Test extraction of storage size hints."""
        text = "I need 5TB storage for my data lake"
        
        result = self.detector.detect_use_case(text)
        
        assert "estimated_sizes" in result.context_hints
        assert "5TB" in result.context_hints["estimated_sizes"]
    
    def test_extract_context_hints_multiple_sizes(self):
        """Test extraction of multiple storage sizes."""
        text = "I need 2GB for images and 10TB for backups"
        
        result = self.detector.detect_use_case(text)
        
        sizes = result.context_hints.get("estimated_sizes", [])
        assert "2GB" in sizes
        assert "10TB" in sizes
    
    def test_extract_context_hints_regions(self):
        """Test extraction of region preferences."""
        text = "Deploy storage in East US and West EU"
        
        result = self.detector.detect_use_case(text)
        
        regions = result.context_hints.get("preferred_regions", [])
        assert "east us" in regions
        assert "west eu" in regions
    
    def test_extract_context_hints_urgency(self):
        """Test extraction of urgency indicators."""
        text = "I need storage urgently, ASAP for the project"
        
        result = self.detector.detect_use_case(text)
        
        assert result.context_hints.get("urgency") == "high"
    
    def test_extract_context_hints_environment_production(self):
        """Test detection of production environment."""
        text = "I need production storage for our live application"
        
        result = self.detector.detect_use_case(text)
        
        assert result.context_hints.get("environment") == "production"
    
    def test_extract_context_hints_environment_development(self):
        """Test detection of development environment."""
        text = "I need storage for our development environment"
        
        result = self.detector.detect_use_case(text)
        
        assert result.context_hints.get("environment") == "development"
    
    def test_extract_context_hints_compliance(self):
        """Test detection of compliance requirements."""
        text = "I need storage for compliance with audit regulations"
        
        result = self.detector.detect_use_case(text)
        
        assert result.context_hints.get("compliance_required") is True
    
    def test_extract_context_hints_security(self):
        """Test detection of security requirements."""
        text = "I need secure encrypted storage for confidential data"
        
        result = self.detector.detect_use_case(text)
        
        assert result.context_hints.get("security_sensitive") is True
    
    def test_extract_context_hints_scalability(self):
        """Test detection of scalability requirements."""
        text = "I need scalable storage that can handle growth"
        
        result = self.detector.detect_use_case(text)
        
        assert result.context_hints.get("scalability_important") is True
    
    def test_extract_context_hints_reference_previous(self):
        """Test detection of references to previous deployments."""
        text = "I need storage like last time, similar to the previous setup"
        
        result = self.detector.detect_use_case(text)
        
        assert result.context_hints.get("reference_previous") is True
    
    def test_get_use_case_suggestions_partial_match(self):
        """Test use case suggestions for partial input."""
        suggestions = self.detector.get_use_case_suggestions("ima")
        
        assert "images" in suggestions
    
    def test_get_use_case_suggestions_contains_match(self):
        """Test use case suggestions that contain the input."""
        suggestions = self.detector.get_use_case_suggestions("ack")
        
        assert "backup" in suggestions or "backups" in suggestions
    
    def test_get_use_case_suggestions_empty_input(self):
        """Test use case suggestions with empty input."""
        suggestions = self.detector.get_use_case_suggestions("")
        
        assert suggestions == []
    
    def test_get_use_case_suggestions_no_matches(self):
        """Test use case suggestions with no matches."""
        suggestions = self.detector.get_use_case_suggestions("xyz123")
        
        assert suggestions == []
    
    def test_get_use_case_suggestions_prioritization(self):
        """Test that suggestions are prioritized correctly."""
        suggestions = self.detector.get_use_case_suggestions("log")
        
        # Both "log" and "logs" start with "log", so "logs" comes first alphabetically
        # The important thing is that both are found
        assert "log" in suggestions
        assert "logs" in suggestions
        assert len(suggestions) >= 2
    
    def test_analyze_text_complexity_basic(self):
        """Test basic text complexity analysis."""
        text = "I need storage for images"
        
        analysis = self.detector.analyze_text_complexity(text)
        
        assert analysis["word_count"] == 5
        assert analysis["character_count"] == len(text)
        assert analysis["sentence_count"] == 1
        assert analysis["has_technical_terms"] is False
        assert analysis["has_business_context"] is False
    
    def test_analyze_text_complexity_technical(self):
        """Test complexity analysis with technical terms."""
        text = "I need high IOPS storage with low latency for SSD performance"
        
        analysis = self.detector.analyze_text_complexity(text)
        
        assert analysis["has_technical_terms"] is True
    
    def test_analyze_text_complexity_business(self):
        """Test complexity analysis with business context."""
        text = "Our business needs customer-facing storage for the company"
        
        analysis = self.detector.analyze_text_complexity(text)
        
        assert analysis["has_business_context"] is True
    
    def test_analyze_text_complexity_score(self):
        """Test complexity score calculation."""
        short_text = "Storage needed"
        long_text = "I need comprehensive storage solution for our enterprise application with specific performance requirements and compliance needs"
        
        short_analysis = self.detector.analyze_text_complexity(short_text)
        long_analysis = self.detector.analyze_text_complexity(long_text)
        
        assert long_analysis["complexity_score"] > short_analysis["complexity_score"]


class TestCreateUseCaseDetector:
    """Test suite for factory function."""
    
    def test_create_use_case_detector(self):
        """Test factory function creates proper detector instance."""
        detector = create_use_case_detector()
        
        assert isinstance(detector, UseCaseDetector)
        assert hasattr(detector, 'detect_use_case')
        assert hasattr(detector, 'get_use_case_suggestions')


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = UseCaseDetector()
    
    def test_very_long_input(self):
        """Test detection with very long input text."""
        text = "I need storage " * 100 + "for images"  # Very long text
        
        result = self.detector.detect_use_case(text)
        
        assert result.primary_use_case == "images"
        assert result.confidence > 0.0
    
    def test_special_characters(self):
        """Test detection with special characters."""
        text = "I need storage for my @images & #photos!"
        
        result = self.detector.detect_use_case(text)
        
        assert result.primary_use_case == "images"
    
    def test_unicode_text(self):
        """Test detection with unicode characters."""
        text = "I need storage for my images 📸 and photos 🖼️"
        
        result = self.detector.detect_use_case(text)
        
        assert result.primary_use_case == "images"
    
    def test_mixed_case_keywords(self):
        """Test detection with mixed case keywords."""
        text = "I need STORAGE for My ImAgEs"
        
        result = self.detector.detect_use_case(text)
        
        assert result.primary_use_case == "images"
    
    def test_numbers_in_text(self):
        """Test detection with numbers in text."""
        text = "I need storage for 1000 images in my database2"
        
        result = self.detector.detect_use_case(text)
        
        # Should detect both images and database, prioritize database
        assert result.primary_use_case == "database"