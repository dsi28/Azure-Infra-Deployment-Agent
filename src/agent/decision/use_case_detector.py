"""
Use case detection for Azure Storage Account configuration.

Analyzes user input to identify storage use cases and extract relevant
context for making intelligent configuration recommendations.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .rules import (
    get_use_case_keywords, 
    get_performance_indicators,
    get_confidence_score,
    USE_CASE_RULES
)


@dataclass 
class DetectedUseCase:
    """
    Detected use case with confidence and context.
    
    Represents the result of analyzing user input to determine
    the primary storage use case and supporting context.
    """
    primary_use_case: str
    confidence: float
    keywords_found: List[str]
    performance_indicators: Dict[str, List[str]]
    context_hints: Dict[str, Any]


class UseCaseDetector:
    """
    Detects storage use cases from user input text.
    
    Analyzes natural language input to identify the primary storage
    use case and extract relevant context for configuration decisions.
    """
    
    def __init__(self):
        """Initialize the use case detector."""
        # Compile regex patterns for better performance
        self._quantity_pattern = re.compile(r'\b(\d+)\s*(tb|gb|mb|terabyte|gigabyte|megabyte)s?\b', re.IGNORECASE)
        self._region_pattern = re.compile(r'\b(east|west|central|north|south)\s*(us|eu|asia|uk)\b', re.IGNORECASE)
        self._urgency_pattern = re.compile(r'\b(urgent|asap|immediately|quickly|soon|now)\b', re.IGNORECASE)
    
    def detect_use_case(self, user_input: str) -> DetectedUseCase:
        """
        Detect the primary storage use case from user input.
        
        Args:
            user_input (str): Natural language description of storage needs.
            
        Returns:
            DetectedUseCase: Detected use case with confidence and context.
        """
        if not user_input or not user_input.strip():
            return DetectedUseCase(
                primary_use_case="general",
                confidence=0.1,
                keywords_found=[],
                performance_indicators={"performance": [], "cost": [], "archive": []},
                context_hints={}
            )
        
        # Extract keywords and indicators
        use_case_keywords = get_use_case_keywords(user_input)
        performance_indicators = get_performance_indicators(user_input)
        
        # Determine primary use case
        primary_use_case = self._determine_primary_use_case(
            use_case_keywords, performance_indicators, user_input
        )
        
        # Calculate confidence
        confidence = get_confidence_score(use_case_keywords, user_input, performance_indicators)
        
        # Extract context hints
        context_hints = self._extract_context_hints(user_input)
        
        return DetectedUseCase(
            primary_use_case=primary_use_case,
            confidence=confidence,
            keywords_found=use_case_keywords,
            performance_indicators=performance_indicators,
            context_hints=context_hints
        )
    
    def _determine_primary_use_case(
        self, 
        use_case_keywords: List[str], 
        indicators: Dict[str, List[str]],
        user_input: str
    ) -> str:
        """
        Determine the primary use case from detected keywords and indicators.
        
        Args:
            use_case_keywords (List[str]): Detected use case keywords.
            indicators (Dict[str, List[str]]): Performance/cost/archive indicators.
            user_input (str): Original user input for additional analysis.
            
        Returns:
            str: Primary use case identifier.
        """
        if not use_case_keywords:
            # Try to infer from indicators if no direct keywords found
            if indicators["archive"]:
                return "archive"
            elif indicators["performance"] and any(word in user_input.lower() 
                                                  for word in ["database", "analytics", "cache"]):
                return "database"
            else:
                return "general"
        
        # Handle single keyword case
        if len(use_case_keywords) == 1:
            return use_case_keywords[0]
        
        # Handle multiple keywords - prioritize based on specificity and context
        return self._prioritize_use_cases(use_case_keywords, indicators, user_input)
    
    def _prioritize_use_cases(
        self, 
        keywords: List[str], 
        indicators: Dict[str, List[str]],
        user_input: str
    ) -> str:
        """
        Prioritize multiple use case keywords to determine the primary one.
        
        Args:
            keywords (List[str]): Multiple detected keywords.
            indicators (Dict[str, List[str]]): Context indicators.
            user_input (str): Original user input.
            
        Returns:
            str: Highest priority use case.
        """
        # Priority order based on specificity and common patterns
        priority_order = [
            "database", "db", "cache",  # High performance requirements
            "archive", "archival",      # Clear long-term storage intent
            "backups", "backup",        # Common enterprise use case
            "data_lake", "analytics",   # Analytics workloads
            "logs", "log",              # Operational data
            "images", "media", "video", # Content storage
            "website", "web",           # Web applications
            "documents",                # Document storage
            "staging", "development", "dev", "temp", "temporary"  # Development
        ]
        
        # Find highest priority keyword present
        for priority_keyword in priority_order:
            if priority_keyword in keywords:
                return priority_keyword
        
        # Fallback to first detected keyword
        return keywords[0]
    
    def _extract_context_hints(self, user_input: str) -> Dict[str, Any]:
        """
        Extract additional context hints from user input.
        
        Args:
            user_input (str): User input text to analyze.
            
        Returns:
            Dict[str, Any]: Context hints for configuration decisions.
        """
        hints = {}
        user_input_lower = user_input.lower()
        
        # Extract storage size hints
        size_matches = self._quantity_pattern.findall(user_input)
        if size_matches:
            # Convert to standardized format
            sizes = []
            for amount, unit in size_matches:
                amount = int(amount)
                unit_lower = unit.lower()
                if unit_lower in ['tb', 'terabyte']:
                    sizes.append(f"{amount}TB")
                elif unit_lower in ['gb', 'gigabyte']:
                    sizes.append(f"{amount}GB")
                else:
                    sizes.append(f"{amount}MB")
            hints["estimated_sizes"] = sizes
        
        # Extract region preferences
        region_matches = self._region_pattern.findall(user_input)
        if region_matches:
            hints["preferred_regions"] = [f"{direction} {location}".lower() 
                                        for direction, location in region_matches]
        
        # Extract urgency indicators
        urgency_matches = self._urgency_pattern.findall(user_input)
        if urgency_matches:
            hints["urgency"] = "high"
        
        # Check for existing storage references
        if any(phrase in user_input_lower for phrase in ["like last time", "similar to", "same as"]):
            hints["reference_previous"] = True
        
        # Check for environment indicators
        if any(env in user_input_lower for env in ["production", "prod"]):
            hints["environment"] = "production"
        elif any(env in user_input_lower for env in ["development", "dev", "test", "staging"]):
            hints["environment"] = "development"
        
        # Check for compliance requirements
        if any(term in user_input_lower for term in ["compliance", "regulation", "audit", "governance"]):
            hints["compliance_required"] = True
        
        # Check for security requirements  
        if any(term in user_input_lower for term in ["secure", "encrypted", "private", "confidential"]):
            hints["security_sensitive"] = True
        
        # Check for scalability requirements
        if any(term in user_input_lower for term in ["scale", "scalable", "growth", "expanding"]):
            hints["scalability_important"] = True
        
        return hints
    
    def get_use_case_suggestions(self, partial_input: str) -> List[str]:
        """
        Get use case suggestions for partial user input (for autocomplete/suggestions).
        
        Args:
            partial_input (str): Partial user input.
            
        Returns:
            List[str]: List of suggested use cases that match the input.
        """
        if not partial_input:
            return []
        
        partial_lower = partial_input.lower()
        suggestions = []
        
        # Find use cases that start with or contain the partial input
        for use_case in USE_CASE_RULES.keys():
            if use_case.startswith(partial_lower) or partial_lower in use_case:
                suggestions.append(use_case)
        
        # Sort by relevance (starts with first, then contains)
        starts_with = [uc for uc in suggestions if uc.startswith(partial_lower)]
        contains = [uc for uc in suggestions if not uc.startswith(partial_lower)]
        
        return starts_with + contains
    
    def analyze_text_complexity(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze the complexity and richness of user input.
        
        Args:
            user_input (str): User input to analyze.
            
        Returns:
            Dict[str, Any]: Analysis of input complexity and richness.
        """
        words = user_input.split()
        
        analysis = {
            "word_count": len(words),
            "character_count": len(user_input),
            "sentence_count": len([s for s in user_input.split('.') if s.strip()]),
            "has_technical_terms": any(term in user_input.lower() 
                                     for term in ["iops", "throughput", "latency", "ssd", "hdd"]),
            "has_business_context": any(term in user_input.lower() 
                                      for term in ["business", "customer", "client", "company"]),
            "complexity_score": min(1.0, len(words) / 20.0)  # Normalized complexity
        }
        
        return analysis


def create_use_case_detector() -> UseCaseDetector:
    """
    Factory function to create a UseCaseDetector instance.
    
    Returns:
        UseCaseDetector: Configured detector instance.
    """
    return UseCaseDetector()