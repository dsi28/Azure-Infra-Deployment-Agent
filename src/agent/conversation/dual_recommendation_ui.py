"""
Dual recommendation user interface for Azure Infrastructure Agent.

This module handles the presentation and user interaction for side-by-side
LLM and rule-based storage recommendations.
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum

from ..decision.dual_recommender import DualRecommendation, RecommendationType
from ..decision.llm_advisor import LLMRecommendation
from ..decision.rules import StorageConfig
from ...config.logging import get_logger

logger = get_logger(__name__)


class UserChoice(Enum):
    """User's choice for recommendation selection."""
    LLM = "1"
    RULES = "2" 
    CANCEL = "cancel"


class DualRecommendationUI:
    """
    User interface for dual recommendation presentation and selection.
    
    This class handles the display of side-by-side recommendations and
    collection of user preferences between different recommendation approaches.
    """
    
    def __init__(self):
        """Initialize dual recommendation UI."""
        logger.info("DualRecommendationUI initialized")
    
    def present_dual_recommendations(self, dual_rec: DualRecommendation) -> None:
        """
        Present both recommendations to the user in a clear comparison format.
        
        Args:
            dual_rec (DualRecommendation): Dual recommendation to present.
        """
        print("\n" + "="*80)
        print("STORAGE CONFIGURATION RECOMMENDATIONS")
        print("="*80)
        
        if not dual_rec.llm_available:
            self._present_rules_only(dual_rec.rules_recommendation)
            return
        
        # Present side-by-side comparison
        self._present_side_by_side(dual_rec)
        
        # Show agreement analysis
        self._show_agreement_analysis(dual_rec)
    
    def _present_rules_only(self, rules_rec: StorageConfig) -> None:
        """
        Present only rule-based recommendation when LLM unavailable.
        
        Args:
            rules_rec (StorageConfig): Rule-based recommendation.
        """
        print("AI Recommendation: Unavailable (LLM offline)")
        print("Rule-Based Recommendation: Available")
        print()
        
        print("RULE-BASED CONFIGURATION:")
        print(f"   • Access Tier: {rules_rec.tier}")
        print(f"   • Performance: {rules_rec.performance}")  
        print(f"   • Replication: {rules_rec.replication}")
        print(f"   • Reasoning: {rules_rec.reasoning}")
        print()
    
    def _present_side_by_side(self, dual_rec: DualRecommendation) -> None:
        """
        Present LLM and rules recommendations side-by-side.
        
        Args:
            dual_rec (DualRecommendation): Dual recommendation to present.
        """
        llm_rec = dual_rec.llm_recommendation
        rules_rec = dual_rec.rules_recommendation
        
        print("AI RECOMMENDATION" + " " * 30 + "RULE-BASED RECOMMENDATION")
        print("-" * 40 + " " * 5 + "-" * 35)
        
        # Tier comparison
        tier_marker = "+" if llm_rec.tier == rules_rec.tier else "!"
        print(f"Access Tier: {llm_rec.tier:<15} {tier_marker}     Access Tier: {rules_rec.tier}")
        
        # Performance comparison  
        perf_marker = "+" if llm_rec.performance == rules_rec.performance else "!"
        print(f"Performance: {llm_rec.performance:<15} {perf_marker}     Performance: {rules_rec.performance}")
        
        # Replication comparison
        repl_marker = "+" if llm_rec.replication == rules_rec.replication else "!"
        print(f"Replication: {llm_rec.replication:<15} {repl_marker}     Replication: {rules_rec.replication}")
        
        # Confidence  
        confidence_str = f"{llm_rec.confidence:.1%}"
        print(f"Confidence: {confidence_str:<16}     Confidence: Built-in rules")
        
        print()
        
        # Reasoning
        print("AI REASONING:")
        print(f"   {llm_rec.reasoning}")
        print()
        
        print("RULE-BASED REASONING:")
        print(f"   {rules_rec.reasoning}")
        print()
    
    def _show_agreement_analysis(self, dual_rec: DualRecommendation) -> None:
        """
        Show agreement analysis between recommendations.
        
        Args:
            dual_rec (DualRecommendation): Dual recommendation to analyze.
        """
        if not dual_rec.llm_available:
            return
            
        agreement = dual_rec.get_agreement_score()
        
        print("AGREEMENT ANALYSIS:")
        
        if agreement >= 0.67:
            print(f"   + High Agreement ({agreement:.1%}) - Both recommendations align well")
        elif agreement >= 0.33:
            print(f"   ! Moderate Agreement ({agreement:.1%}) - Some differences to consider")
        else:
            print(f"   - Low Agreement ({agreement:.1%}) - Significant differences detected")
        
        print()
    
    def get_user_choice(self, dual_rec: DualRecommendation) -> Tuple[UserChoice, Optional[Dict[str, Any]]]:
        """
        Collect user's choice between recommendations.
        
        Args:
            dual_rec (DualRecommendation): Dual recommendation being chosen from.
            
        Returns:
            Tuple[UserChoice, Optional[Dict[str, Any]]]: User choice and custom config if applicable.
        """
        if not dual_rec.llm_available:
            return self._get_rules_only_choice()
        
        return self._get_dual_choice(dual_rec)
    
    def _get_rules_only_choice(self) -> Tuple[UserChoice, Optional[Dict[str, Any]]]:
        """
        Get user choice when only rules recommendation available.
        
        Returns:
            Tuple[UserChoice, Optional[Dict[str, Any]]]: User choice and custom config.
        """
        print("CHOICE OPTIONS:")
        print("   Use Rule-Based Recommendation")
        print("   Cancel")
        print()
        
        while True:
            choice = input("Select your choice (1/cancel): ").strip().lower()
            
            if choice in ['1']:
                return UserChoice.RULES, None
            elif choice in ['cancel', 'c']:
                return UserChoice.CANCEL, None
            else:
                print("❌ Invalid choice. Please enter 1 or cancel.")
    
    def _get_dual_choice(self, dual_rec: DualRecommendation) -> Tuple[UserChoice, Optional[Dict[str, Any]]]:
        """
        Get user choice between dual recommendations.
        
        Args:
            dual_rec (DualRecommendation): Dual recommendation being chosen from.
            
        Returns:
            Tuple[UserChoice, Optional[Dict[str, Any]]]: User choice and custom config.
        """
        print("CHOICE OPTIONS:")
        print("1  Use AI Recommendation (LLM-based)")
        print("2  Use Rule-Based Recommendation")
        print("3  Cancel")
        print()
        
        while True:
            choice = input("Select your choice (1/2/cancel): ").strip().lower()
            
            if choice in ['1']:
                return UserChoice.LLM, None
            elif choice in ['2']:
                return UserChoice.RULES, None
            elif choice in ['cancel', 'c']:
                return UserChoice.CANCEL, None
            else:
                print("❌ Invalid choice. Please enter 1, 2, or cancel.")
    
    def show_final_selection(self, choice: UserChoice, config: Dict[str, Any]) -> None:
        """
        Display the final selected configuration.
        
        Args:
            choice (UserChoice): Type of choice made.
            config (Dict[str, Any]): Final configuration selected.
        """
        choice_labels = {
            UserChoice.LLM: "AI Recommendation",
            UserChoice.RULES: "Rule-Based Recommendation"
        }
        
        print("\n" + "="*60)
        print("FINAL CONFIGURATION SELECTED")
        print("="*60)
        print(f"Source: {choice_labels.get(choice, 'Unknown')}")
        print()
        print("Configuration Details:")
        print(f"   • Access Tier: {config.get('tier', 'N/A')}")
        print(f"   • Performance: {config.get('performance', 'N/A')}")
        print(f"   • Replication: {config.get('replication', 'N/A')}")
        
        if config.get('reasoning'):
            print(f"   • Reasoning: {config['reasoning']}")
        
        print("="*60)


def create_dual_recommendation_ui() -> DualRecommendationUI:
    """
    Factory function to create dual recommendation UI.
    
    Returns:
        DualRecommendationUI: Configured dual recommendation UI instance.
    """
    return DualRecommendationUI()