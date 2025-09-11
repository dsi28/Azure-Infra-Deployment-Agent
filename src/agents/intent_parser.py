"""
Intent parsing and classification for Azure Infrastructure Agent.

This module implements keyword-based intent classification to understand user
requests for Azure resource deployment and management.
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from .base import IntentParserAgent, AgentRequest, AgentResponse
from .entities import EntityExtractor, ExtractedEntities, EntityType
from ..config.logging import get_logger
from ..config.settings import get_settings

logger = get_logger(__name__)


class Intent(Enum):
    """Enumeration of supported intents."""
    # Resource creation intents
    CREATE_STORAGE_ACCOUNT = "create_storage_account"
    CREATE_WEB_APP = "create_web_app"
    CREATE_FUNCTION_APP = "create_function_app"
    CREATE_APP_SERVICE_PLAN = "create_app_service_plan"
    CREATE_RESOURCE_GROUP = "create_resource_group"
    CREATE_VIRTUAL_NETWORK = "create_virtual_network"
    
    # Resource management intents
    LIST_RESOURCES = "list_resources"
    DELETE_RESOURCE = "delete_resource"
    UPDATE_RESOURCE = "update_resource"
    
    # Deployment intents
    DEPLOY_TEMPLATE = "deploy_template"
    VALIDATE_TEMPLATE = "validate_template"
    PREVIEW_TEMPLATE = "preview_template"
    
    # Information intents
    GET_HELP = "get_help"
    GET_STATUS = "get_status"
    GET_COSTS = "get_costs"
    
    # Conversation intents
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"


@dataclass
class IntentMatch:
    """
    Represents a matched intent with confidence score.
    
    This class contains information about a detected intent including
    the confidence level and any supporting keywords found.
    """
    intent: Intent
    confidence: float
    keywords: List[str]
    reasoning: str


class IntentClassifier:
    """
    Keyword-based intent classifier for Azure resource requests.
    
    This class uses pattern matching and keyword detection to classify
    user intents for Azure infrastructure deployment and management.
    """
    
    def __init__(self):
        """Initialize the intent classifier with predefined patterns."""
        self._initialize_patterns()
        logger.info("IntentClassifier initialized with patterns for intent recognition")
    
    def _initialize_patterns(self) -> None:
        """Initialize keyword patterns for intent classification."""
        
        # Intent patterns with keywords and weights
        self.intent_patterns = {
            Intent.CREATE_STORAGE_ACCOUNT: {
                'keywords': [
                    'storage account', 'storage', 'blob', 'blob storage',
                    'file share', 'table storage', 'queue storage'
                ],
                'actions': ['create', 'need', 'want', 'deploy', 'provision', 'set up', 'make'],
                'weight': 1.0
            },
            
            Intent.CREATE_WEB_APP: {
                'keywords': [
                    'web app', 'webapp', 'website', 'web application',
                    'app service', 'web site'
                ],
                'actions': ['create', 'need', 'want', 'deploy', 'provision', 'set up', 'make'],
                'weight': 1.0
            },
            
            Intent.CREATE_FUNCTION_APP: {
                'keywords': [
                    'function app', 'azure function', 'serverless function',
                    'lambda', 'function'
                ],
                'actions': ['create', 'need', 'want', 'deploy', 'provision', 'set up', 'make'],
                'weight': 1.0
            },
            
            Intent.CREATE_APP_SERVICE_PLAN: {
                'keywords': [
                    'app service plan', 'service plan', 'hosting plan'
                ],
                'actions': ['create', 'need', 'want', 'deploy', 'provision', 'set up', 'make'],
                'weight': 1.0
            },
            
            Intent.CREATE_RESOURCE_GROUP: {
                'keywords': [
                    'resource group', 'resource-group', 'rg'
                ],
                'actions': ['create', 'need', 'want', 'deploy', 'provision', 'set up', 'make'],
                'weight': 0.9
            },
            
            Intent.CREATE_VIRTUAL_NETWORK: {
                'keywords': [
                    'virtual network', 'vnet', 'network', 'subnet'
                ],
                'actions': ['create', 'need', 'want', 'deploy', 'provision', 'set up', 'make'],
                'weight': 1.0
            },
            
            Intent.LIST_RESOURCES: {
                'keywords': [
                    'list', 'show', 'resources', 'what do I have',
                    'inventory', 'existing'
                ],
                'actions': ['list', 'show', 'display', 'get', 'see'],
                'weight': 0.8
            },
            
            Intent.DELETE_RESOURCE: {
                'keywords': [
                    'delete', 'remove', 'destroy', 'cleanup', 'clean up'
                ],
                'actions': ['delete', 'remove', 'destroy', 'cleanup'],
                'weight': 0.9
            },
            
            Intent.DEPLOY_TEMPLATE: {
                'keywords': [
                    'deploy', 'deployment', 'template', 'arm template',
                    'bicep', 'infrastructure'
                ],
                'actions': ['deploy', 'run', 'execute', 'apply'],
                'weight': 0.9
            },
            
            Intent.VALIDATE_TEMPLATE: {
                'keywords': [
                    'validate', 'check', 'verify', 'template'
                ],
                'actions': ['validate', 'check', 'verify', 'test'],
                'weight': 0.8
            },
            
            Intent.PREVIEW_TEMPLATE: {
                'keywords': [
                    'preview', 'show', 'template', 'what will be created'
                ],
                'actions': ['preview', 'show', 'display', 'see'],
                'weight': 0.8
            },
            
            Intent.GET_HELP: {
                'keywords': [
                    'help', 'how', 'what can you do', 'commands',
                    'usage', 'guide', 'documentation'
                ],
                'actions': ['help', 'explain', 'show', 'tell me'],
                'weight': 0.7
            },
            
            Intent.GET_STATUS: {
                'keywords': [
                    'status', 'progress', 'deployment status', 'what is happening'
                ],
                'actions': ['status', 'check', 'show', 'get'],
                'weight': 0.7
            },
            
            Intent.GREETING: {
                'keywords': [
                    'hello', 'hi', 'hey', 'good morning', 'good afternoon',
                    'good evening', 'greetings'
                ],
                'actions': [],
                'weight': 0.6
            },
            
            Intent.GOODBYE: {
                'keywords': [
                    'bye', 'goodbye', 'see you', 'exit', 'quit',
                    'thank you', 'thanks', 'done'
                ],
                'actions': [],
                'weight': 0.6
            }
        }
        
        # Compile regex patterns for efficiency
        self._compiled_patterns = {}
        for intent, patterns in self.intent_patterns.items():
            self._compiled_patterns[intent] = {
                'keyword_patterns': [re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE) 
                                   for kw in patterns['keywords']],
                'action_patterns': [re.compile(r'\b' + re.escape(action) + r'\b', re.IGNORECASE) 
                                  for action in patterns['actions']],
                'weight': patterns['weight']
            }
    
    def classify_intent(self, text: str) -> List[IntentMatch]:
        """
        Classify the intent of the given text.
        
        Args:
            text (str): The input text to classify.
            
        Returns:
            List[IntentMatch]: List of matched intents sorted by confidence.
        """
        text_lower = text.lower().strip()
        matches = []
        
        # Check each intent pattern
        for intent, patterns in self._compiled_patterns.items():
            keyword_score = 0
            action_score = 0
            matched_keywords = []
            matched_actions = []
            
            # Check keyword matches
            for pattern in patterns['keyword_patterns']:
                if pattern.search(text_lower):
                    keyword_score += 1
                    matched_keywords.append(pattern.pattern.replace(r'\b', '').replace(r'\\', ''))
            
            # Check action matches
            for pattern in patterns['action_patterns']:
                if pattern.search(text_lower):
                    action_score += 1
                    matched_actions.append(pattern.pattern.replace(r'\b', '').replace(r'\\', ''))
            
            # Calculate confidence based on matches
            if keyword_score > 0 or action_score > 0:
                # Base confidence from keyword matches
                confidence = min(keyword_score * 0.4, 1.0)
                
                # Bonus for action words
                if action_score > 0 and keyword_score > 0:
                    confidence = min(confidence + action_score * 0.3, 1.0)
                elif action_score > 0:
                    confidence = min(action_score * 0.2, 0.6)
                
                # Apply intent weight
                confidence *= patterns['weight']
                
                # Special handling for greetings and goodbyes
                if intent in [Intent.GREETING, Intent.GOODBYE] and keyword_score > 0:
                    confidence = 0.8
                
                if confidence > 0.1:  # Minimum threshold
                    all_matches = matched_keywords + matched_actions
                    reasoning = f"Found keywords: {matched_keywords}" + \
                              (f", actions: {matched_actions}" if matched_actions else "")
                    
                    matches.append(IntentMatch(
                        intent=intent,
                        confidence=confidence,
                        keywords=all_matches,
                        reasoning=reasoning
                    ))
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        # If no matches found, return UNKNOWN intent
        if not matches:
            matches.append(IntentMatch(
                intent=Intent.UNKNOWN,
                confidence=0.5,
                keywords=[],
                reasoning="No recognizable intent patterns found"
            ))
        
        return matches
    
    def get_best_intent(self, text: str) -> IntentMatch:
        """
        Get the highest confidence intent match for the given text.
        
        Args:
            text (str): The input text to classify.
            
        Returns:
            IntentMatch: The best matching intent.
        """
        matches = self.classify_intent(text)
        return matches[0]


class BasicIntentParser(IntentParserAgent):
    """
    Enhanced implementation of intent parsing agent with optional OLLAMA integration.
    
    This agent combines keyword-based intent classification with optional OLLAMA
    enhancement and entity extraction to understand user requests for Azure
    infrastructure deployment. OLLAMA provides natural language understanding
    with graceful fallback to keyword-based classification.
    """
    
    def __init__(self, name: str = "BasicIntentParser", version: str = "1.0.0"):
        """
        Initialize the intent parser.
        
        Args:
            name (str): The name of the agent.
            version (str): The version of the agent.
        """
        super().__init__(name, version)
        self.classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        
        # Initialize OLLAMA classifier if available
        self.ollama_classifier = None
        self._initialize_ollama()
        
        # Add supported intents
        for intent in Intent:
            self.add_intent(intent.value)
        
        enhancement_status = "with OLLAMA enhancement" if self.ollama_classifier and self.ollama_classifier.is_available() else "keyword-based only"
        logger.info(f"BasicIntentParser initialized with {len(self.supported_intents)} supported intents ({enhancement_status})")
    
    def _initialize_ollama(self) -> None:
        """Initialize OLLAMA classifier if enabled and available."""
        try:
            settings = get_settings()
            if settings.ollama.enabled:
                from ..llm.ollama_intent_classifier import OllamaIntentClassifier, OllamaConfig
                
                # Convert settings to OllamaConfig
                config = OllamaConfig(
                    enabled=settings.ollama.enabled,
                    base_url=settings.ollama.base_url,
                    model=settings.ollama.model,
                    timeout=settings.ollama.timeout,
                    confidence_threshold=settings.ollama.confidence_threshold
                )
                
                self.ollama_classifier = OllamaIntentClassifier(config)
                
                if self.ollama_classifier.is_available():
                    logger.info("OLLAMA intent enhancement enabled and available")
                else:
                    logger.info("OLLAMA intent enhancement enabled but not available - using keyword fallback")
            else:
                logger.info("OLLAMA intent enhancement disabled in configuration")
        except Exception as e:
            logger.warning(f"Failed to initialize OLLAMA classifier: {e}. Using keyword-based classification only.")
            self.ollama_classifier = None
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process user input to extract intent and entities with OLLAMA enhancement.
        
        Args:
            request (AgentRequest): The user request to process.
            
        Returns:
            AgentResponse: Response containing detected intent and entities.
        """
        user_input = request.user_input.strip()
        
        # Log the processing
        logger.debug(f"Processing intent for input: '{user_input}'")
        
        # Try OLLAMA classification first if available
        intent_match = None
        classification_method = "keyword"
        
        if self.ollama_classifier and self.ollama_classifier.is_available():
            try:
                ollama_match = self.ollama_classifier.classify_intent(user_input)
                if ollama_match:
                    intent_match = ollama_match
                    classification_method = "OLLAMA"
                    logger.debug(f"OLLAMA classification successful: {intent_match.intent.value} "
                               f"(confidence: {intent_match.confidence:.2f})")
                else:
                    logger.debug("OLLAMA classification returned low confidence, falling back to keywords")
            except Exception as e:
                logger.warning(f"OLLAMA classification failed: {e}, falling back to keywords")
        
        # Fallback to keyword-based classification if OLLAMA didn't provide a result
        if intent_match is None:
            intent_match = self.classifier.get_best_intent(user_input)
            classification_method = "keyword"
        
        # Extract entities
        entities = self.entity_extractor.extract_entities(user_input)
        
        # Determine next action based on intent
        next_action = self._determine_next_action(intent_match, entities)
        
        # Generate response message
        response_message = self._generate_response_message(intent_match, entities)
        
        # Create response
        response = AgentResponse(
            response=response_message,
            confidence=intent_match.confidence,
            intent=intent_match.intent.value,
            entities=entities.to_dict(),
            next_action=next_action
        )
        
        logger.info(f"Detected intent: {intent_match.intent.value} "
                   f"(confidence: {intent_match.confidence:.2f}, method: {classification_method})")
        
        return response
    
    def _determine_next_action(self, intent_match: IntentMatch, entities: ExtractedEntities) -> str:
        """
        Determine the next action based on the detected intent and entities.
        
        Args:
            intent_match (IntentMatch): The matched intent.
            entities (ExtractedEntities): Extracted entities.
            
        Returns:
            str: The recommended next action.
        """
        intent = intent_match.intent
        
        if intent == Intent.CREATE_STORAGE_ACCOUNT:
            if entities.has_entity(EntityType.RESOURCE_NAME):
                return "collect_storage_parameters"
            else:
                return "collect_storage_name"
        
        elif intent == Intent.CREATE_WEB_APP:
            if entities.has_entity(EntityType.RESOURCE_NAME):
                return "collect_webapp_parameters"
            else:
                return "collect_webapp_name"
        
        elif intent == Intent.CREATE_FUNCTION_APP:
            return "collect_function_parameters"
        
        elif intent == Intent.LIST_RESOURCES:
            return "list_resources"
        
        elif intent == Intent.DELETE_RESOURCE:
            return "confirm_deletion"
        
        elif intent == Intent.DEPLOY_TEMPLATE:
            return "deploy_template"
        
        elif intent == Intent.VALIDATE_TEMPLATE:
            return "validate_template"
        
        elif intent == Intent.PREVIEW_TEMPLATE:
            return "preview_template"
        
        elif intent == Intent.GET_HELP:
            return "show_help"
        
        elif intent == Intent.GET_STATUS:
            return "show_status"
        
        elif intent == Intent.GREETING:
            return "show_welcome"
        
        elif intent == Intent.GOODBYE:
            return "end_conversation"
        
        else:
            return "clarify_intent"
    
    def _generate_response_message(self, intent_match: IntentMatch, entities: ExtractedEntities) -> str:
        """
        Generate a response message based on the detected intent and entities.
        
        Args:
            intent_match (IntentMatch): The matched intent.
            entities (ExtractedEntities): Extracted entities.
            
        Returns:
            str: The response message.
        """
        intent = intent_match.intent
        confidence = intent_match.confidence
        
        if intent == Intent.CREATE_STORAGE_ACCOUNT:
            resource_name = entities.get_entity_value(EntityType.RESOURCE_NAME)
            region = entities.get_entity_value(EntityType.REGION)
            
            message = "I'll help you create a storage account."
            if resource_name:
                message += f" I see you want to name it '{resource_name}'."
            if region:
                message += f" You want to deploy it to {region}."
            
            return message
        
        elif intent == Intent.CREATE_WEB_APP:
            resource_name = entities.get_entity_value(EntityType.RESOURCE_NAME)
            runtime = entities.get_entity_value(EntityType.RUNTIME_STACK)
            
            message = "I'll help you create a web app."
            if resource_name:
                message += f" I see you want to name it '{resource_name}'."
            if runtime:
                message += f" You want to use {runtime} as the runtime."
            
            return message
        
        elif intent == Intent.CREATE_FUNCTION_APP:
            return "I'll help you create a Function App."
        
        elif intent == Intent.LIST_RESOURCES:
            return "Let me show you your current Azure resources."
        
        elif intent == Intent.DELETE_RESOURCE:
            return "I can help you delete resources. Which resource would you like to remove?"
        
        elif intent == Intent.GET_HELP:
            return ("I can help you deploy Azure infrastructure including storage accounts, "
                   "web apps, and function apps. Just tell me what you need!")
        
        elif intent == Intent.GREETING:
            return ("Hello! I'm your Azure Infrastructure Agent. I can help you deploy "
                   "and manage Azure resources. What would you like to create today?")
        
        elif intent == Intent.GOODBYE:
            return "Thank you for using the Azure Infrastructure Agent. Have a great day!"
        
        elif intent == Intent.UNKNOWN:
            if confidence < 0.3:
                return ("I'm not sure what you'd like to do. I can help you create storage accounts, "
                       "web apps, function apps, and other Azure resources. What would you like to deploy?")
            else:
                return "Could you please clarify what you'd like to do with your Azure infrastructure?"
        
        else:
            return "I understand you want to work with Azure resources. Let me know how I can help!"


def create_intent_parser() -> BasicIntentParser:
    """
    Factory function to create a configured intent parser.
    
    Returns:
        BasicIntentParser: A configured intent parser instance.
    """
    return BasicIntentParser()