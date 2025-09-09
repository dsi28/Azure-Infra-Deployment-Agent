"""
Dual recommendation orchestrator for Azure Infrastructure Agent.

This module coordinates both LLM-based and rule-based recommendation systems
to provide side-by-side storage configuration suggestions.
"""

from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

from .llm_advisor import LLMStorageAdvisor, LLMRecommendation
from .storage_advisor import StorageAdvisor
from .use_case_detector import UseCaseDetector
from .rules import get_use_case_keywords, get_performance_indicators
from .rules import StorageConfig
from ..memory.user_profile import UserProfile
from ...config.logging import get_logger

logger = get_logger(__name__)


class RecommendationType(Enum):
    """Types of recommendations available."""
    LLM = "llm"
    RULES = "rules"
    CUSTOM = "custom"


@dataclass
class DualRecommendation:
    """
    Container for both LLM and rule-based recommendations.
    
    Provides structured comparison between different recommendation approaches
    with confidence scoring and reasoning for each.
    """
    llm_recommendation: Optional[LLMRecommendation]
    rules_recommendation: StorageConfig
    llm_available: bool
    user_input: str
    context: Dict[str, Any]
    
    def get_agreement_score(self) -> float:
        """
        Calculate how much the two recommendations agree.
        
        Returns:
            float: Agreement score between 0.0 and 1.0.
        """
        if not self.llm_recommendation:
            return 0.0
        
        agreement_points = 0
        total_points = 3
        
        # Check tier agreement
        if self.llm_recommendation.tier == self.rules_recommendation.tier:
            agreement_points += 1
            
        # Check performance agreement  
        if self.llm_recommendation.performance == self.rules_recommendation.performance:
            agreement_points += 1
            
        # Check replication agreement
        if self.llm_recommendation.replication == self.rules_recommendation.replication:
            agreement_points += 1
            
        return agreement_points / total_points
    
    def get_confidence_difference(self) -> Optional[float]:
        """
        Get the confidence difference between recommendations.
        
        Returns:
            Optional[float]: Difference in confidence scores, or None if LLM unavailable.
        """
        if not self.llm_recommendation:
            return None
            
        # Rules confidence comes from the context (use case detection confidence)
        rules_confidence = self.context.get('rules_confidence', 0.7)
        
        return abs(self.llm_recommendation.confidence - rules_confidence)


class DualRecommendationEngine:
    """
    Orchestrates both LLM and rule-based recommendation systems.
    
    This class manages the dual recommendation process, coordinating between
    different recommendation approaches and providing structured comparisons.
    """
    
    def __init__(self):
        """Initialize dual recommendation engine."""
        self.llm_advisor = LLMStorageAdvisor()
        self.rules_advisor = StorageAdvisor()
        logger.info("DualRecommendationEngine initialized")
    
    def get_dual_recommendation(
        self,
        user_input: str,
        user_profile: Optional[UserProfile] = None
    ) -> DualRecommendation:
        """
        Get both LLM and rule-based recommendations for user input.
        
        Args:
            user_input (str): User's storage requirement description.
            user_profile (Optional[UserProfile]): User preferences and history.
            
        Returns:
            DualRecommendation: Container with both recommendations and metadata.
        """
        logger.info(f"Getting dual recommendations for: '{user_input}'")
        
        # Build context from user input
        context = self._build_context(user_input, user_profile)
        
        # Get rule-based recommendation (always available)
        rules_recommendation = self._get_rules_recommendation(user_input, user_profile, context)
        
        # Get LLM recommendation (may fail)
        llm_recommendation, llm_available = self._get_llm_recommendation(user_input, user_profile, context)
        
        # Create dual recommendation container
        dual_rec = DualRecommendation(
            llm_recommendation=llm_recommendation,
            rules_recommendation=rules_recommendation,
            llm_available=llm_available,
            user_input=user_input,
            context=context
        )
        
        # Log agreement analysis
        if llm_available:
            agreement = dual_rec.get_agreement_score()
            logger.info(f"Recommendation agreement score: {agreement:.2f}")
            
            if agreement >= 0.67:
                logger.info("High agreement between LLM and rules recommendations")
            elif agreement >= 0.33:
                logger.info("Moderate agreement between recommendations")
            else:
                logger.info("Low agreement between recommendations - user choice important")
        
        return dual_rec
    
    def _build_context(
        self,
        user_input: str,
        user_profile: Optional[UserProfile] = None
    ) -> Dict[str, Any]:
        """
        Build context information for recommendations.
        
        Args:
            user_input (str): User's storage requirement description.
            user_profile (Optional[UserProfile]): User preferences and history.
            
        Returns:
            Dict[str, Any]: Context information for recommendation engines.
        """
        # Detect use case and keywords
        use_case_keywords = get_use_case_keywords(user_input)
        performance_indicators = get_performance_indicators(user_input)
        
        # Use detector to get primary use case
        detector = UseCaseDetector()
        detected_use_case = detector.detect_use_case(user_input)
        primary_use_case = detected_use_case.primary_use_case
        
        context = {
            'use_case_keywords': use_case_keywords,
            'performance_indicators': performance_indicators,
            'primary_use_case': primary_use_case,
            'user_profile': user_profile
        }
        
        logger.debug(f"Built context with {len(use_case_keywords)} keywords, "
                    f"primary use case: {primary_use_case}")
        
        return context
    
    def _get_rules_recommendation(
        self,
        user_input: str,
        user_profile: Optional[UserProfile],
        context: Dict[str, Any]
    ) -> StorageConfig:
        """
        Get rule-based recommendation.
        
        Args:
            user_input (str): User's storage requirement description.
            user_profile (Optional[UserProfile]): User preferences and history.
            context (Dict[str, Any]): Context information.
            
        Returns:
            StorageConfig: Rule-based storage configuration recommendation.
        """
        try:
            # Convert user_profile to preferences dict if available
            user_preferences = None
            if user_profile:
                user_preferences = {
                    'preferred_regions': user_profile.preferred_regions,
                    'cost_preference': user_profile.cost_preference,
                    'default_performance_tier': user_profile.default_performance_tier,
                    'default_replication': user_profile.default_replication,
                    'use_case_patterns': user_profile.use_case_patterns
                }
            
            recommendation = self.rules_advisor.recommend_configuration(
                user_input=user_input,
                user_preferences=user_preferences,
                context=context
            )
            
            # Store rules confidence in context
            confidence = recommendation.confidence if hasattr(recommendation, 'confidence') else 0.7
            context['rules_confidence'] = confidence
            
            logger.debug("Rules recommendation generated successfully")
            return recommendation.configuration
            
        except Exception as e:
            logger.error(f"Error getting rules recommendation: {str(e)}")
            # Fallback to basic recommendation
            return StorageConfig(
                tier="Hot",
                performance="Standard", 
                replication="LRS",
                reasoning="Default configuration due to rules engine error"
            )
    
    def _get_llm_recommendation(
        self,
        user_input: str,
        user_profile: Optional[UserProfile],
        context: Dict[str, Any]
    ) -> Tuple[Optional[LLMRecommendation], bool]:
        """
        Get LLM-based recommendation with fallback handling.
        
        Args:
            user_input (str): User's storage requirement description.
            user_profile (Optional[UserProfile]): User preferences and history.
            context (Dict[str, Any]): Context information.
            
        Returns:
            Tuple[Optional[LLMRecommendation], bool]: LLM recommendation and availability flag.
        """
        try:
            recommendation = self.llm_advisor.get_recommendation(
                user_input=user_input,
                user_profile=user_profile,
                context=context
            )
            
            if recommendation:
                logger.debug("LLM recommendation generated successfully")
                return recommendation, True
            else:
                logger.warning("LLM recommendation failed - no valid response")
                return None, False
                
        except Exception as e:
            logger.error(f"Error getting LLM recommendation: {str(e)}")
            return None, False
    
    def compare_recommendations(self, dual_rec: DualRecommendation) -> Dict[str, Any]:
        """
        Analyze and compare the dual recommendations.
        
        Args:
            dual_rec (DualRecommendation): Dual recommendation to analyze.
            
        Returns:
            Dict[str, Any]: Comparison analysis results.
        """
        analysis = {
            'agreement_score': dual_rec.get_agreement_score(),
            'confidence_difference': dual_rec.get_confidence_difference(),
            'llm_available': dual_rec.llm_available,
            'differences': [],
            'similarities': []
        }
        
        if not dual_rec.llm_recommendation:
            analysis['recommendation'] = "Use rules-based recommendation (LLM unavailable)"
            return analysis
        
        llm_rec = dual_rec.llm_recommendation
        rules_rec = dual_rec.rules_recommendation
        
        # Analyze differences
        if llm_rec.tier != rules_rec.tier:
            analysis['differences'].append(f"Tier: LLM={llm_rec.tier}, Rules={rules_rec.tier}")
        else:
            analysis['similarities'].append(f"Both recommend {llm_rec.tier} tier")
            
        if llm_rec.performance != rules_rec.performance:
            analysis['differences'].append(f"Performance: LLM={llm_rec.performance}, Rules={rules_rec.performance}")
        else:
            analysis['similarities'].append(f"Both recommend {llm_rec.performance} performance")
            
        if llm_rec.replication != rules_rec.replication:
            analysis['differences'].append(f"Replication: LLM={llm_rec.replication}, Rules={rules_rec.replication}")
        else:
            analysis['similarities'].append(f"Both recommend {llm_rec.replication} replication")
        
        # Generate recommendation
        agreement = analysis['agreement_score']
        if agreement >= 0.67:
            analysis['recommendation'] = "High agreement - either recommendation is good"
        elif agreement >= 0.33:
            analysis['recommendation'] = "Moderate agreement - consider user preference"
        else:
            analysis['recommendation'] = "Low agreement - user choice critical"
        
        return analysis


def create_dual_recommender() -> DualRecommendationEngine:
    """
    Factory function to create dual recommendation engine.
    
    Returns:
        DualRecommendationEngine: Configured dual recommendation engine.
    """
    return DualRecommendationEngine()