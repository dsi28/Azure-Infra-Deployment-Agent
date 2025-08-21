"""
Unit tests for agents.intent_parser module.

Tests for intent classification including IntentClassifier, BasicIntentParser,
and various intent recognition scenarios with expected use cases, edge cases, and failures.
"""

import pytest
from src.agents.intent_parser import (
    Intent,
    IntentMatch,
    IntentClassifier,
    BasicIntentParser,
    create_intent_parser
)
from src.agents.base import AgentRequest
from src.agents.entities import EntityType


class TestIntent:
    """Test cases for Intent enum."""
    
    def test_intent_values(self):
        """Test Intent enum values."""
        assert Intent.CREATE_STORAGE_ACCOUNT.value == "create_storage_account"
        assert Intent.CREATE_WEB_APP.value == "create_web_app"
        assert Intent.CREATE_FUNCTION_APP.value == "create_function_app"
        assert Intent.LIST_RESOURCES.value == "list_resources"
        assert Intent.DELETE_RESOURCE.value == "delete_resource"
        assert Intent.GET_HELP.value == "get_help"
        assert Intent.GREETING.value == "greeting"
        assert Intent.GOODBYE.value == "goodbye"
        assert Intent.UNKNOWN.value == "unknown"


class TestIntentMatch:
    """Test cases for IntentMatch dataclass."""
    
    def test_intent_match_creation(self):
        """Test IntentMatch creation."""
        match = IntentMatch(
            intent=Intent.CREATE_STORAGE_ACCOUNT,
            confidence=0.85,
            keywords=["storage", "create"],
            reasoning="Found keywords: storage, create"
        )
        
        assert match.intent == Intent.CREATE_STORAGE_ACCOUNT
        assert match.confidence == 0.85
        assert match.keywords == ["storage", "create"]
        assert match.reasoning == "Found keywords: storage, create"


class TestIntentClassifier:
    """Test cases for IntentClassifier class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.classifier = IntentClassifier()
    
    def test_intent_classifier_initialization(self):
        """Test IntentClassifier initialization."""
        classifier = IntentClassifier()
        
        assert classifier.intent_patterns is not None
        assert classifier._compiled_patterns is not None
        assert len(classifier.intent_patterns) > 0
    
    def test_classify_storage_account_intent(self):
        """Test classification of storage account creation intent."""
        text = "I need a storage account"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.CREATE_STORAGE_ACCOUNT
        assert best_match.confidence > 0.3
    
    def test_classify_web_app_intent(self):
        """Test classification of web app creation intent."""
        text = "Create a web app for my website"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.CREATE_WEB_APP
        assert best_match.confidence > 0.3
    
    def test_classify_function_app_intent(self):
        """Test classification of function app creation intent."""
        text = "I want to deploy an Azure function"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.CREATE_FUNCTION_APP
        assert best_match.confidence > 0.3
    
    def test_classify_list_resources_intent(self):
        """Test classification of list resources intent."""
        text = "Show me my current resources"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.LIST_RESOURCES
        assert best_match.confidence > 0.2
    
    def test_classify_delete_resource_intent(self):
        """Test classification of delete resource intent."""
        text = "Remove the old storage account"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        # Find delete intent in matches
        delete_matches = [m for m in matches if m.intent == Intent.DELETE_RESOURCE]
        assert len(delete_matches) > 0
        assert delete_matches[0].confidence > 0.2
    
    def test_classify_help_intent(self):
        """Test classification of help intent."""
        text = "What can you help me with?"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.GET_HELP
        assert best_match.confidence > 0.2
    
    def test_classify_greeting_intent(self):
        """Test classification of greeting intent."""
        text = "Hello there!"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.GREETING
        assert best_match.confidence > 0.5
    
    def test_classify_goodbye_intent(self):
        """Test classification of goodbye intent."""
        text = "Thanks, goodbye!"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        # Find goodbye intent in matches
        goodbye_matches = [m for m in matches if m.intent == Intent.GOODBYE]
        assert len(goodbye_matches) > 0
        assert goodbye_matches[0].confidence > 0.5
    
    def test_classify_unknown_intent(self):
        """Test classification when no clear intent is found."""
        text = "Random gibberish text with no meaning"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.UNKNOWN
        assert best_match.confidence > 0
    
    def test_get_best_intent_success(self):
        """Test getting the best intent match."""
        text = "Create a premium storage account"
        
        best_match = self.classifier.get_best_intent(text)
        
        assert best_match.intent == Intent.CREATE_STORAGE_ACCOUNT
        assert best_match.confidence > 0.3
        assert len(best_match.keywords) > 0
    
    def test_confidence_scoring_with_actions(self):
        """Test that action words boost confidence scores."""
        text1 = "storage account"  # Just keyword
        text2 = "create storage account"  # Keyword + action
        
        match1 = self.classifier.get_best_intent(text1)
        match2 = self.classifier.get_best_intent(text2)
        
        # Text with action should have higher confidence
        assert match2.confidence > match1.confidence
    
    def test_case_insensitive_classification(self):
        """Test that classification is case insensitive."""
        texts = [
            "Create a STORAGE ACCOUNT",
            "create a storage account",
            "CREATE A Storage Account"
        ]
        
        for text in texts:
            best_match = self.classifier.get_best_intent(text)
            assert best_match.intent == Intent.CREATE_STORAGE_ACCOUNT
    
    def test_multiple_intent_matches(self):
        """Test handling of text that could match multiple intents."""
        text = "Create a web app and also need storage"
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) >= 2
        
        # Should have both web app and storage account intents
        intent_types = [m.intent for m in matches]
        assert Intent.CREATE_WEB_APP in intent_types
        assert Intent.CREATE_STORAGE_ACCOUNT in intent_types
    
    def test_empty_text_edge_case(self):
        """Test classification with empty text."""
        text = ""
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.UNKNOWN
    
    def test_whitespace_text_edge_case(self):
        """Test classification with whitespace-only text."""
        text = "   \n\t   "
        
        matches = self.classifier.classify_intent(text)
        
        assert len(matches) > 0
        best_match = matches[0]
        assert best_match.intent == Intent.UNKNOWN


class TestBasicIntentParser:
    """Test cases for BasicIntentParser class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.parser = BasicIntentParser()
    
    def test_basic_intent_parser_initialization(self):
        """Test BasicIntentParser initialization."""
        parser = BasicIntentParser("TestParser", "2.0.0")
        
        assert parser.name == "TestParser"
        assert parser.version == "2.0.0"
        assert parser.classifier is not None
        assert parser.entity_extractor is not None
        assert len(parser.supported_intents) > 0
    
    def test_basic_intent_parser_default_initialization(self):
        """Test BasicIntentParser initialization with defaults."""
        parser = BasicIntentParser()
        
        assert parser.name == "BasicIntentParser"
        assert parser.version == "1.0.0"
    
    def test_process_storage_account_request(self):
        """Test processing storage account creation request."""
        request = AgentRequest(user_input="I need a storage account")
        
        response = self.parser.process(request)
        
        assert response.intent == "create_storage_account"
        assert response.confidence > 0.3
        assert "storage account" in response.response.lower()
        assert response.next_action == "collect_storage_name"
    
    def test_process_web_app_request_with_name(self):
        """Test processing web app creation request with name."""
        request = AgentRequest(user_input="Create a web app called myapp")
        
        response = self.parser.process(request)
        
        assert response.intent == "create_web_app"
        assert response.confidence > 0.3
        assert "web app" in response.response.lower()
        assert response.next_action == "collect_webapp_parameters"  # Has name
        assert "entities" in response.dict()
        assert response.entities.get("resource_name") == "myapp"
    
    def test_process_region_entity_extraction(self):
        """Test processing with region entity extraction."""
        request = AgentRequest(user_input="Deploy to East US")
        
        response = self.parser.process(request)
        
        assert "entities" in response.dict()
        assert response.entities.get("region") == "East US"
    
    def test_process_multiple_entities(self):
        """Test processing with multiple entity extraction."""
        request = AgentRequest(user_input="Create storage account called mystorage in West US with premium tier")
        
        response = self.parser.process(request)
        
        assert response.intent == "create_storage_account"
        entities = response.entities
        assert entities.get("resource_name") == "mystorage"
        assert entities.get("region") == "West US"
        assert entities.get("performance_tier") == "Premium"
    
    def test_process_greeting_request(self):
        """Test processing greeting request."""
        request = AgentRequest(user_input="Hello!")
        
        response = self.parser.process(request)
        
        assert response.intent == "greeting"
        assert response.confidence > 0.5
        assert response.next_action == "show_welcome"
        assert "hello" in response.response.lower() or "azure" in response.response.lower()
    
    def test_process_help_request(self):
        """Test processing help request."""
        request = AgentRequest(user_input="What can you help me with?")
        
        response = self.parser.process(request)
        
        assert response.intent == "get_help"
        assert response.next_action == "show_help"
        assert "help" in response.response.lower() or "storage" in response.response.lower()
    
    def test_process_goodbye_request(self):
        """Test processing goodbye request."""
        request = AgentRequest(user_input="Thanks, goodbye!")
        
        response = self.parser.process(request)
        
        assert response.intent == "goodbye"
        assert response.next_action == "end_conversation"
        assert "thank" in response.response.lower() or "day" in response.response.lower()
    
    def test_process_unknown_request(self):
        """Test processing unknown/unclear request."""
        request = AgentRequest(user_input="Random unclear text")
        
        response = self.parser.process(request)
        
        # Should either be unknown or have low confidence
        if response.intent == "unknown":
            assert response.next_action == "clarify_intent"
        else:
            assert response.confidence < 0.5
    
    def test_determine_next_action_storage_with_name(self):
        """Test next action determination for storage account with name."""
        request = AgentRequest(user_input="Create storage account called teststore")
        
        response = self.parser.process(request)
        
        assert response.next_action == "collect_storage_parameters"
    
    def test_determine_next_action_storage_without_name(self):
        """Test next action determination for storage account without name."""
        request = AgentRequest(user_input="I need a storage account")
        
        response = self.parser.process(request)
        
        assert response.next_action == "collect_storage_name"
    
    def test_determine_next_action_web_app_with_name(self):
        """Test next action determination for web app with name."""
        request = AgentRequest(user_input="Create web app called testapp")
        
        response = self.parser.process(request)
        
        assert response.next_action == "collect_webapp_parameters"
    
    def test_determine_next_action_web_app_without_name(self):
        """Test next action determination for web app without name."""
        request = AgentRequest(user_input="I want to create a web application")
        
        response = self.parser.process(request)
        
        assert response.next_action == "collect_webapp_name"
    
    def test_response_message_generation(self):
        """Test response message generation for different intents."""
        test_cases = [
            ("Create storage called mystorage", "mystorage"),
            ("Create web app named myapp", "myapp"),
            ("Deploy storage in East US", "East US"),
            ("Create Node.js web app", "NODE")
        ]
        
        for text, expected_entity in test_cases:
            request = AgentRequest(user_input=text)
            response = self.parser.process(request)
            
            # Response should mention the detected entity
            assert expected_entity.lower() in response.response.lower() or \
                   expected_entity in response.response, f"Failed for: {text}"
    
    def test_context_preservation(self):
        """Test that request context is preserved."""
        context = {"session_id": "test123", "user_id": "user456"}
        request = AgentRequest(
            user_input="Create a storage account",
            context=context,
            session_id="test123"
        )
        
        response = self.parser.process(request)
        
        # Response should be generated successfully regardless of context
        assert response.intent is not None
        assert response.response is not None


class TestCreateIntentParser:
    """Test cases for create_intent_parser factory function."""
    
    def test_create_intent_parser_success(self):
        """Test successful intent parser creation."""
        parser = create_intent_parser()
        
        assert isinstance(parser, BasicIntentParser)
        assert parser.name == "BasicIntentParser"
        assert parser.version == "1.0.0"
        assert parser.classifier is not None
        assert parser.entity_extractor is not None


class TestIntentParserIntegration:
    """Integration tests for intent parser functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.parser = BasicIntentParser()
    
    def test_task_test_case_storage_account(self):
        """Test the specific test case from TASK.md: 'I need a storage account' → storage_account intent."""
        request = AgentRequest(user_input="I need a storage account")
        
        response = self.parser.process(request)
        
        assert response.intent == "create_storage_account"
        assert response.confidence > 0.3
    
    def test_task_test_case_web_app_with_name(self):
        """Test the specific test case from TASK.md: 'Create a web app called myapp' → web_app intent + name entity."""
        request = AgentRequest(user_input="Create a web app called myapp")
        
        response = self.parser.process(request)
        
        assert response.intent == "create_web_app"
        assert response.entities.get("resource_name") == "myapp"
        assert response.confidence > 0.3
    
    def test_task_test_case_region_entity(self):
        """Test the specific test case from TASK.md: 'Deploy to East US' → region entity."""
        request = AgentRequest(user_input="Deploy to East US")
        
        response = self.parser.process(request)
        
        assert response.entities.get("region") == "East US"
    
    def test_real_world_complex_request(self):
        """Test a complex real-world request with multiple intents and entities."""
        request = AgentRequest(
            user_input="Hello! I want to create a premium storage account called companydata in East US with GRS replication"
        )
        
        response = self.parser.process(request)
        
        # Should prioritize the main intent (storage creation over greeting)
        assert response.intent in ["create_storage_account", "greeting"]
        
        # Should extract multiple entities regardless of intent
        entities = response.entities
        if entities.get("resource_name"):
            assert entities.get("resource_name") == "companydata"
        if entities.get("region"):
            assert entities.get("region") == "East US"
        if entities.get("performance_tier"):
            assert entities.get("performance_tier") == "Premium"
        if entities.get("replication_type"):
            assert entities.get("replication_type") == "GRS"
    
    def test_error_handling_malformed_input(self):
        """Test error handling with malformed input."""
        malformed_inputs = [
            None,  # Will be converted to string by Pydantic
            "",
            "   ",
            "\n\t\r",
            "!@#$%^&*()",
        ]
        
        for malformed_input in malformed_inputs:
            try:
                if malformed_input is None:
                    # Skip None test as Pydantic will handle it
                    continue
                    
                request = AgentRequest(user_input=malformed_input)
                response = self.parser.process(request)
                
                # Should handle gracefully
                assert response.intent is not None
                assert response.response is not None
                assert isinstance(response.confidence, float)
                
            except Exception as e:
                pytest.fail(f"Parser failed on input '{malformed_input}': {e}")
    
    def test_performance_multiple_requests(self):
        """Test performance with multiple sequential requests."""
        test_requests = [
            "Create a storage account",
            "I need a web app called testapp",
            "Deploy to West US",
            "Show me my resources",
            "Delete old storage",
            "Help me with Azure",
            "Hello there",
            "Thank you, goodbye"
        ]
        
        responses = []
        for text in test_requests:
            request = AgentRequest(user_input=text)
            response = self.parser.process(request)
            responses.append(response)
        
        # All requests should be processed successfully
        assert len(responses) == len(test_requests)
        
        for i, response in enumerate(responses):
            assert response.intent is not None, f"Failed on request {i}: {test_requests[i]}"
            assert response.response is not None, f"No response for request {i}: {test_requests[i]}"
            assert isinstance(response.confidence, float), f"Invalid confidence for request {i}: {test_requests[i]}"