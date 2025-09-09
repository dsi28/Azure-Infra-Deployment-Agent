"""
Tests for dual recommendation system components.

This module tests the LLM advisor, dual recommender, UI components, and
feedback tracking to ensure proper functionality of the side-by-side
recommendation system.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from src.agent.decision.llm_advisor import LLMStorageAdvisor, LLMRecommendation
from src.agent.decision.dual_recommender import DualRecommendationEngine, DualRecommendation
from src.agent.conversation.dual_recommendation_ui import DualRecommendationUI, UserChoice
from src.agent.learning.recommendation_feedback import RecommendationPreferenceTracker, RecommendationFeedback
from src.agent.decision.rules import StorageConfig
from src.agent.memory.user_profile import UserProfile


class TestLLMStorageAdvisor:
    """Test cases for LLM-based storage advisor."""
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client for testing."""
        mock_client = Mock()
        return mock_client
    
    @pytest.fixture
    def llm_advisor(self, mock_ollama_client):
        """LLM advisor instance for testing."""
        return LLMStorageAdvisor(mock_ollama_client)
    
    def test_initialization(self, llm_advisor):
        """Test LLM advisor initialization."""
        assert llm_advisor is not None
        assert llm_advisor.system_prompt is not None
        assert "Azure Storage expert" in llm_advisor.system_prompt
        assert "Hot" in llm_advisor.system_prompt
        assert "LRS" in llm_advisor.system_prompt
    
    def test_successful_recommendation(self, llm_advisor, mock_ollama_client):
        """Test successful LLM recommendation generation."""
        # Mock LLM response
        mock_response = '''
        Here's my recommendation:
        {
            "tier": "Hot",
            "performance": "Standard",
            "replication": "LRS",
            "reasoning": "Images need fast access for web display",
            "confidence": 0.8
        }
        '''
        mock_ollama_client.generate.return_value = mock_response
        
        # Test recommendation
        user_input = "I need storage for website images"
        recommendation = llm_advisor.get_recommendation(user_input)
        
        assert recommendation is not None
        assert recommendation.tier == "Hot"
        assert recommendation.performance == "Standard"
        assert recommendation.replication == "LRS"
        assert recommendation.confidence == 0.8
        assert "fast access" in recommendation.reasoning
    
    def test_invalid_json_response(self, llm_advisor, mock_ollama_client):
        """Test handling of invalid JSON response."""
        mock_ollama_client.generate.return_value = "Invalid response without JSON"
        
        user_input = "I need storage for backups"
        recommendation = llm_advisor.get_recommendation(user_input)
        
        assert recommendation is None
    
    def test_missing_required_fields(self, llm_advisor, mock_ollama_client):
        """Test handling of response missing required fields."""
        mock_response = '''
        {
            "tier": "Hot",
            "performance": "Standard"
        }
        '''
        mock_ollama_client.generate.return_value = mock_response
        
        user_input = "I need storage"
        recommendation = llm_advisor.get_recommendation(user_input)
        
        assert recommendation is None
    
    def test_invalid_enum_values(self, llm_advisor, mock_ollama_client):
        """Test handling of invalid enum values in response."""
        mock_response = '''
        {
            "tier": "SuperHot",
            "performance": "Standard",
            "replication": "LRS",
            "reasoning": "Test",
            "confidence": 0.8
        }
        '''
        mock_ollama_client.generate.return_value = mock_response
        
        user_input = "I need storage"
        recommendation = llm_advisor.get_recommendation(user_input)
        
        assert recommendation is None
    
    def test_context_aware_prompting(self, llm_advisor, mock_ollama_client):
        """Test that user profile and context are included in prompts."""
        mock_ollama_client.generate.return_value = '''
        {
            "tier": "Cool",
            "performance": "Standard",
            "replication": "GRS",
            "reasoning": "Cost-optimized backup storage",
            "confidence": 0.9
        }
        '''
        
        user_profile = UserProfile()
        user_profile.cost_preference = "optimized"
        user_profile.preferred_regions = ["eastus"]
        
        context = {
            "use_case_keywords": ["backups"],
            "performance_indicators": {"cost": ["cheap"]}
        }
        
        user_input = "I need cheap backup storage"
        recommendation = llm_advisor.get_recommendation(user_input, user_profile, context)
        
        # Verify the prompt included context
        call_args = mock_ollama_client.generate.call_args
        prompt = call_args[1]['prompt']
        
        assert "optimized" in prompt
        assert "eastus" in prompt
        assert "backups" in prompt
        assert recommendation is not None


class TestDualRecommendationEngine:
    """Test cases for dual recommendation engine."""
    
    @pytest.fixture
    def mock_llm_advisor(self):
        """Mock LLM advisor for testing."""
        return Mock()
    
    @pytest.fixture
    def mock_rules_advisor(self):
        """Mock rules advisor for testing."""
        return Mock()
    
    @pytest.fixture
    def dual_engine(self, mock_llm_advisor, mock_rules_advisor):
        """Dual recommendation engine for testing."""
        engine = DualRecommendationEngine()
        engine.llm_advisor = mock_llm_advisor
        engine.rules_advisor = mock_rules_advisor
        return engine
    
    def test_dual_recommendation_both_available(self, dual_engine, mock_llm_advisor, mock_rules_advisor):
        """Test dual recommendation when both systems available."""
        # Mock LLM recommendation
        llm_rec = LLMRecommendation(
            tier="Hot",
            performance="Premium",
            replication="ZRS", 
            reasoning="High-performance for traffic",
            confidence=0.8,
            raw_response=""
        )
        mock_llm_advisor.get_recommendation.return_value = llm_rec
        
        # Mock rules recommendation
        rules_rec = StorageConfig(
            tier="Hot",
            performance="Standard",
            replication="LRS",
            reasoning="Cost-effective for images"
        )
        mock_rules_advisor.get_storage_recommendation.return_value = rules_rec
        
        user_input = "I need storage for high-traffic images"
        dual_rec = dual_engine.get_dual_recommendation(user_input)
        
        assert dual_rec is not None
        assert dual_rec.llm_available is True
        assert dual_rec.llm_recommendation == llm_rec
        assert dual_rec.rules_recommendation == rules_rec
        assert dual_rec.user_input == user_input
    
    def test_dual_recommendation_llm_unavailable(self, dual_engine, mock_llm_advisor, mock_rules_advisor):
        """Test dual recommendation when LLM unavailable."""
        # Mock LLM failure
        mock_llm_advisor.get_recommendation.return_value = None
        
        # Mock rules recommendation
        rules_rec = StorageConfig(
            tier="Hot",
            performance="Standard",
            replication="LRS",
            reasoning="Default image storage"
        )
        mock_rules_advisor.get_storage_recommendation.return_value = rules_rec
        
        user_input = "I need storage for images"
        dual_rec = dual_engine.get_dual_recommendation(user_input)
        
        assert dual_rec is not None
        assert dual_rec.llm_available is False
        assert dual_rec.llm_recommendation is None
        assert dual_rec.rules_recommendation == rules_rec
    
    def test_agreement_score_calculation(self):
        """Test agreement score calculation between recommendations."""
        llm_rec = LLMRecommendation(
            tier="Hot",
            performance="Standard",
            replication="LRS",
            reasoning="Test",
            confidence=0.8,
            raw_response=""
        )
        
        rules_rec = StorageConfig(
            tier="Hot",
            performance="Standard", 
            replication="LRS",
            reasoning="Test"
        )
        
        dual_rec = DualRecommendation(
            llm_recommendation=llm_rec,
            rules_recommendation=rules_rec,
            llm_available=True,
            user_input="test",
            context={}
        )
        
        # All three match = 100% agreement
        assert dual_rec.get_agreement_score() == 1.0
    
    def test_partial_agreement_score(self):
        """Test partial agreement score calculation."""
        llm_rec = LLMRecommendation(
            tier="Hot",
            performance="Premium",  # Different
            replication="LRS",
            reasoning="Test",
            confidence=0.8,
            raw_response=""
        )
        
        rules_rec = StorageConfig(
            tier="Hot", 
            performance="Standard",  # Different
            replication="LRS",
            reasoning="Test"
        )
        
        dual_rec = DualRecommendation(
            llm_recommendation=llm_rec,
            rules_recommendation=rules_rec,
            llm_available=True,
            user_input="test",
            context={}
        )
        
        # 2 out of 3 match = 67% agreement
        assert abs(dual_rec.get_agreement_score() - 0.67) < 0.01
    
    def test_comparison_analysis(self, dual_engine):
        """Test recommendation comparison analysis."""
        llm_rec = LLMRecommendation(
            tier="Hot",
            performance="Premium",
            replication="ZRS",
            reasoning="High performance needed",
            confidence=0.9,
            raw_response=""
        )
        
        rules_rec = StorageConfig(
            tier="Hot",
            performance="Standard",
            replication="LRS", 
            reasoning="Cost-effective solution"
        )
        
        dual_rec = DualRecommendation(
            llm_recommendation=llm_rec,
            rules_recommendation=rules_rec,
            llm_available=True,
            user_input="test",
            context={'rules_confidence': 0.7}
        )
        
        analysis = dual_engine.compare_recommendations(dual_rec)
        
        assert analysis['llm_available'] is True
        assert len(analysis['differences']) == 2  # Performance and replication differ
        assert len(analysis['similarities']) == 1  # Tier matches
        assert analysis['agreement_score'] < 0.5  # Low agreement


class TestDualRecommendationUI:
    """Test cases for dual recommendation UI."""
    
    @pytest.fixture
    def ui(self):
        """Dual recommendation UI for testing."""
        return DualRecommendationUI()
    
    @pytest.fixture
    def sample_dual_recommendation(self):
        """Sample dual recommendation for testing."""
        llm_rec = LLMRecommendation(
            tier="Hot",
            performance="Premium",
            replication="ZRS",
            reasoning="AI analysis suggests high performance",
            confidence=0.85,
            raw_response=""
        )
        
        rules_rec = StorageConfig(
            tier="Hot",
            performance="Standard",
            replication="LRS",
            reasoning="Rule-based cost optimization"
        )
        
        return DualRecommendation(
            llm_recommendation=llm_rec,
            rules_recommendation=rules_rec,
            llm_available=True,
            user_input="I need storage for my application",
            context={}
        )
    
    @patch('builtins.input')
    def test_user_choice_llm(self, mock_input, ui, sample_dual_recommendation):
        """Test user choosing LLM recommendation."""
        mock_input.return_value = '1'
        
        choice, config = ui.get_user_choice(sample_dual_recommendation)
        
        assert choice == UserChoice.LLM
        assert config is None
    
    @patch('builtins.input')
    def test_user_choice_rules(self, mock_input, ui, sample_dual_recommendation):
        """Test user choosing rules recommendation."""
        mock_input.return_value = '2'
        
        choice, config = ui.get_user_choice(sample_dual_recommendation)
        
        assert choice == UserChoice.RULES
        assert config is None
    
    @patch('builtins.input')
    def test_user_choice_custom(self, mock_input, ui, sample_dual_recommendation):
        """Test user choosing custom configuration."""
        # Mock custom configuration inputs
        mock_input.side_effect = ['3', '1', '2', '3']  # Custom, Hot, Premium, ZRS
        
        choice, config = ui.get_user_choice(sample_dual_recommendation)
        
        assert choice == UserChoice.CUSTOM
        assert config is not None
        assert config['tier'] == 'Hot'
        assert config['performance'] == 'Premium'
        assert config['replication'] == 'ZRS'
    
    @patch('builtins.input')
    def test_invalid_choice_retry(self, mock_input, ui, sample_dual_recommendation):
        """Test handling of invalid user choice with retry."""
        mock_input.side_effect = ['invalid', '5', '1']  # Invalid, out of range, valid
        
        choice, config = ui.get_user_choice(sample_dual_recommendation)
        
        assert choice == UserChoice.LLM
        assert mock_input.call_count == 3  # Should retry invalid inputs
    
    def test_llm_unavailable_ui(self, ui):
        """Test UI when LLM is unavailable."""
        rules_rec = StorageConfig(
            tier="Hot",
            performance="Standard",
            replication="LRS",
            reasoning="Rules-only recommendation"
        )
        
        dual_rec = DualRecommendation(
            llm_recommendation=None,
            rules_recommendation=rules_rec,
            llm_available=False,
            user_input="test",
            context={}
        )
        
        # Test that presentation handles LLM unavailable case
        # This would normally test print output, but we'll just verify no exceptions
        ui.present_dual_recommendations(dual_rec)
        
        # Should not raise any exceptions
        assert True


class TestRecommendationFeedback:
    """Test cases for recommendation feedback tracking."""
    
    @pytest.fixture
    def temp_feedback_file(self):
        """Temporary feedback file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        yield temp_file
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.fixture
    def tracker(self, temp_feedback_file):
        """Feedback tracker for testing."""
        return RecommendationPreferenceTracker(temp_feedback_file)
    
    @pytest.fixture
    def sample_dual_recommendation(self):
        """Sample dual recommendation for testing."""
        llm_rec = LLMRecommendation(
            tier="Hot",
            performance="Premium",
            replication="ZRS",
            reasoning="AI recommendation",
            confidence=0.8,
            raw_response=""
        )
        
        rules_rec = StorageConfig(
            tier="Hot",
            performance="Standard",
            replication="LRS",
            reasoning="Rules recommendation"
        )
        
        return DualRecommendation(
            llm_recommendation=llm_rec,
            rules_recommendation=rules_rec,
            llm_available=True,
            user_input="I need storage for images",
            context={
                'use_case_keywords': ['images'],
                'primary_use_case': 'images'
            }
        )
    
    def test_record_feedback(self, tracker, sample_dual_recommendation):
        """Test recording user feedback."""
        final_config = {
            'tier': 'Hot',
            'performance': 'Premium',
            'replication': 'ZRS',
            'reasoning': 'User chose LLM recommendation'
        }
        
        initial_count = len(tracker.feedback_history)
        
        tracker.record_feedback(
            sample_dual_recommendation,
            UserChoice.LLM,
            final_config
        )
        
        assert len(tracker.feedback_history) == initial_count + 1
        
        feedback = tracker.feedback_history[-1]
        assert feedback.user_choice == 'llm'
        assert feedback.final_tier == 'Hot'
        assert feedback.final_performance == 'Premium'
        assert feedback.primary_use_case == 'images'
    
    def test_preference_statistics(self, tracker, sample_dual_recommendation):
        """Test preference statistics calculation."""
        # Record multiple feedback entries
        configs = [
            {'tier': 'Hot', 'performance': 'Premium', 'replication': 'ZRS', 'reasoning': 'LLM'},
            {'tier': 'Hot', 'performance': 'Standard', 'replication': 'LRS', 'reasoning': 'Rules'},
            {'tier': 'Cool', 'performance': 'Standard', 'replication': 'GRS', 'reasoning': 'Custom'}
        ]
        
        choices = [UserChoice.LLM, UserChoice.RULES, UserChoice.CUSTOM]
        
        for choice, config in zip(choices, configs):
            tracker.record_feedback(sample_dual_recommendation, choice, config)
        
        stats = tracker.get_preference_statistics()
        
        assert stats['total_choices'] == 3
        assert stats['llm_choices'] == 1
        assert stats['rules_choices'] == 1
        assert stats['custom_choices'] == 1
        assert abs(stats['llm_preference_rate'] - 0.5) < 0.01  # 1 out of 2 when LLM available
    
    def test_use_case_preferences(self, tracker):
        """Test use case preference tracking."""
        # Create different dual recommendations for different use cases
        use_cases = ['images', 'backups', 'images']
        choices = [UserChoice.LLM, UserChoice.RULES, UserChoice.RULES]
        
        for use_case, choice in zip(use_cases, choices):
            dual_rec = DualRecommendation(
                llm_recommendation=Mock(),
                rules_recommendation=Mock(),
                llm_available=True,
                user_input=f"I need {use_case} storage",
                context={'primary_use_case': use_case}
            )
            
            tracker.record_feedback(dual_rec, choice, {'tier': 'Hot'})
        
        use_case_prefs = tracker.get_use_case_preferences()
        
        assert 'images' in use_case_prefs
        assert 'backups' in use_case_prefs
        assert use_case_prefs['images']['llm'] == 1
        assert use_case_prefs['images']['rules'] == 1
        assert use_case_prefs['backups']['rules'] == 1
    
    def test_should_prefer_llm(self, tracker, sample_dual_recommendation):
        """Test LLM preference recommendation logic."""
        # Record multiple LLM choices to establish preference
        for _ in range(4):
            tracker.record_feedback(
                sample_dual_recommendation,
                UserChoice.LLM,
                {'tier': 'Hot'}
            )
        
        # Record one rules choice
        tracker.record_feedback(
            sample_dual_recommendation,
            UserChoice.RULES,
            {'tier': 'Hot'}
        )
        
        # Should prefer LLM with 80% choice rate
        assert tracker.should_prefer_llm() is True
        assert tracker.should_prefer_llm('images') is True
    
    def test_recommendation_accuracy(self, tracker):
        """Test recommendation accuracy calculation."""
        # Perfect LLM recommendation
        llm_rec = LLMRecommendation(
            tier="Hot", performance="Standard", replication="LRS",
            reasoning="Test", confidence=0.8, raw_response=""
        )
        
        dual_rec = DualRecommendation(
            llm_recommendation=llm_rec,
            rules_recommendation=Mock(),
            llm_available=True,
            user_input="test",
            context={}
        )
        
        # User chooses LLM recommendation exactly
        tracker.record_feedback(
            dual_rec,
            UserChoice.LLM,
            {'tier': 'Hot', 'performance': 'Standard', 'replication': 'LRS'}
        )
        
        accuracy = tracker.get_recommendation_accuracy()
        assert accuracy['llm_accuracy'] == 1.0
    
    def test_persistence(self, tracker, sample_dual_recommendation, temp_feedback_file):
        """Test feedback persistence to file."""
        tracker.record_feedback(
            sample_dual_recommendation,
            UserChoice.LLM,
            {'tier': 'Hot'}
        )
        
        # Create new tracker with same file
        new_tracker = RecommendationPreferenceTracker(temp_feedback_file)
        
        assert len(new_tracker.feedback_history) == 1
        assert new_tracker.feedback_history[0].user_choice == 'llm'


class TestEndToEndDualRecommendation:
    """End-to-end integration tests for dual recommendation system."""
    
    @patch('src.agent.decision.llm_advisor.OllamaClient')
    def test_complete_dual_recommendation_flow(self, mock_ollama_class):
        """Test complete dual recommendation flow."""
        # Mock Ollama client
        mock_client = Mock()
        mock_ollama_class.return_value = mock_client
        
        # Mock LLM response
        mock_client.generate.return_value = '''
        {
            "tier": "Cool",
            "performance": "Standard", 
            "replication": "GRS",
            "reasoning": "Backup storage needs geo-redundancy",
            "confidence": 0.9
        }
        '''
        
        # Create engine
        engine = DualRecommendationEngine()
        
        # Get dual recommendation
        user_input = "I need storage for database backups"
        dual_rec = engine.get_dual_recommendation(user_input)
        
        # Verify both recommendations generated
        assert dual_rec is not None
        assert dual_rec.llm_available is True
        assert dual_rec.llm_recommendation is not None
        assert dual_rec.rules_recommendation is not None
        
        # Verify LLM recommendation
        assert dual_rec.llm_recommendation.tier == "Cool"
        assert dual_rec.llm_recommendation.replication == "GRS"
        
        # Verify rules recommendation (should also suggest backups -> Cool + GRS)
        assert dual_rec.rules_recommendation.tier == "Cool"
        assert dual_rec.rules_recommendation.replication == "GRS"
        
        # Should have high agreement for backup use case
        assert dual_rec.get_agreement_score() > 0.8
    
    def test_fallback_when_llm_fails(self):
        """Test system fallback when LLM completely fails."""
        # Create engine with failing LLM
        engine = DualRecommendationEngine()
        engine.llm_advisor.ollama_client = Mock()
        engine.llm_advisor.ollama_client.generate.side_effect = Exception("LLM failed")
        
        user_input = "I need storage for images"
        dual_rec = engine.get_dual_recommendation(user_input)
        
        # Should still work with rules only
        assert dual_rec is not None
        assert dual_rec.llm_available is False
        assert dual_rec.llm_recommendation is None
        assert dual_rec.rules_recommendation is not None
        assert dual_rec.rules_recommendation.tier == "Hot"  # Images should be Hot


if __name__ == "__main__":
    pytest.main([__file__])