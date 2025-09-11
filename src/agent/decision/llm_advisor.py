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
        return """You are an Azure Storage expert. You must analyze user storage requirements and provide ONE recommendation.

CRITICAL: Your response must be ONLY valid JSON. No additional text before or after the JSON.

AZURE STORAGE OPTIONS:

Access Tiers (choose exactly one):
- Hot: For frequently accessed data (daily/weekly). Higher storage cost, lower access cost.
- Cool: For infrequently accessed data (monthly). Lower storage cost, higher access cost.
- Archive: For rarely accessed data (yearly). Lowest storage cost, highest access cost.

Performance Tiers (choose exactly one):
- Standard: General purpose, cost-effective for most workloads
- Premium: High performance SSD-based storage for demanding applications

Replication Types (choose exactly one):
- LRS: Locally redundant, 3 copies in same region (lowest cost)
- GRS: Geo-redundant, 6 copies across 2 regions (disaster recovery)
- ZRS: Zone-redundant, 3 copies across availability zones (high availability)
- RAGRS: Read-access geo-redundant (GRS + read access to secondary)
- GZRS: Geo-zone-redundant (combines ZRS and GRS)
- RAGZRS: Read-access geo-zone-redundant (GZRS + read access)

COMMON SCENARIOS:
1. Website images/media → Hot + Standard + LRS
2. Application data (high traffic) → Hot + Premium + ZRS
3. Database backups → Cool + Standard + GRS
4. Archive/compliance data → Archive + Standard + GRS
5. Development/testing → Hot + Standard + LRS
6. Data analytics → Cool + Premium + ZRS

EXAMPLE USER REQUESTS AND RESPONSES:
Request: "storage for website images"
Response: {"tier": "Hot", "performance": "Standard", "replication": "LRS", "reasoning": "Website images need fast access (Hot tier), standard performance is cost-effective, and LRS provides sufficient durability for non-critical assets", "confidence": 0.9}

Request: "backup storage that should survive datacenter failure"
Response: {"tier": "Cool", "performance": "Standard", "replication": "GRS", "reasoning": "Backups are accessed infrequently (Cool tier), standard performance is sufficient, and GRS provides disaster recovery across regions", "confidence": 0.9}

Request: "old data I don't access often, stored in multiple datacenters same region"
Response: {"tier": "Cool", "performance": "Standard", "replication": "ZRS", "reasoning": "Infrequently accessed data suits Cool tier, standard performance is sufficient, and ZRS provides redundancy across availability zones within the same region", "confidence": 0.9}

IMPORTANT RULES:
1. Response must be ONLY valid JSON - no additional text
2. Choose exactly one value for each field - no alternatives or pipe symbols
3. All field names must be lowercase: "tier", "performance", "replication", "reasoning", "confidence"
4. Confidence must be a number between 0.0 and 1.0
5. Reasoning should be one clear sentence explaining the choice

Your response must match this exact format:
{"tier": "Hot", "performance": "Standard", "replication": "LRS", "reasoning": "Brief explanation", "confidence": 0.8}"""

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
        
        prompt_parts.append("\nIMPORTANT: Respond with ONLY valid JSON using this exact format:")
        prompt_parts.append('{"tier": "Hot|Cool|Archive", "performance": "Standard|Premium", "replication": "LRS|GRS|ZRS|RAGRS|GZRS|RAGZRS", "reasoning": "explanation", "confidence": 0.8}')
        prompt_parts.append("\nNo additional text. Only the JSON response.")
        
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
            
            # Validate enum values with fallback for pipe-separated values
            valid_tiers = ['Hot', 'Cool', 'Archive']
            valid_performance = ['Standard', 'Premium']
            valid_replication = ['LRS', 'GRS', 'ZRS', 'RAGRS', 'GZRS', 'RAGZRS']
            
            tier = json_data['tier'].strip()
            performance = json_data['performance'].strip()
            replication = json_data['replication'].strip()
            
            # Handle pipe-separated values by taking the first valid option
            if '|' in tier:
                tier_options = [t.strip() for t in tier.split('|')]
                tier = next((t for t in tier_options if t in valid_tiers), tier_options[0])
                logger.warning(f"LLM returned multiple tiers '{json_data['tier']}', using '{tier}'")
            
            if '|' in performance:
                perf_options = [p.strip() for p in performance.split('|')]
                performance = next((p for p in perf_options if p in valid_performance), perf_options[0])
                logger.warning(f"LLM returned multiple performance options '{json_data['performance']}', using '{performance}'")
            
            if '|' in replication:
                repl_options = [r.strip() for r in replication.split('|')]
                replication = next((r for r in repl_options if r in valid_replication), repl_options[0])
                logger.warning(f"LLM returned multiple replication options '{json_data['replication']}', using '{replication}'")
            
            # Final validation
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
        Extract JSON object from LLM response text with improved error handling.
        
        Args:
            response (str): Raw LLM response.
            
        Returns:
            Optional[Dict[str, Any]]: Parsed JSON data or None if not found.
        """
        # Clean up the response
        response = response.strip()
        
        # Try to find JSON object in response
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            logger.warning(f"No JSON braces found in LLM response: {response[:100]}...")
            return None
        
        json_str = response[start_idx:end_idx + 1]
        
        try:
            # First attempt - direct parsing
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"First JSON parse failed: {e}")
            
            # Second attempt - clean up common LLM formatting issues
            try:
                # Fix common issues with LLM responses
                cleaned = json_str.replace('\n', ' ').replace('\t', ' ')
                # Remove extra spaces
                import re
                cleaned = re.sub(r'\s+', ' ', cleaned)
                # Fix quotes issues
                cleaned = cleaned.replace("'", '"')
                
                return json.loads(cleaned)
            except json.JSONDecodeError as e2:
                logger.warning(f"Second JSON parse failed: {e2}")
                logger.warning(f"Problematic JSON string: {json_str}")
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