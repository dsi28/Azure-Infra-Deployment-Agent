"""
Storage configuration advisor for Azure Storage Accounts.

Main decision engine that combines use case detection, user preferences,
and business rules to recommend optimal storage configurations.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from .rules import (
    USE_CASE_RULES, 
    StorageConfig, 
    apply_cost_preference,
    generate_reasoning
)
from .use_case_detector import UseCaseDetector, DetectedUseCase, create_use_case_detector


@dataclass
class StorageRecommendation:
    """
    Complete storage account recommendation.
    
    Contains the recommended configuration, confidence level,
    reasoning, and supporting context.
    """
    configuration: StorageConfig
    confidence: float
    detected_use_case: str
    alternative_configs: list[StorageConfig]
    context_used: Dict[str, Any]
    suggestion_id: str


class StorageAdvisor:
    """
    Main storage configuration advisor.
    
    Combines use case detection, user preferences, and decision rules
    to provide intelligent storage account configuration recommendations.
    """
    
    def __init__(self, use_case_detector: Optional[UseCaseDetector] = None):
        """
        Initialize the storage advisor.
        
        Args:
            use_case_detector (Optional[UseCaseDetector]): Custom detector instance.
        """
        self.detector = use_case_detector or create_use_case_detector()
        self.recommendation_counter = 0
    
    def recommend_configuration(
        self,
        user_input: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> StorageRecommendation:
        """
        Recommend storage configuration based on user input and preferences.
        
        Args:
            user_input (str): User's storage requirements description.
            user_preferences (Optional[Dict[str, Any]]): User's stored preferences.
            context (Optional[Dict[str, Any]]): Additional context from conversation.
            
        Returns:
            StorageRecommendation: Complete recommendation with reasoning.
        """
        # Detect use case from user input
        detected_use_case = self.detector.detect_use_case(user_input)
        
        # Get base configuration from rules
        base_config = self._get_base_configuration(detected_use_case)
        
        # Apply user preferences
        final_config = self._apply_user_preferences(base_config, user_preferences, detected_use_case.primary_use_case)
        
        # Apply context hints from detection
        final_config = self._apply_context_hints(final_config, detected_use_case.context_hints)
        
        # Generate alternatives
        alternatives = self._generate_alternatives(base_config, user_preferences)
        
        # Generate reasoning
        reasoning = generate_reasoning(
            base_config,
            final_config, 
            detected_use_case.primary_use_case,
            user_preferences.get("cost_preference", "balanced") if user_preferences else "balanced",
            detected_use_case.performance_indicators
        )
        
        # Create final recommendation
        self.recommendation_counter += 1
        
        return StorageRecommendation(
            configuration=StorageConfig(
                tier=final_config["tier"],
                performance=final_config["performance"],
                replication=final_config["replication"],
                reasoning=reasoning
            ),
            confidence=detected_use_case.confidence,
            detected_use_case=detected_use_case.primary_use_case,
            alternative_configs=alternatives,
            context_used={
                "user_preferences": user_preferences or {},
                "detected_keywords": detected_use_case.keywords_found,
                "context_hints": detected_use_case.context_hints,
                "performance_indicators": detected_use_case.performance_indicators
            },
            suggestion_id=f"storage_rec_{self.recommendation_counter:04d}"
        )
    
    def _get_base_configuration(self, detected_use_case: DetectedUseCase) -> Dict[str, str]:
        """
        Get base configuration from use case rules.
        
        Args:
            detected_use_case (DetectedUseCase): Detected use case information.
            
        Returns:
            Dict[str, str]: Base storage configuration.
        """
        use_case = detected_use_case.primary_use_case
        
        if use_case in USE_CASE_RULES:
            rule = USE_CASE_RULES[use_case]
            return {
                "tier": rule["tier"],
                "performance": rule["performance"],
                "replication": rule["replication"]
            }
        else:
            # Default configuration for unknown use cases
            return {
                "tier": "Hot",
                "performance": "Standard", 
                "replication": "LRS"
            }
    
    def _apply_user_preferences(
        self, 
        base_config: Dict[str, str], 
        user_preferences: Optional[Dict[str, Any]],
        detected_use_case: str
    ) -> Dict[str, str]:
        """
        Apply user preferences to modify base configuration.
        
        Args:
            base_config (Dict[str, str]): Base configuration from rules.
            user_preferences (Optional[Dict[str, Any]]): User's stored preferences.
            detected_use_case (str): The detected use case.
            
        Returns:
            Dict[str, str]: Configuration modified by user preferences.
        """
        if not user_preferences:
            return base_config
        
        config = base_config.copy()
        
        # Apply cost preference modifications
        cost_preference = user_preferences.get("cost_preference", "balanced")
        config = apply_cost_preference(config, cost_preference)
        
        # Apply default overrides if specified
        if "default_performance_tier" in user_preferences:
            config["performance"] = user_preferences["default_performance_tier"]
        
        if "default_replication" in user_preferences:
            config["replication"] = user_preferences["default_replication"]
        
        # Apply learned use case patterns for the detected use case
        use_case_patterns = user_preferences.get("use_case_patterns", {})
        if detected_use_case in use_case_patterns:
            learned_pattern = use_case_patterns[detected_use_case]
            if "tier" in learned_pattern:
                config["tier"] = learned_pattern["tier"]
            if "replication" in learned_pattern:
                config["replication"] = learned_pattern["replication"]
            if "performance" in learned_pattern:
                config["performance"] = learned_pattern["performance"]
        
        return config
    
    def _apply_context_hints(
        self, 
        config: Dict[str, str], 
        context_hints: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Apply context hints to further refine configuration.
        
        Args:
            config (Dict[str, str]): Current configuration.
            context_hints (Dict[str, Any]): Context hints from use case detection.
            
        Returns:
            Dict[str, str]: Configuration refined by context hints.
        """
        refined_config = config.copy()
        
        # Apply production environment requirements
        if context_hints.get("environment") == "production":
            # Production typically needs better redundancy
            if refined_config["replication"] == "LRS":
                refined_config["replication"] = "ZRS"
        
        # Apply compliance requirements
        if context_hints.get("compliance_required"):
            # Compliance often requires geographic redundancy
            if refined_config["replication"] in ["LRS", "ZRS"]:
                refined_config["replication"] = "GRS"
        
        # Apply security requirements
        if context_hints.get("security_sensitive"):
            # Security-sensitive data might need premium features
            if refined_config["performance"] == "Standard":
                refined_config["performance"] = "Premium"
        
        # Apply scalability requirements
        if context_hints.get("scalability_important"):
            # Scalable solutions often benefit from zone redundancy
            if refined_config["replication"] == "LRS":
                refined_config["replication"] = "ZRS"
            # May need premium performance
            if refined_config["performance"] == "Standard":
                refined_config["performance"] = "Premium"
        
        # Apply urgency indicators
        if context_hints.get("urgency") == "high":
            # High urgency usually means don't compromise on performance
            refined_config["tier"] = "Hot"
            if refined_config["performance"] == "Standard":
                refined_config["performance"] = "Premium"
        
        # Apply size hints
        estimated_sizes = context_hints.get("estimated_sizes", [])
        if estimated_sizes:
            # Large storage needs might benefit from different configurations
            for size in estimated_sizes:
                if "TB" in size and int(size.replace("TB", "")) >= 10:
                    # Very large storage might benefit from Cool tier for cost
                    if refined_config["tier"] == "Hot":
                        refined_config["tier"] = "Cool"
                    break
        
        return refined_config
    
    def _generate_alternatives(
        self, 
        base_config: Dict[str, str], 
        user_preferences: Optional[Dict[str, Any]]
    ) -> list[StorageConfig]:
        """
        Generate alternative configurations for user consideration.
        
        Args:
            base_config (Dict[str, str]): Base configuration.
            user_preferences (Optional[Dict[str, Any]]): User preferences.
            
        Returns:
            list[StorageConfig]: List of alternative configurations.
        """
        alternatives = []
        
        # Cost-optimized alternative
        cost_optimized = apply_cost_preference(base_config, "optimized")
        if cost_optimized != base_config:
            alternatives.append(StorageConfig(
                tier=cost_optimized["tier"],
                performance=cost_optimized["performance"],
                replication=cost_optimized["replication"],
                reasoning="Cost-optimized alternative with lower storage costs"
            ))
        
        # Performance-optimized alternative
        performance_optimized = apply_cost_preference(base_config, "performance")
        if performance_optimized != base_config:
            alternatives.append(StorageConfig(
                tier=performance_optimized["tier"],
                performance=performance_optimized["performance"],
                replication=performance_optimized["replication"],
                reasoning="Performance-optimized alternative with higher throughput and availability"
            ))
        
        # High availability alternative (if not already using ZRS/GRS)
        if base_config["replication"] == "LRS":
            ha_config = base_config.copy()
            ha_config["replication"] = "ZRS"
            alternatives.append(StorageConfig(
                tier=ha_config["tier"],
                performance=ha_config["performance"],
                replication=ha_config["replication"],
                reasoning="High availability alternative with zone redundancy"
            ))
        
        return alternatives
    
    def explain_recommendation(self, recommendation: StorageRecommendation) -> Dict[str, Any]:
        """
        Provide detailed explanation of a recommendation.
        
        Args:
            recommendation (StorageRecommendation): Recommendation to explain.
            
        Returns:
            Dict[str, Any]: Detailed explanation and supporting information.
        """
        config = recommendation.configuration
        
        explanation = {
            "summary": f"Recommended {config.performance} performance {config.tier} tier with {config.replication} replication",
            "reasoning": config.reasoning,
            "confidence_level": self._get_confidence_level(recommendation.confidence),
            "detected_use_case": recommendation.detected_use_case,
            "key_factors": [],
            "trade_offs": {},
            "alternatives_available": len(recommendation.alternative_configs)
        }
        
        # Add key factors that influenced the decision
        context = recommendation.context_used
        if context.get("detected_keywords"):
            explanation["key_factors"].append(f"Detected use case: {', '.join(context['detected_keywords'])}")
        
        if context.get("performance_indicators", {}).get("performance"):
            explanation["key_factors"].append("Performance requirements identified")
        
        if context.get("performance_indicators", {}).get("cost"):
            explanation["key_factors"].append("Cost optimization requested")
        
        if context.get("context_hints", {}).get("environment"):
            explanation["key_factors"].append(f"Environment: {context['context_hints']['environment']}")
        
        # Add trade-offs explanation
        explanation["trade_offs"] = {
            "cost_vs_performance": self._explain_cost_performance_tradeoff(config),
            "availability_vs_cost": self._explain_availability_cost_tradeoff(config),
            "access_speed_vs_cost": self._explain_access_speed_tradeoff(config)
        }
        
        return explanation
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Convert numeric confidence to human-readable level."""
        if confidence >= 0.8:
            return "High"
        elif confidence >= 0.6:
            return "Medium"
        elif confidence >= 0.4:
            return "Low"
        else:
            return "Very Low"
    
    def _explain_cost_performance_tradeoff(self, config: StorageConfig) -> str:
        """Explain cost vs performance tradeoff for the configuration."""
        if config.performance == "Premium":
            return "Premium performance provides higher IOPS and throughput at increased cost"
        else:
            return "Standard performance balances cost and performance for most workloads"
    
    def _explain_availability_cost_tradeoff(self, config: StorageConfig) -> str:
        """Explain availability vs cost tradeoff for the configuration."""
        if config.replication == "GRS":
            return "Geo-redundant storage provides disaster recovery but costs more than local redundancy"
        elif config.replication == "ZRS":
            return "Zone-redundant storage provides high availability within region at moderate cost"
        else:
            return "Locally redundant storage minimizes cost but provides basic fault tolerance"
    
    def _explain_access_speed_tradeoff(self, config: StorageConfig) -> str:
        """Explain access speed vs cost tradeoff for the configuration."""
        if config.tier == "Hot":
            return "Hot tier provides fast access for frequently used data at higher storage cost"
        elif config.tier == "Cool":
            return "Cool tier reduces storage cost but has higher access costs and slower retrieval"
        else:
            return "Archive tier minimizes storage cost but requires hours for data retrieval"


def create_storage_advisor() -> StorageAdvisor:
    """
    Factory function to create a StorageAdvisor instance.
    
    Returns:
        StorageAdvisor: Configured advisor instance.
    """
    return StorageAdvisor()