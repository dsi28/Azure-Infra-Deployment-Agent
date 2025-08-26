"""
Storage-specific prompts for the Azure Storage Agent.

Contains system prompts and templates for understanding storage account
requests and generating appropriate responses.
"""

from typing import Dict, Any


# System prompt for storage agent
STORAGE_AGENT_SYSTEM_PROMPT = """You are an Azure Storage Account specialist assistant. Your role is to help users create and configure Azure Storage Accounts through natural conversation.

Key responsibilities:
1. Understand user's storage needs and use cases
2. Suggest appropriate storage account configurations
3. Ask clarifying questions when requirements are unclear
4. Provide brief, helpful explanations for your suggestions

Storage account configuration options:
- Performance Tiers: Standard (cost-effective), Premium (high-performance)
- Access Tiers: Hot (frequently accessed), Cool (infrequently accessed), Archive (rarely accessed)
- Replication: LRS (locally redundant), GRS (geo-redundant), ZRS (zone-redundant)
- Account Kind: StorageV2 (general purpose v2) - default for most cases

Common use cases and recommendations:
- Website/app assets: Hot tier, Standard performance, LRS replication
- Images/media: Hot tier, Standard performance, LRS or ZRS replication
- Backups: Cool tier, Standard performance, GRS replication
- Logs/analytics: Cool tier, Standard performance, LRS replication
- Archive/compliance: Archive tier, Standard performance, GRS replication
- High-performance databases: Premium performance, ZRS replication

Always be concise and focus on storage accounts only. Don't suggest other Azure resources."""


# Template for extracting storage requirements
EXTRACT_REQUIREMENTS_PROMPT = """Based on this user request, extract the storage account requirements:

User request: "{user_input}"

Identify:
1. Use case/purpose (if mentioned)
2. Performance needs (high-performance, cost-effective, or not specified)
3. Access frequency (frequent, occasional, rare, or not specified)
4. Durability needs (local redundancy OK, need geo-redundancy, or not specified)
5. Any specific preferences (region, naming, etc.)

Respond in JSON format:
{{
    "use_case": "description of intended use",
    "performance_needs": "high-performance|cost-effective|not_specified",
    "access_frequency": "frequent|occasional|rare|not_specified", 
    "durability_needs": "local|geo|not_specified",
    "preferences": {{
        "region": "region if mentioned or null",
        "name_suggestion": "suggested name or null"
    }}
}}"""


# Template for configuration suggestions
SUGGEST_CONFIG_PROMPT = """Based on these storage requirements, suggest the best Azure Storage Account configuration:

Requirements: {requirements}
User preferences: {user_preferences}

Provide configuration suggestion in JSON format:
{{
    "performance_tier": "Standard|Premium",
    "access_tier": "Hot|Cool|Archive", 
    "replication_type": "LRS|GRS|ZRS",
    "account_kind": "StorageV2",
    "reasoning": "Brief explanation of why these settings are recommended"
}}"""


# Template for conversational response
CONVERSATIONAL_RESPONSE_PROMPT = """Generate a natural, conversational response about this Azure Storage Account configuration:

Configuration: {configuration}
User context: {context}

Create a response that:
1. Acknowledges the user's request
2. Presents the configuration in a friendly, understandable way
3. Briefly explains why these settings are good for their use case
4. Asks for confirmation to proceed

Keep the response concise (2-3 sentences) and conversational."""


def format_extract_requirements_prompt(user_input: str) -> str:
    """
    Format the requirements extraction prompt with user input.
    
    Args:
        user_input (str): User's storage request.
        
    Returns:
        str: Formatted prompt for LLM.
    """
    return EXTRACT_REQUIREMENTS_PROMPT.format(user_input=user_input)


def format_suggest_config_prompt(requirements: Dict[str, Any], user_preferences: Dict[str, Any]) -> str:
    """
    Format the configuration suggestion prompt.
    
    Args:
        requirements (Dict): Extracted storage requirements.
        user_preferences (Dict): User's stored preferences.
        
    Returns:
        str: Formatted prompt for LLM.
    """
    return SUGGEST_CONFIG_PROMPT.format(
        requirements=requirements,
        user_preferences=user_preferences
    )


def format_conversational_response_prompt(configuration: Dict[str, Any], context: Dict[str, Any]) -> str:
    """
    Format the conversational response prompt.
    
    Args:
        configuration (Dict): Suggested storage configuration.
        context (Dict): User context and preferences.
        
    Returns:
        str: Formatted prompt for LLM.
    """
    return CONVERSATIONAL_RESPONSE_PROMPT.format(
        configuration=configuration,
        context=context
    )