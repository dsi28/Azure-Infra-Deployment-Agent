"""
Tests for simple feedback learning system.

Tests the feedback learning capabilities to ensure the agent
learns from user interactions and improves recommendations.
"""

import pytest
import os
import tempfile
import shutil
from src.agent.learning.simple_feedback import (
    SimpleFeedbackLearner,
    FeedbackType, 
    FeedbackEntry,
    LearningPattern,
    create_feedback_learner
)


class TestSimpleFeedbackLearner:
    """Test simple feedback learning system."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.learner = SimpleFeedbackLearner(self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_record_positive_feedback(self):
        """Test recording positive feedback."""
        original_rec = {
            "detected_use_case": "images",
            "configuration": {
                "tier": "Hot",
                "performance": "Standard",
                "replication": "LRS"
            }
        }
        
        self.learner.record_feedback(
            feedback_type=FeedbackType.POSITIVE,
            original_recommendation=original_rec,
            user_input="I need storage for images",
            user_response="yes",
            confidence_before=0.8
        )
        
        # Verify feedback recorded
        assert len(self.learner.feedback_history) == 1
        feedback = self.learner.feedback_history[0]
        assert feedback.feedback_type == FeedbackType.POSITIVE
        assert feedback.satisfaction_score == 1.0
        assert feedback.confidence_before == 0.8
        
        # Verify learning pattern created
        assert "images" in self.learner.learned_patterns
        pattern = self.learner.learned_patterns["images"]
        assert pattern.use_case == "images"
        assert pattern.sample_count == 1
        assert pattern.success_rate > 0.5  # Should improve
    
    def test_record_negative_feedback(self):
        """Test recording negative feedback."""
        original_rec = {
            "detected_use_case": "backups",
            "configuration": {
                "tier": "Archive", 
                "performance": "Standard",
                "replication": "LRS"
            }
        }
        
        self.learner.record_feedback(
            feedback_type=FeedbackType.NEGATIVE,
            original_recommendation=original_rec,
            user_input="I need backup storage",
            user_response="no, that's too slow",
            confidence_before=0.7
        )
        
        feedback = self.learner.feedback_history[0]
        assert feedback.feedback_type == FeedbackType.NEGATIVE
        assert feedback.satisfaction_score == 0.1
        
        # Pattern should reflect poor performance
        pattern = self.learner.learned_patterns["backups"]
        assert pattern.success_rate < 0.5
    
    def test_record_modification_feedback(self):
        """Test recording modification feedback."""
        original_rec = {
            "detected_use_case": "website",
            "configuration": {
                "tier": "Hot",
                "performance": "Standard", 
                "replication": "LRS"
            }
        }
        
        final_config = {
            "tier": "Hot",
            "performance": "Premium",  # User upgraded performance
            "replication": "ZRS"       # User upgraded replication
        }
        
        self.learner.record_feedback(
            feedback_type=FeedbackType.MODIFICATION,
            original_recommendation=original_rec,
            user_input="I need website storage",
            user_response="make it faster",
            final_configuration=final_config,
            modification_requested="make it faster",
            confidence_before=0.75
        )
        
        feedback = self.learner.feedback_history[0]
        assert feedback.feedback_type == FeedbackType.MODIFICATION
        assert feedback.modification_requested == "make it faster"
        assert feedback.satisfaction_score == 0.6  # Partial satisfaction
        
        # Pattern should learn from final configuration
        pattern = self.learner.learned_patterns["website"]
        assert pattern.preferred_config.get("performance") == "Premium"
        assert pattern.preferred_config.get("replication") == "ZRS"
    
    def test_get_preference_adjustments(self):
        """Test getting preference adjustments from learned patterns."""
        # Create some learning history
        self._create_learning_history_for_images()
        
        # Get adjustments for images use case
        adjustments = self.learner.get_preference_adjustments("images")
        
        # Should return preferences based on learned patterns
        assert "preferred_access_tier" in adjustments
        assert adjustments["preferred_access_tier"] == "Hot"
        assert adjustments["preferred_performance"] == "Standard"
        assert adjustments["preferred_replication"] == "LRS"
    
    def test_get_preference_adjustments_insufficient_data(self):
        """Test preference adjustments with insufficient learning data."""
        # No learning history
        adjustments = self.learner.get_preference_adjustments("unknown")
        
        # Should return empty adjustments
        assert adjustments == {}
    
    def test_confidence_adjustment(self):
        """Test confidence adjustment based on learning."""
        self._create_learning_history_for_images()
        
        # Test confidence adjustment for images (should be positive)
        base_confidence = 0.8
        adjusted = self.learner.get_confidence_adjustment("images", base_confidence)
        
        # Should increase confidence due to good success rate
        assert adjusted >= base_confidence
        assert adjusted <= 0.95  # Clamped to max
        
        # Test for use case with no history
        adjusted_unknown = self.learner.get_confidence_adjustment("unknown", base_confidence)
        assert adjusted_unknown == base_confidence  # No change
    
    def test_learning_insights(self):
        """Test getting learning insights and statistics."""
        # Create varied learning history
        self._create_varied_learning_history()
        
        insights = self.learner.get_learning_insights()
        
        # Verify insights structure
        assert "total_feedback" in insights
        assert "feedback_breakdown" in insights
        assert "average_satisfaction" in insights
        assert "common_modifications" in insights
        assert "learned_patterns" in insights
        assert "learning_quality" in insights
        
        assert insights["total_feedback"] > 0
        assert isinstance(insights["average_satisfaction"], float)
        assert 0.0 <= insights["average_satisfaction"] <= 1.0
    
    def test_persistence_feedback_history(self):
        """Test persistence of feedback history."""
        # Record some feedback
        original_rec = {"detected_use_case": "logs", "configuration": {"tier": "Cool"}}
        self.learner.record_feedback(
            FeedbackType.POSITIVE, original_rec, "test", "yes"
        )
        
        # Create new learner instance (should load from file)
        new_learner = SimpleFeedbackLearner(self.temp_dir)
        
        # Should have loaded the feedback
        assert len(new_learner.feedback_history) == 1
        assert new_learner.feedback_history[0].feedback_type == FeedbackType.POSITIVE
        assert new_learner.feedback_history[0].user_input == "test"
    
    def test_persistence_learned_patterns(self):
        """Test persistence of learned patterns."""
        self._create_learning_history_for_images()
        
        # Create new learner (should load patterns)
        new_learner = SimpleFeedbackLearner(self.temp_dir)
        
        # Should have loaded patterns
        assert "images" in new_learner.learned_patterns
        pattern = new_learner.learned_patterns["images"]
        assert pattern.use_case == "images"
        assert pattern.sample_count > 0
    
    def test_learning_quality_assessment(self):
        """Test learning quality assessment."""
        # Test with insufficient data
        insights = self.learner.get_learning_insights()
        assert "Insufficient data" in insights["learning_quality"]
        
        # Add positive feedback
        for i in range(10):
            self.learner.record_feedback(
                FeedbackType.POSITIVE,
                {"detected_use_case": f"test{i}", "configuration": {}},
                f"test input {i}",
                "yes"
            )
        
        insights = self.learner.get_learning_insights()
        assert "Excellent" in insights["learning_quality"] or "Good" in insights["learning_quality"]
    
    def test_satisfaction_score_calculation(self):
        """Test satisfaction score calculation for different feedback types."""
        test_cases = [
            (FeedbackType.POSITIVE, None, 1.0),
            (FeedbackType.NEGATIVE, None, 0.1),
            (FeedbackType.MODIFICATION, "make it cheaper", 0.6),
            (FeedbackType.MODIFICATION, "completely different", 0.4),
            (FeedbackType.MODIFICATION, "something else", 0.6),  # Default for modifications
            (FeedbackType.NEUTRAL, None, 0.5)
        ]
        
        for feedback_type, modification, expected_score in test_cases:
            # Use private method directly for testing
            score = self.learner._calculate_satisfaction_score(feedback_type, modification)
            assert score == expected_score
    
    def test_multiple_learning_iterations(self):
        """Test learning improvement over multiple iterations."""
        use_case = "databases"
        
        # Start with mediocre recommendation
        initial_rec = {
            "detected_use_case": use_case,
            "configuration": {"tier": "Cool", "performance": "Standard", "replication": "LRS"}
        }
        
        # User requests modifications (learning opportunity)
        self.learner.record_feedback(
            FeedbackType.MODIFICATION,
            initial_rec,
            "I need database storage",
            "make it faster", 
            final_configuration={"tier": "Hot", "performance": "Premium", "replication": "ZRS"},
            modification_requested="make it faster"
        )
        
        # Second interaction - recommend improved config
        improved_rec = {
            "detected_use_case": use_case,
            "configuration": {"tier": "Hot", "performance": "Premium", "replication": "ZRS"}
        }
        
        # User accepts (positive feedback)
        self.learner.record_feedback(
            FeedbackType.POSITIVE,
            improved_rec,
            "I need database storage again",
            "yes"
        )
        
        # Check learning
        pattern = self.learner.learned_patterns[use_case]
        assert pattern.sample_count == 2
        assert pattern.success_rate > 0.5  # Should improve over time
        assert pattern.preferred_config["performance"] == "Premium"
    
    def _create_learning_history_for_images(self):
        """Helper to create consistent learning history for images."""
        for i in range(5):
            self.learner.record_feedback(
                FeedbackType.POSITIVE,
                {
                    "detected_use_case": "images",
                    "configuration": {
                        "tier": "Hot",
                        "performance": "Standard", 
                        "replication": "LRS"
                    }
                },
                f"I need image storage {i}",
                "yes",
                confidence_before=0.8
            )
    
    def _create_varied_learning_history(self):
        """Helper to create varied learning history for testing."""
        feedback_scenarios = [
            (FeedbackType.POSITIVE, "images", "Hot", "yes"),
            (FeedbackType.NEGATIVE, "backups", "Archive", "too slow"),
            (FeedbackType.MODIFICATION, "website", "Cool", "make it faster"),
            (FeedbackType.POSITIVE, "logs", "Cool", "perfect"),
            (FeedbackType.MODIFICATION, "databases", "Standard", "make it cheaper")
        ]
        
        for feedback_type, use_case, tier, response in feedback_scenarios:
            self.learner.record_feedback(
                feedback_type,
                {
                    "detected_use_case": use_case,
                    "configuration": {"tier": tier, "performance": "Standard", "replication": "LRS"}
                },
                f"I need {use_case} storage",
                response
            )


class TestFeedbackLearnerIntegration:
    """Integration tests for feedback learner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_feedback_learner_factory(self):
        """Test factory function."""
        learner = create_feedback_learner(self.temp_dir)
        
        assert isinstance(learner, SimpleFeedbackLearner)
        assert learner.data_dir == self.temp_dir
    
    def test_end_to_end_learning_cycle(self):
        """Test complete learning cycle from feedback to improved recommendations."""
        learner = create_feedback_learner(self.temp_dir)
        
        # 1. Initial recommendation (no prior learning)
        adjustments = learner.get_preference_adjustments("analytics")
        assert adjustments == {}  # No learning yet
        
        # 2. User provides feedback on initial recommendation
        learner.record_feedback(
            FeedbackType.MODIFICATION,
            {
                "detected_use_case": "analytics",
                "configuration": {"tier": "Cool", "performance": "Standard", "replication": "LRS"}
            },
            "I need analytics storage",
            "make it faster for real-time analytics",
            final_configuration={"tier": "Hot", "performance": "Premium", "replication": "ZRS"},
            modification_requested="make it faster"
        )
        
        # 3. Get adjustments after learning
        adjustments = learner.get_preference_adjustments("analytics")
        # Should still be empty due to low confidence with single sample
        
        # 4. Add more positive feedback to build confidence
        for i in range(4):
            learner.record_feedback(
                FeedbackType.POSITIVE,
                {
                    "detected_use_case": "analytics",
                    "configuration": {"tier": "Hot", "performance": "Premium", "replication": "ZRS"}
                },
                f"I need analytics storage {i}",
                "yes"
            )
        
        # 5. Now should have learned preferences
        adjustments = learner.get_preference_adjustments("analytics")
        assert adjustments.get("preferred_access_tier") == "Hot"
        assert adjustments.get("preferred_performance") == "Premium"
        
        # 6. Confidence should be adjusted based on success
        confidence_adj = learner.get_confidence_adjustment("analytics", 0.8)
        assert confidence_adj >= 0.8  # Should maintain or increase confidence
        
        # 7. Learning insights should show progress
        insights = learner.get_learning_insights()
        assert insights["total_feedback"] == 5
        assert "analytics" in insights["learned_patterns"]
        assert insights["learned_patterns"]["analytics"]["sample_count"] == 5