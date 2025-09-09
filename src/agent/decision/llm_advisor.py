"""
LLM-based storage recommendations for Azure Infrastructure Agent.

This module implements intelligent storage account recommendations using
local Ollama LLM with Azure storage expertise prompts.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..llm.ollama_client import OllamaClient
from ..memory.user_profile import UserProfile
from .rules import StorageConfig
from ...config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMRecommendation:
    """
    LLM-generated storage recommendation with reasoning.
    
    Contains the recommended configuration along with the LLM's
    reasoning and confidence assessment.
    """
    tier: str
    performance: str
    replication: str
    reasoning: str
    confidence: float
    raw_response: str


class LLMStorageAdvisor:
    """
    LLM-based storage advisor using Ollama for intelligent recommendations.
    
    This class leverages local LLM capabilities to provide storage account
    configuration recommendations based on user input and context.
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize LLM storage advisor.
        
        Args:
            ollama_client (Optional[OllamaClient]): Ollama client for LLM inference.
        """
        self.ollama_client = ollama_client or OllamaClient()
        self.system_prompt = self._build_system_prompt()
        logger.info("LLMStorageAdvisor initialized")
    
    def _build_system_prompt(self) -> str:
        """
        Build comprehensive system prompt with Azure storage expertise.
        
        Returns:
            str: System prompt containing Azure storage knowledge.
        """
        return """You are an Azure Storage expert with deep knowledge of storage account configurations.

AZURE STORAGE TIERS:
- Hot: Frequently accessed data, highest storage cost, lowest access cost
- Cool: Infrequently accessed data (monthly), lower storage cost, higher access cost
- Archive: Rarely accessed data (yearly), lowest storage cost, highest access cost

PERFORMANCE TIERS:
- Standard: Cost-effective, good for most workloads, up to 20,000 IOPS
- Premium: High performance, SSD-based, up to 80,000 IOPS, higher cost

REPLICATION TYPES:
- LRS (Locally Redundant): 3 copies in same region, lowest cost, 99.999999999% durability
- GRS (Geo-Redundant): 6 copies across 2 regions, disaster recovery, higher cost
- ZRS (Zone-Redundant): 3 copies across availability zones, high availability
- RAGRS (Read-Access GRS): GRS + read access to secondary region
- GZRS (Geo-Zone-Redundant): ZRS + geo-replication
- RAGZRS (Read-Access GZRS): GZRS + read access to secondary region

DECISION GUIDELINES:
- Images/Media for websites: Hot + Standard + LRS (fast access, cost-effective)
- High-traffic applications: Hot + Premium + ZRS (performance + availability)
- Backups: Cool + Standard + GRS (cost-effective + disaster recovery)
- Archive/Compliance: Archive + Standard + GRS (lowest cost + compliance)
- Development/Testing: Hot + Standard + LRS (cost-effective for dev)
- Data lakes/Analytics: Cool + Premium + ZRS (performance for analytics)

Respond with JSON format:
{
    "tier": "Hot|Cool|Archive",
    "performance": "Standard|Premium", 
    "replication": "LRS|GRS|ZRS|RAGRS|GZRS|RAGZRS",
    "reasoning": "Brief explanation of choices",
    "confidence": 0.8
}"""

    def get_recommendation(
        self, 
        user_input: str, 
        user_profile: Optional[UserProfile] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[LLMRecommendation]:
        """
        Get LLM-based storage recommendation for user input.
        
        Args:
            user_input (str): User's storage requirement description.
            user_profile (Optional[UserProfile]): User preferences and history.
            context (Optional[Dict[str, Any]]): Additional context information.
            
        Returns:
            Optional[LLMRecommendation]: LLM recommendation or None if failed.
        """
        try:
            # Build context-aware prompt
            prompt = self._build_recommendation_prompt(user_input, user_profile, context)
            
            # Combine system prompt with user prompt
            full_prompt = f"{self.system_prompt}\n\n{prompt}"
            
            # Get LLM response
            response_obj = self.ollama_client.generate(prompt=full_prompt)
            response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
            
            if not response:
                logger.warning("LLM returned empty response")
                return None
            
            # Parse and validate response
            recommendation = self._parse_llm_response(response, user_input)
            
            if recommendation:
                logger.info(f"LLM recommendation generated with confidence {recommendation.confidence}")
            else:
                logger.warning("Failed to parse LLM response into valid recommendation")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting LLM recommendation: {str(e)}")
            return None
    
    def _build_recommendation_prompt(
        self,
        user_input: str,
        user_profile: Optional[UserProfile] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build context-aware prompt for LLM recommendation.
        
        Args:
            user_input (str): User's storage requirement description.
            user_profile (Optional[UserProfile]): User preferences and history.
            context (Optional[Dict[str, Any]]): Additional context information.
            
        Returns:
            str: Complete prompt for LLM.
        """
        prompt_parts = [
            f"User request: '{user_input}'"
        ]
        
        # Add user preferences if available
        if user_profile:
            preferences = []
            if user_profile.cost_preference:
                preferences.append(f"Cost preference: {user_profile.cost_preference}")
            if user_profile.preferred_regions:
                preferences.append(f"Preferred regions: {', '.join(user_profile.preferred_regions)}")
            if user_profile.default_performance_tier:
                preferences.append(f"Default performance: {user_profile.default_performance_tier}")
            
            if preferences:
                prompt_parts.append("User preferences: " + "; ".join(preferences))
        
        # Add context information
        if context:
            if context.get("use_case_keywords"):
                prompt_parts.append(f"Detected keywords: {', '.join(context['use_case_keywords'])}")
            if context.get("performance_indicators"):
                indicators = context['performance_indicators']
                if indicators.get('performance'):
                    prompt_parts.append(f"Performance keywords: {', '.join(indicators['performance'])}")
                if indicators.get('cost'):
                    prompt_parts.append(f"Cost keywords: {', '.join(indicators['cost'])}")
        
        prompt_parts.append("\nProvide storage account configuration recommendation in JSON format.")
        
        return "\n".join(prompt_parts)
    
    def _parse_llm_response(self, response: str, original_input: str) -> Optional[LLMRecommendation]:
        """
        Parse and validate LLM response into structured recommendation.
        
        Args:
            response (str): Raw LLM response.
            original_input (str): Original user input for context.
            
        Returns:
            Optional[LLMRecommendation]: Parsed recommendation or None if invalid.
        """
        try:
            # Try to extract JSON from response
            json_data = self._extract_json_from_response(response)
            if not json_data:
                logger.warning("No valid JSON found in LLM response")
                return None
            
            # Validate required fields
            required_fields = ['tier', 'performance', 'replication', 'reasoning']
            for field in required_fields:
                if field not in json_data:
                    logger.warning(f"Missing required field '{field}' in LLM response")
                    return None
            
            # Validate enum values
            valid_tiers = ['Hot', 'Cool', 'Archive']
            valid_performance = ['Standard', 'Premium']
            valid_replication = ['LRS', 'GRS', 'ZRS', 'RAGRS', 'GZRS', 'RAGZRS']
            
            tier = json_data['tier']
            performance = json_data['performance']
            replication = json_data['replication']
            
            if tier not in valid_tiers:
                logger.warning(f"Invalid tier '{tier}' in LLM response")
                return None
                
            if performance not in valid_performance:
                logger.warning(f"Invalid performance '{performance}' in LLM response")
                return None
                
            if replication not in valid_replication:
                logger.warning(f"Invalid replication '{replication}' in LLM response")
                return None
            
            # Extract confidence (default to 0.7 if not provided)
            confidence = float(json_data.get('confidence', 0.7))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
            
            return LLMRecommendation(
                tier=tier,
                performance=performance,
                replication=replication,
                reasoning=json_data['reasoning'],
                confidence=confidence,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return None
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object from LLM response text.
        
        Args:
            response (str): Raw LLM response.
            
        Returns:
            Optional[Dict[str, Any]]: Parsed JSON data or None if not found.
        """
        # Try to find JSON object in response
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            return None
        
        json_str = response[start_idx:end_idx + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    def to_storage_config(self, recommendation: LLMRecommendation) -> StorageConfig:
        """
        Convert LLM recommendation to StorageConfig format.
        
        Args:
            recommendation (LLMRecommendation): LLM recommendation.
            
        Returns:
            StorageConfig: Converted storage configuration.
        """
        return StorageConfig(
            tier=recommendation.tier,
            performance=recommendation.performance,
            replication=recommendation.replication,
            reasoning=recommendation.reasoning
        )


def create_llm_advisor() -> LLMStorageAdvisor:
    """
    Factory function to create LLM storage advisor.
    
    Returns:
        LLMStorageAdvisor: Configured LLM storage advisor instance.
    """
    return LLMStorageAdvisor()