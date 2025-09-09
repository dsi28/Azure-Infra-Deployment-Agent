"""
Recommendation feedback learning system for Azure Infrastructure Agent.

This module tracks user preferences between LLM and rule-based recommendations
to improve future suggestion quality and personalization.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from ..decision.dual_recommender import RecommendationType, DualRecommendation
from ..conversation.dual_recommendation_ui import UserChoice
from ...config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RecommendationFeedback:
    """
    Single feedback record for recommendation choice.
    
    Tracks what was recommended by each system and what the user ultimately chose,
    along with contextual information for learning patterns.
    """
    timestamp: str
    user_input: str
    user_choice: str  # 'llm', 'rules'
    
    # LLM recommendation (if available)
    llm_available: bool
    llm_tier: Optional[str] = None
    llm_performance: Optional[str] = None
    llm_replication: Optional[str] = None
    llm_confidence: Optional[float] = None
    llm_reasoning: Optional[str] = None
    
    # Rules recommendation
    rules_tier: str = ""
    rules_performance: str = ""
    rules_replication: str = ""
    rules_reasoning: str = ""
    
    # Final configuration chosen
    final_tier: str = ""
    final_performance: str = ""
    final_replication: str = ""
    final_reasoning: str = ""
    
    # Context and analysis
    use_case_keywords: List[str] = None
    primary_use_case: Optional[str] = None
    agreement_score: Optional[float] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.use_case_keywords is None:
            self.use_case_keywords = []


class RecommendationPreferenceTracker:
    """
    Tracks and analyzes user preferences between recommendation types.
    
    This class maintains a history of user choices and provides insights
    into when users prefer LLM vs rule-based recommendations.
    """
    
    def __init__(self, feedback_file: str = "data/recommendation_feedback.json"):
        """
        Initialize recommendation preference tracker.
        
        Args:
            feedback_file (str): Path to feedback storage file.
        """
        self.feedback_file = feedback_file
        self.feedback_history: List[RecommendationFeedback] = []
        self._ensure_data_directory()
        self._load_feedback_history()
        logger.info(f"RecommendationPreferenceTracker initialized with {len(self.feedback_history)} records")
    
    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
    
    def _load_feedback_history(self) -> None:
        """Load existing feedback history from file."""
        try:
            if os.path.exists(self.feedback_file):
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.feedback_history = [
                        RecommendationFeedback(**record) for record in data
                    ]
                logger.debug(f"Loaded {len(self.feedback_history)} feedback records")
            else:
                logger.info("No existing feedback file found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading feedback history: {str(e)}")
            self.feedback_history = []
    
    def record_feedback(
        self,
        dual_rec: DualRecommendation,
        user_choice: UserChoice,
        final_config: Dict[str, Any]
    ) -> None:
        """
        Record user's choice feedback for learning.
        
        Args:
            dual_rec (DualRecommendation): The dual recommendation presented.
            user_choice (UserChoice): User's choice between recommendations.
            final_config (Dict[str, Any]): Final configuration selected.
        """
        try:
            # Convert user choice to string
            choice_mapping = {
                UserChoice.LLM: 'llm',
                UserChoice.RULES: 'rules',
                UserChoice.CANCEL: 'cancel'
            }
            
            choice_str = choice_mapping.get(user_choice, 'unknown')
            
            # Don't record cancelled choices
            if choice_str == 'cancel':
                return
            
            # Create feedback record
            feedback = RecommendationFeedback(
                timestamp=datetime.now().isoformat(),
                user_input=dual_rec.user_input,
                user_choice=choice_str,
                
                # LLM data
                llm_available=dual_rec.llm_available,
                llm_tier=dual_rec.llm_recommendation.tier if dual_rec.llm_recommendation else None,
                llm_performance=dual_rec.llm_recommendation.performance if dual_rec.llm_recommendation else None,
                llm_replication=dual_rec.llm_recommendation.replication if dual_rec.llm_recommendation else None,
                llm_confidence=dual_rec.llm_recommendation.confidence if dual_rec.llm_recommendation else None,
                llm_reasoning=dual_rec.llm_recommendation.reasoning if dual_rec.llm_recommendation else None,
                
                # Rules data
                rules_tier=dual_rec.rules_recommendation.tier,
                rules_performance=dual_rec.rules_recommendation.performance,
                rules_replication=dual_rec.rules_recommendation.replication,
                rules_reasoning=dual_rec.rules_recommendation.reasoning,
                
                # Final configuration
                final_tier=final_config.get('tier', ''),
                final_performance=final_config.get('performance', ''),
                final_replication=final_config.get('replication', ''),
                final_reasoning=final_config.get('reasoning', ''),
                
                # Context
                use_case_keywords=dual_rec.context.get('use_case_keywords', []),
                primary_use_case=dual_rec.context.get('primary_use_case'),
                agreement_score=dual_rec.get_agreement_score()
            )
            
            # Add to history and save
            self.feedback_history.append(feedback)
            self._save_feedback_history()
            
            logger.info(f"Recorded feedback: user chose '{choice_str}' with agreement score {feedback.agreement_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error recording feedback: {str(e)}")
    
    def _save_feedback_history(self) -> None:
        """Save feedback history to file."""
        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                data = [asdict(feedback) for feedback in self.feedback_history]
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.feedback_history)} feedback records")
            
        except Exception as e:
            logger.error(f"Error saving feedback history: {str(e)}")
    
    def get_preference_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive preference statistics.
        
        Returns:
            Dict[str, Any]: Statistics about user preferences.
        """
        if not self.feedback_history:
            return {
                'total_choices': 0,
                'llm_preference_rate': 0.0,
                'rules_preference_rate': 0.0
            }
        
        total_choices = len(self.feedback_history)
        llm_choices = sum(1 for f in self.feedback_history if f.user_choice == 'llm')
        rules_choices = sum(1 for f in self.feedback_history if f.user_choice == 'rules')
        
        # Only count cases where LLM was available for preference rates
        llm_available_cases = [f for f in self.feedback_history if f.llm_available]
        llm_available_count = len(llm_available_cases)
        
        if llm_available_count > 0:
            llm_chosen_when_available = sum(1 for f in llm_available_cases if f.user_choice == 'llm')
            rules_chosen_when_llm_available = sum(1 for f in llm_available_cases if f.user_choice == 'rules')
            
            llm_preference_rate = llm_chosen_when_available / llm_available_count
            rules_vs_llm_rate = rules_chosen_when_llm_available / llm_available_count
        else:
            llm_preference_rate = 0.0
            rules_vs_llm_rate = 0.0
        
        return {
            'total_choices': total_choices,
            'llm_available_cases': llm_available_count,
            'llm_choices': llm_choices,
            'rules_choices': rules_choices,
            'llm_preference_rate': llm_preference_rate,
            'rules_preference_rate': rules_vs_llm_rate
        }
    
    def get_use_case_preferences(self) -> Dict[str, Dict[str, int]]:
        """
        Get preference patterns by use case.
        
        Returns:
            Dict[str, Dict[str, int]]: Preferences broken down by use case.
        """
        use_case_prefs = {}
        
        for feedback in self.feedback_history:
            if not feedback.primary_use_case:
                continue
                
            use_case = feedback.primary_use_case
            if use_case not in use_case_prefs:
                use_case_prefs[use_case] = {'llm': 0, 'rules': 0}
            
            use_case_prefs[use_case][feedback.user_choice] += 1
        
        return use_case_prefs
    
    def get_agreement_vs_choice_analysis(self) -> Dict[str, List[float]]:
        """
        Analyze relationship between recommendation agreement and user choice.
        
        Returns:
            Dict[str, List[float]]: Agreement scores grouped by user choice.
        """
        analysis = {'llm': [], 'rules': []}
        
        for feedback in self.feedback_history:
            if feedback.agreement_score is not None:
                analysis[feedback.user_choice].append(feedback.agreement_score)
        
        return analysis
    
    def should_prefer_llm(self, use_case: Optional[str] = None) -> bool:
        """
        Determine if LLM should be preferred based on historical patterns.
        
        Args:
            use_case (Optional[str]): Specific use case to analyze.
            
        Returns:
            bool: True if LLM should be preferred for this context.
        """
        # Get overall or use-case specific preferences
        if use_case:
            use_case_prefs = self.get_use_case_preferences()
            if use_case not in use_case_prefs:
                return False  # Default to rules for unknown use cases
                
            prefs = use_case_prefs[use_case]
            total = sum(prefs.values())
            if total < 3:  # Need at least 3 samples
                return False
                
            llm_rate = prefs['llm'] / total
        else:
            stats = self.get_preference_statistics()
            llm_rate = stats['llm_preference_rate']
        
        return llm_rate > 0.6  # Prefer LLM if chosen >60% of the time
    
    def get_recommendation_accuracy(self) -> Dict[str, float]:
        """
        Calculate accuracy of recommendations (how often they're chosen unchanged).
        
        Returns:
            Dict[str, float]: Accuracy rates for each recommendation type.
        """
        llm_correct = 0
        llm_total = 0
        rules_correct = 0
        rules_total = 0
        
        for feedback in self.feedback_history:
            # Check LLM accuracy (if available and chosen)
            if feedback.llm_available and feedback.user_choice == 'llm':
                llm_total += 1
                if (feedback.llm_tier == feedback.final_tier and
                    feedback.llm_performance == feedback.final_performance and
                    feedback.llm_replication == feedback.final_replication):
                    llm_correct += 1
            
            # Check rules accuracy (if chosen)
            if feedback.user_choice == 'rules':
                rules_total += 1
                if (feedback.rules_tier == feedback.final_tier and
                    feedback.rules_performance == feedback.final_performance and
                    feedback.rules_replication == feedback.final_replication):
                    rules_correct += 1
        
        return {
            'llm_accuracy': llm_correct / llm_total if llm_total > 0 else 0.0,
            'rules_accuracy': rules_correct / rules_total if rules_total > 0 else 0.0
        }


def create_recommendation_tracker() -> RecommendationPreferenceTracker:
    """
    Factory function to create recommendation preference tracker.
    
    Returns:
        RecommendationPreferenceTracker: Configured tracker instance.
    """
    return RecommendationPreferenceTracker()