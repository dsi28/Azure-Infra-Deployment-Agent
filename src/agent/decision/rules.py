"""
Simple decision rules for Azure Storage Account configuration.

Contains rule-based logic for determining appropriate storage configurations
based on use cases and user preferences.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class StorageConfig:
    """
    Storage configuration recommendation.
    
    Represents a complete storage account configuration with
    performance tier, access tier, and replication settings.
    """
    tier: str  # Hot, Cool, Archive
    performance: str  # Standard, Premium
    replication: str  # LRS, GRS, ZRS
    reasoning: str  # Human-readable explanation


# Core decision rules based on use case keywords
USE_CASE_RULES = {
    "images": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Images need fast access for web display, standard performance is cost-effective, local redundancy sufficient for most image use cases"
    },
    "website": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Website assets require fast access for good user experience, standard performance balances cost and speed"
    },
    "web": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Web content needs immediate availability, standard performance is adequate for most web workloads"
    },
    "backups": {
        "tier": "Cool", 
        "performance": "Standard", 
        "replication": "GRS",
        "reasoning": "Backups are accessed infrequently but need geographic redundancy for disaster recovery"
    },
    "backup": {
        "tier": "Cool", 
        "performance": "Standard", 
        "replication": "GRS",
        "reasoning": "Backup data should be stored cost-effectively with geographic protection against disasters"
    },
    "logs": {
        "tier": "Cool", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Log files are accessed occasionally for analysis, cool tier reduces storage costs significantly"
    },
    "log": {
        "tier": "Cool", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Log storage prioritizes cost efficiency over access speed"
    },
    "archive": {
        "tier": "Archive", 
        "performance": "Standard", 
        "replication": "GRS",
        "reasoning": "Archive data is rarely accessed, requires maximum cost savings and geographic redundancy for compliance"
    },
    "archival": {
        "tier": "Archive", 
        "performance": "Standard", 
        "replication": "GRS",
        "reasoning": "Long-term archival storage optimizes for lowest cost with disaster recovery protection"
    },
    "data_lake": {
        "tier": "Cool", 
        "performance": "Premium", 
        "replication": "ZRS",
        "reasoning": "Data lake workloads need high performance for analytics with zone redundancy for availability"
    },
    "analytics": {
        "tier": "Cool", 
        "performance": "Premium", 
        "replication": "ZRS",
        "reasoning": "Analytics workloads require high IOPS and zone redundancy for continuous availability"
    },
    "database": {
        "tier": "Hot", 
        "performance": "Premium", 
        "replication": "ZRS",
        "reasoning": "Database storage demands high performance and zone redundancy for maximum uptime"
    },
    "db": {
        "tier": "Hot", 
        "performance": "Premium", 
        "replication": "ZRS",
        "reasoning": "Database workloads need premium performance with zone-level fault tolerance"
    },
    "media": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Media files need fast access for streaming, standard performance handles most media workloads"
    },
    "video": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Video content requires immediate access for playback, standard performance is usually sufficient"
    },
    "documents": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Document storage needs quick access, standard performance balances cost and responsiveness"
    },
    "temp": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Temporary storage prioritizes access speed over redundancy, local replication reduces costs"
    },
    "temporary": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Temporary files need fast access, minimal redundancy acceptable for short-term storage"
    },
    "cache": {
        "tier": "Hot", 
        "performance": "Premium", 
        "replication": "LRS",
        "reasoning": "Cache storage requires maximum performance for quick data retrieval, local redundancy sufficient"
    },
    "staging": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Staging environments need responsive storage, local redundancy adequate for non-production use"
    },
    "development": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Development storage balances performance and cost, local redundancy suitable for dev environments"
    },
    "dev": {
        "tier": "Hot", 
        "performance": "Standard", 
        "replication": "LRS",
        "reasoning": "Dev environments optimize for cost-effectiveness while maintaining reasonable performance"
    }
}

# Cost preference modifiers
COST_PREFERENCE_MODIFIERS = {
    "optimized": {
        "tier_adjustment": {"Hot": "Cool", "Cool": "Archive"},  # Prefer cheaper tiers
        "performance_adjustment": {"Premium": "Standard"},  # Prefer standard performance
        "replication_adjustment": {"GRS": "LRS", "ZRS": "LRS"}  # Prefer local redundancy
    },
    "balanced": {
        "tier_adjustment": {},  # No adjustments for balanced
        "performance_adjustment": {},
        "replication_adjustment": {}
    },
    "performance": {
        "tier_adjustment": {"Cool": "Hot", "Archive": "Cool"},  # Prefer faster tiers
        "performance_adjustment": {"Standard": "Premium"},  # Prefer premium performance
        "replication_adjustment": {"LRS": "ZRS"}  # Prefer zone redundancy
    }
}

# Performance keywords that suggest Premium tier
PERFORMANCE_KEYWORDS = [
    "fast", "high-performance", "performance", "speed", "quick", 
    "database", "analytics", "cache", "iops", "throughput"
]

# Cost keywords that suggest cost optimization
COST_KEYWORDS = [
    "cheap", "cost-effective", "budget", "affordable", "economical",
    "inexpensive", "cost-optimized", "save money", "minimize cost"
]

# Archive keywords that suggest Archive tier
ARCHIVE_KEYWORDS = [
    "archive", "archival", "long-term", "compliance", "retention",
    "rarely accessed", "cold storage", "infrequent"
]


def get_use_case_keywords(text: str) -> List[str]:
    """
    Extract relevant use case keywords from user input.
    
    Args:
        text (str): User input text to analyze.
        
    Returns:
        List[str]: List of detected use case keywords.
    """
    text_lower = text.lower()
    detected_keywords = []
    
    for keyword in USE_CASE_RULES.keys():
        if keyword in text_lower:
            detected_keywords.append(keyword)
    
    return detected_keywords


def get_performance_indicators(text: str) -> Dict[str, List[str]]:
    """
    Detect performance, cost, and archive indicators in user input.
    
    Args:
        text (str): User input text to analyze.
        
    Returns:
        Dict[str, List[str]]: Dictionary with performance, cost, and archive keywords found.
    """
    text_lower = text.lower()
    indicators = {
        "performance": [],
        "cost": [],
        "archive": []
    }
    
    for keyword in PERFORMANCE_KEYWORDS:
        if keyword in text_lower:
            indicators["performance"].append(keyword)
    
    for keyword in COST_KEYWORDS:
        if keyword in text_lower:
            indicators["cost"].append(keyword)
    
    for keyword in ARCHIVE_KEYWORDS:
        if keyword in text_lower:
            indicators["archive"].append(keyword)
    
    return indicators


def apply_cost_preference(config: Dict[str, str], cost_preference: str) -> Dict[str, str]:
    """
    Modify storage configuration based on cost preference.
    
    Args:
        config (Dict[str, str]): Original storage configuration.
        cost_preference (str): User's cost preference (optimized, balanced, performance).
        
    Returns:
        Dict[str, str]: Modified configuration based on cost preference.
    """
    if cost_preference not in COST_PREFERENCE_MODIFIERS:
        return config
    
    modifiers = COST_PREFERENCE_MODIFIERS[cost_preference]
    modified_config = config.copy()
    
    # Apply tier adjustment
    if config["tier"] in modifiers["tier_adjustment"]:
        modified_config["tier"] = modifiers["tier_adjustment"][config["tier"]]
    
    # Apply performance adjustment
    if config["performance"] in modifiers["performance_adjustment"]:
        modified_config["performance"] = modifiers["performance_adjustment"][config["performance"]]
    
    # Apply replication adjustment
    if config["replication"] in modifiers["replication_adjustment"]:
        modified_config["replication"] = modifiers["replication_adjustment"][config["replication"]]
    
    return modified_config


def generate_reasoning(
    original_config: Dict[str, str], 
    final_config: Dict[str, str], 
    use_case: str,
    cost_preference: str,
    indicators: Dict[str, List[str]]
) -> str:
    """
    Generate human-readable reasoning for configuration choice.
    
    Args:
        original_config (Dict[str, str]): Original use case configuration.
        final_config (Dict[str, str]): Final recommended configuration.
        use_case (str): Primary use case detected.
        cost_preference (str): User's cost preference.
        indicators (Dict[str, List[str]]): Performance/cost indicators found.
        
    Returns:
        str: Human-readable explanation of the configuration choice.
    """
    base_reasoning = USE_CASE_RULES.get(use_case, {}).get("reasoning", "")
    modifications = []
    
    # Check if configuration was modified from original
    if original_config["tier"] != final_config["tier"]:
        if cost_preference == "optimized":
            modifications.append(f"switched to {final_config['tier']} tier for cost savings")
        elif cost_preference == "performance":
            modifications.append(f"upgraded to {final_config['tier']} tier for better performance")
    
    if original_config["performance"] != final_config["performance"]:
        if final_config["performance"] == "Premium":
            modifications.append("upgraded to Premium performance for higher throughput")
        else:
            modifications.append("using Standard performance for cost efficiency")
    
    if original_config["replication"] != final_config["replication"]:
        if final_config["replication"] == "LRS":
            modifications.append("using local redundancy to minimize costs")
        elif final_config["replication"] == "ZRS":
            modifications.append("using zone redundancy for better availability")
    
    # Add context from detected keywords
    if indicators["cost"]:
        modifications.append("optimizing for cost based on budget requirements")
    elif indicators["performance"]:
        modifications.append("prioritizing performance based on speed requirements")
    elif indicators["archive"]:
        modifications.append("configured for long-term archival storage")
    
    if modifications:
        reasoning = base_reasoning + ". Additionally, " + ", ".join(modifications)
    else:
        reasoning = base_reasoning
    
    return reasoning


def get_confidence_score(
    use_case_keywords: List[str], 
    text: str, 
    indicators: Dict[str, List[str]]
) -> float:
    """
    Calculate confidence score for the storage configuration decision.
    
    Args:
        use_case_keywords (List[str]): Detected use case keywords.
        text (str): Original user input.
        indicators (Dict[str, List[str]]): Performance/cost indicators.
        
    Returns:
        float: Confidence score between 0.0 and 1.0.
    """
    base_confidence = 0.3  # Base confidence for any text input
    
    # Add confidence for detected use cases
    if use_case_keywords:
        base_confidence += 0.4  # Strong boost for known use cases
        
        # Extra confidence for multiple related keywords
        if len(use_case_keywords) > 1:
            base_confidence += 0.1
    
    # Add confidence for specific indicators
    total_indicators = sum(len(keywords) for keywords in indicators.values())
    if total_indicators > 0:
        base_confidence += min(0.2, total_indicators * 0.05)  # Up to 0.2 boost
    
    # Add confidence for text length (more context usually means better understanding)
    word_count = len(text.split())
    if word_count >= 5:
        base_confidence += 0.05
    if word_count >= 10:
        base_confidence += 0.05
    
    # Cap at 1.0
    return min(1.0, base_confidence)