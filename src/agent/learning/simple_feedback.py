"""
Simple feedback learning system for Azure Storage Agent.

Implements basic learning from user feedback to improve future recommendations
without requiring complex machine learning. Uses JSON-based storage to track
user preferences and satisfaction patterns.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class FeedbackType(Enum):
    """Types of feedback the agent can receive."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MODIFICATION = "modification"
    NEUTRAL = "neutral"


@dataclass
class FeedbackEntry:
    """
    Single feedback entry for learning.
    
    Captures user feedback on storage recommendations to improve future suggestions.
    """
    timestamp: str
    feedback_type: FeedbackType
    original_recommendation: Dict[str, Any]
    user_input: str
    user_response: str
    final_configuration: Optional[Dict[str, Any]] = None
    modification_requested: Optional[str] = None
    confidence_before: float = 0.0
    satisfaction_score: float = 0.5  # 0.0 to 1.0


@dataclass
class LearningPattern:
    """
    Learned pattern from user interactions.
    
    Represents insights gained from user feedback to improve future recommendations.
    """
    use_case: str
    preferred_config: Dict[str, Any]
    confidence: float
    sample_count: int
    last_updated: str
    success_rate: float


class SimpleFeedbackLearner:
    """
    Simple feedback learning system for storage recommendations.
    
    Learns from user interactions to improve future storage configuration suggestions
    without requiring complex machine learning algorithms.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize feedback learning system.
        
        Args:
            data_dir (str): Directory for storing learning data.
        """
        self.data_dir = data_dir
        self.feedback_file = os.path.join(data_dir, "feedback_learning.json")
        self.patterns_file = os.path.join(data_dir, "learned_patterns.json")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing data
        self.feedback_history = self._load_feedback_history()
        self.learned_patterns = self._load_learned_patterns()
    
    def record_feedback(
        self, 
        feedback_type: FeedbackType,
        original_recommendation: Dict[str, Any],
        user_input: str,
        user_response: str,
        final_configuration: Optional[Dict[str, Any]] = None,
        modification_requested: Optional[str] = None,
        confidence_before: float = 0.0
    ) -> None:
        """
        Record user feedback for learning.
        
        Args:
            feedback_type (FeedbackType): Type of feedback received.
            original_recommendation (Dict[str, Any]): Original recommendation made.
            user_input (str): User's original request.
            user_response (str): User's response to recommendation.
            final_configuration (Optional[Dict[str, Any]]): Final config if different.
            modification_requested (Optional[str]): What modification was requested.
            confidence_before (float): Original recommendation confidence.
        """
        # Calculate satisfaction score based on feedback type
        satisfaction_score = self._calculate_satisfaction_score(
            feedback_type, modification_requested
        )
        
        feedback_entry = FeedbackEntry(
            timestamp=datetime.now().isoformat(),
            feedback_type=feedback_type,
            original_recommendation=original_recommendation,
            user_input=user_input,
            user_response=user_response,
            final_configuration=final_configuration,
            modification_requested=modification_requested,
            confidence_before=confidence_before,
            satisfaction_score=satisfaction_score
        )
        
        self.feedback_history.append(feedback_entry)
        self._save_feedback_history()
        
        # Update learned patterns
        self._update_patterns(feedback_entry)
    
    def get_preference_adjustments(self, use_case: str) -> Dict[str, Any]:
        """
        Get preference adjustments based on learned patterns.
        
        Args:
            use_case (str): Storage use case to get adjustments for.
            
        Returns:
            Dict[str, Any]: Preference adjustments to apply.
        """
        pattern = self.learned_patterns.get(use_case)
        if not pattern or pattern.confidence < 0.4 or pattern.sample_count < 3:
            return {}
        
        # Return preference adjustments based on learned patterns
        adjustments = {}
        
        # Extract preferences from successful configurations
        if pattern.success_rate > 0.7:
            preferred_config = pattern.preferred_config
            
            if "tier" in preferred_config:
                adjustments["preferred_access_tier"] = preferred_config["tier"]
            
            if "performance" in preferred_config:
                adjustments["preferred_performance"] = preferred_config["performance"]
                
            if "replication" in preferred_config:
                adjustments["preferred_replication"] = preferred_config["replication"]
        
        return adjustments
    
    def get_confidence_adjustment(
        self, 
        use_case: str, 
        base_confidence: float
    ) -> float:
        """
        Adjust confidence based on learning history.
        
        Args:
            use_case (str): Storage use case.
            base_confidence (float): Original confidence score.
            
        Returns:
            float: Adjusted confidence score.
        """
        pattern = self.learned_patterns.get(use_case)
        if not pattern or pattern.sample_count < 3:
            return base_confidence
        
        # Adjust confidence based on success rate
        success_multiplier = 0.8 + (pattern.success_rate * 0.4)  # 0.8 to 1.2 range
        adjusted_confidence = base_confidence * success_multiplier
        
        # Clamp to valid range
        return max(0.1, min(0.95, adjusted_confidence))
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """
        Get insights from learning history.
        
        Returns:
            Dict[str, Any]: Learning insights and statistics.
        """
        if not self.feedback_history:
            return {
                "total_feedback": 0, 
                "insights": "No feedback data yet",
                "feedback_breakdown": {},
                "average_satisfaction": 0.5,
                "common_modifications": {},
                "learned_patterns": {},
                "learning_quality": "Insufficient data - need more interactions"
            }
        
        total_feedback = len(self.feedback_history)
        
        # Count feedback types
        feedback_counts = {}
        satisfaction_scores = []
        
        for feedback in self.feedback_history:
            feedback_type = feedback.feedback_type.value
            feedback_counts[feedback_type] = feedback_counts.get(feedback_type, 0) + 1
            satisfaction_scores.append(feedback.satisfaction_score)
        
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
        
        # Most common modifications
        modifications = [
            f.modification_requested for f in self.feedback_history 
            if f.modification_requested
        ]
        
        common_modifications = {}
        for mod in modifications:
            common_modifications[mod] = common_modifications.get(mod, 0) + 1
        
        # Learning patterns summary
        patterns_summary = {}
        for use_case, pattern in self.learned_patterns.items():
            patterns_summary[use_case] = {
                "confidence": pattern.confidence,
                "success_rate": pattern.success_rate,
                "sample_count": pattern.sample_count,
                "preferred_config": pattern.preferred_config
            }
        
        return {
            "total_feedback": total_feedback,
            "feedback_breakdown": feedback_counts,
            "average_satisfaction": avg_satisfaction,
            "common_modifications": common_modifications,
            "learned_patterns": patterns_summary,
            "learning_quality": self._assess_learning_quality()
        }
    
    def _calculate_satisfaction_score(
        self, 
        feedback_type: FeedbackType,
        modification_requested: Optional[str]
    ) -> float:
        """Calculate satisfaction score from feedback."""
        if feedback_type == FeedbackType.POSITIVE:
            return 1.0
        elif feedback_type == FeedbackType.NEGATIVE:
            return 0.1
        elif feedback_type == FeedbackType.MODIFICATION:
            # Minor modifications still indicate partial satisfaction
            if modification_requested and any(word in modification_requested.lower() 
                                            for word in ["cheaper", "faster"]):
                return 0.6
            elif modification_requested and any(word in modification_requested.lower()
                                              for word in ["different", "completely"]):
                return 0.4
            return 0.6  # Default for modifications
        else:  # NEUTRAL
            return 0.5
    
    def _update_patterns(self, feedback_entry: FeedbackEntry) -> None:
        """Update learned patterns based on feedback."""
        # Extract use case from original recommendation
        use_case = feedback_entry.original_recommendation.get("detected_use_case", "general")
        
        # Get or create pattern
        if use_case not in self.learned_patterns:
            self.learned_patterns[use_case] = LearningPattern(
                use_case=use_case,
                preferred_config={},
                confidence=0.5,
                sample_count=0,
                last_updated=datetime.now().isoformat(),
                success_rate=0.5
            )
        
        pattern = self.learned_patterns[use_case]
        pattern.sample_count += 1
        pattern.last_updated = datetime.now().isoformat()
        
        # Update success rate based on satisfaction
        old_success_rate = pattern.success_rate
        satisfaction = feedback_entry.satisfaction_score
        
        # Exponential moving average for success rate
        alpha = 0.3  # Learning rate
        pattern.success_rate = (alpha * satisfaction) + ((1 - alpha) * old_success_rate)
        
        # Update preferred configuration if this was successful or a modification
        final_config = (feedback_entry.final_configuration or 
                      feedback_entry.original_recommendation.get("configuration", {}))
        
        if isinstance(final_config, dict) and (satisfaction > 0.5 or 
                                              feedback_entry.feedback_type == FeedbackType.MODIFICATION):
            # Update preferred config with successful or modified settings
            for key in ["tier", "performance", "replication"]:
                if key in final_config:
                    pattern.preferred_config[key] = final_config[key]
        
        # Update pattern confidence
        pattern.confidence = min(0.9, pattern.success_rate * (pattern.sample_count / 10))
        
        self._save_learned_patterns()
    
    def _assess_learning_quality(self) -> str:
        """Assess the quality of learning so far."""
        if len(self.feedback_history) < 5:
            return "Insufficient data - need more interactions"
        
        avg_satisfaction = sum(f.satisfaction_score for f in self.feedback_history) / len(self.feedback_history)
        
        if avg_satisfaction > 0.8:
            return "Excellent - high user satisfaction"
        elif avg_satisfaction > 0.6:
            return "Good - generally positive feedback"
        elif avg_satisfaction > 0.4:
            return "Fair - mixed feedback, learning in progress"
        else:
            return "Poor - need to review recommendation strategy"
    
    def _load_feedback_history(self) -> List[FeedbackEntry]:
        """Load feedback history from file."""
        if not os.path.exists(self.feedback_file):
            return []
        
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [
                    FeedbackEntry(
                        timestamp=entry["timestamp"],
                        feedback_type=FeedbackType(entry["feedback_type"]),
                        original_recommendation=entry["original_recommendation"],
                        user_input=entry["user_input"],
                        user_response=entry["user_response"],
                        final_configuration=entry.get("final_configuration"),
                        modification_requested=entry.get("modification_requested"),
                        confidence_before=entry.get("confidence_before", 0.0),
                        satisfaction_score=entry.get("satisfaction_score", 0.5)
                    )
                    for entry in data
                ]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading feedback history: {e}")
            return []
    
    def _save_feedback_history(self) -> None:
        """Save feedback history to file."""
        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                data = []
                for entry in self.feedback_history:
                    entry_dict = asdict(entry)
                    entry_dict["feedback_type"] = entry.feedback_type.value
                    data.append(entry_dict)
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving feedback history: {e}")
    
    def _load_learned_patterns(self) -> Dict[str, LearningPattern]:
        """Load learned patterns from file."""
        if not os.path.exists(self.patterns_file):
            return {}
        
        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    key: LearningPattern(
                        use_case=pattern["use_case"],
                        preferred_config=pattern["preferred_config"],
                        confidence=pattern["confidence"],
                        sample_count=pattern["sample_count"],
                        last_updated=pattern["last_updated"],
                        success_rate=pattern["success_rate"]
                    )
                    for key, pattern in data.items()
                }
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading learned patterns: {e}")
            return {}
    
    def _save_learned_patterns(self) -> None:
        """Save learned patterns to file."""
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                data = {}
                for key, pattern in self.learned_patterns.items():
                    data[key] = asdict(pattern)
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving learned patterns: {e}")


def create_feedback_learner(data_dir: str = "data") -> SimpleFeedbackLearner:
    """
    Factory function to create a SimpleFeedbackLearner instance.
    
    Args:
        data_dir (str): Directory for storing learning data.
        
    Returns:
        SimpleFeedbackLearner: Configured feedback learning system.
    """
    return SimpleFeedbackLearner(data_dir)