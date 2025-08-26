"""
Test scenarios for storage agent functionality.

Tests the main user scenarios outlined in TASK-AGENT.md to ensure
agent provides appropriate responses and configurations.
"""

import pytest
from unittest.mock import Mock, patch
from src.agent.core.simple_agent import SimpleAgent, AgentResponse
from src.agent.conversation.storage_conversation import StorageConversation, ConversationState
from src.agent.decision.storage_advisor import StorageRecommendation
from src.agent.decision.rules import StorageConfig


class TestStorageAgentScenarios:
    """Test main storage agent scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock dependencies to avoid external service calls
        self.mock_llm = Mock()
        self.mock_profile = Mock()
        self.mock_advisor = Mock()
        
        # Setup common mock returns
        self.mock_llm.is_available.return_value = True
        self.mock_profile.get_context_for_conversation.return_value = {
            "user_preferences": {
                "cost_preference": "optimized",
                "default_performance_tier": "Standard",
                "preferred_regions": ["eastus"]
            }
        }
        self.mock_profile.suggest_storage_name.return_value = "test-storage-001"
        
        # Create agent with mocked dependencies
        self.agent = SimpleAgent(
            llm_client=self.mock_llm,
            user_profile=self.mock_profile,
            storage_advisor=self.mock_advisor
        )
    
    def _create_mock_recommendation(self, use_case: str = "general", confidence: float = 0.85):
        """Helper to create mock storage recommendation."""
        config = StorageConfig(
            performance="Standard",
            tier="Hot",
            replication="LRS",
            reasoning=f"Optimized for {use_case} storage needs"
        )
        return StorageRecommendation(
            configuration=config,
            detected_use_case=use_case,
            confidence=confidence,
            alternative_configs=[],
            context_used={"detected_keywords": [use_case]},
            suggestion_id=f"test_{use_case}_001"
        )
    
    def test_basic_storage_request(self):
        """Test: 'I need a storage account'"""
        # Setup
        recommendation = self._create_mock_recommendation("general")
        self.mock_advisor.recommend_configuration.return_value = recommendation
        self.mock_llm.generate.return_value = Mock(
            success=True,
            content="I'll help you create a general storage account."
        )
        
        # Execute
        response = self.agent.process_message("I need a storage account")
        
        # Verify
        assert response.success
        assert response.recommendation is not None
        assert response.requires_confirmation
        assert "Standard" in response.message
        assert "test-storage-001" in response.message
        
        # Verify calls
        self.mock_advisor.recommend_configuration.assert_called_once()
        self.mock_profile.suggest_storage_name.assert_called_once()
    
    def test_use_case_specific_images(self):
        """Test: 'I need storage for my website images'"""
        # Setup
        recommendation = self._create_mock_recommendation("images", 0.90)
        recommendation.configuration.tier = "Hot"
        self.mock_advisor.recommend_configuration.return_value = recommendation
        self.mock_llm.generate.return_value = Mock(
            success=True,
            content="Perfect for website images! I'll set up fast, accessible storage."
        )
        
        # Execute
        response = self.agent.process_message("I need storage for my website images")
        
        # Verify
        assert response.success
        assert response.recommendation.detected_use_case == "images"
        assert response.recommendation.configuration.tier == "Hot"
        assert response.recommendation.confidence == 0.90
        assert "images" in response.message.lower()
        
    def test_cost_conscious_request(self):
        """Test: 'I need cheap storage for backups'"""
        # Setup  
        recommendation = self._create_mock_recommendation("backups", 0.88)
        recommendation.configuration.tier = "Cool"
        recommendation.configuration.replication = "GRS"
        self.mock_advisor.recommend_configuration.return_value = recommendation
        self.mock_llm.generate.return_value = Mock(
            success=True,
            content="For cost-effective backups, I recommend Cool tier storage."
        )
        
        # Execute
        response = self.agent.process_message("I need cheap storage for backups")
        
        # Verify
        assert response.success
        assert response.recommendation.detected_use_case == "backups"
        assert response.recommendation.configuration.tier == "Cool"
        assert response.recommendation.configuration.replication == "GRS"
        assert "cool" in response.message.lower() or "cost" in response.message.lower()
    
    def test_performance_focused_request(self):
        """Test: 'I need fast storage for a database'"""
        # Setup
        recommendation = self._create_mock_recommendation("database", 0.85)
        recommendation.configuration.performance = "Premium"
        recommendation.configuration.tier = "Hot" 
        self.mock_advisor.recommend_configuration.return_value = recommendation
        self.mock_llm.generate.return_value = Mock(
            success=True,
            content="For database performance, Premium storage is recommended."
        )
        
        # Execute
        response = self.agent.process_message("I need fast storage for a database")
        
        # Verify
        assert response.success
        assert response.recommendation.detected_use_case == "database"
        assert response.recommendation.configuration.performance == "Premium"
        assert "premium" in response.message.lower() or "performance" in response.message.lower()
    
    def test_context_aware_request(self):
        """Test: 'Create another storage account like the last one'"""
        # Setup - simulate previous recommendation
        self.agent.last_recommendation = self._create_mock_recommendation("images")
        
        recommendation = self._create_mock_recommendation("images", 0.92)
        self.mock_advisor.recommend_configuration.return_value = recommendation
        self.mock_llm.generate.return_value = Mock(
            success=True,
            content="I'll create similar storage based on your previous setup."
        )
        
        # Execute
        response = self.agent.process_message("Create another storage account like the last one")
        
        # Verify
        assert response.success
        assert response.recommendation is not None
        assert "similar" in response.message.lower() or "like" in response.message.lower()
    
    def test_confirmation_response(self):
        """Test user confirmation: 'yes'"""
        # Setup - agent has pending recommendation
        self.agent.last_recommendation = self._create_mock_recommendation("images")
        
        # Execute
        response = self.agent.process_message("yes")
        
        # Verify
        assert response.success
        assert not response.requires_confirmation  # Confirmation complete
        assert "perfect" in response.message.lower() or "prepare" in response.message.lower()
        
        # Verify deployment history recorded
        self.mock_profile.add_deployment_history.assert_called_once()
        
    def test_modification_request_cheaper(self):
        """Test modification: 'make it cheaper'"""
        # Setup
        self.agent.last_recommendation = self._create_mock_recommendation("images")
        
        # Mock modified preferences and new recommendation  
        modified_recommendation = self._create_mock_recommendation("images", 0.80)
        modified_recommendation.configuration.tier = "Cool"
        self.mock_advisor.recommend_configuration.return_value = modified_recommendation
        
        # Execute
        response = self.agent.process_message("make it cheaper")
        
        # Verify
        assert response.success
        assert response.requires_confirmation
        assert "cost" in response.message.lower() or "cheaper" in response.message.lower()
        assert response.recommendation.configuration.tier == "Cool"
    
    def test_modification_request_faster(self):
        """Test modification: 'make it faster'"""
        # Setup
        self.agent.last_recommendation = self._create_mock_recommendation("general")
        
        # Mock performance-optimized recommendation
        modified_recommendation = self._create_mock_recommendation("general", 0.82)
        modified_recommendation.configuration.performance = "Premium"
        self.mock_advisor.recommend_configuration.return_value = modified_recommendation
        
        # Execute  
        response = self.agent.process_message("make it faster")
        
        # Verify
        assert response.success
        assert response.requires_confirmation
        assert "performance" in response.message.lower() or "faster" in response.message.lower()
        assert response.recommendation.configuration.performance == "Premium"
    
    def test_agent_unavailable_fallback(self):
        """Test fallback when LLM is unavailable."""
        # Setup - LLM unavailable
        self.mock_llm.is_available.return_value = False
        
        recommendation = self._create_mock_recommendation("images")
        self.mock_advisor.recommend_configuration.return_value = recommendation
        
        # Execute
        response = self.agent.process_message("I need storage for images")
        
        # Verify fallback response generated
        assert response.success
        assert response.recommendation is not None
        assert "I'll help you set up storage for images" in response.message
        assert "fallback" not in response.message.lower()  # User shouldn't see technical details
    
    def test_empty_input_handling(self):
        """Test handling of empty or whitespace input."""
        response = self.agent.process_message("   ")
        
        assert not response.success
        assert "didn't catch that" in response.message.lower()
    
    def test_error_handling(self):
        """Test error handling during processing."""
        # Setup - advisor throws exception
        self.mock_advisor.recommend_configuration.side_effect = Exception("Test error")
        
        # Execute
        response = self.agent.process_message("I need storage")
        
        # Verify error handling
        assert not response.success
        assert response.error_message is not None
        assert "workflow mode" in response.message.lower()


class TestStorageConversationFlow:
    """Test conversation flow management."""
    
    def setup_method(self):
        """Set up conversation test fixtures."""
        self.mock_agent = Mock(spec=SimpleAgent)
        self.conversation = StorageConversation(agent=self.mock_agent)
    
    def test_new_conversation_start(self):
        """Test starting a new conversation."""
        # Setup
        self.mock_agent.start_conversation.return_value = AgentResponse(
            message="Hello! I'm your Azure Storage Agent."
        )
        
        # Execute
        response = self.conversation.start_new_conversation()
        
        # Verify
        assert response.success
        assert self.conversation.context.state == ConversationState.GATHERING_REQUIREMENTS
        assert self.conversation.context.interaction_count == 0
        assert len(self.conversation.conversation_history) == 1
    
    def test_requirements_gathering_flow(self):
        """Test requirements gathering conversation flow."""
        # Setup
        self.conversation.context.state = ConversationState.GATHERING_REQUIREMENTS
        
        mock_recommendation = Mock()
        mock_recommendation.detected_use_case = "images"
        mock_recommendation.confidence = 0.85
        
        self.mock_agent.process_message.return_value = AgentResponse(
            message="Perfect for image storage!",
            recommendation=mock_recommendation,
            success=True,
            context_used={"detected_keywords": ["images"]}
        )
        
        # Execute
        response = self.conversation.process_user_input("I need storage for images")
        
        # Verify state transition
        assert self.conversation.context.state == ConversationState.PRESENTING_RECOMMENDATION
        assert self.conversation.context.current_recommendation == mock_recommendation
        assert self.conversation.context.interaction_count == 1
    
    def test_recommendation_confirmation(self):
        """Test recommendation confirmation flow."""
        # Setup
        self.conversation.context.state = ConversationState.PRESENTING_RECOMMENDATION
        
        self.mock_agent.process_message.return_value = AgentResponse(
            message="Great! Proceeding with deployment.",
            success=True
        )
        
        # Execute
        response = self.conversation.process_user_input("yes")
        
        # Verify state transition to deployment confirmation
        assert self.conversation.context.state == ConversationState.CONFIRMING_DEPLOYMENT
        assert response.success
    
    def test_help_request_handling(self):
        """Test help request handling."""
        # Setup
        self.conversation.context.state = ConversationState.GATHERING_REQUIREMENTS
        self.mock_agent.get_help_message.return_value = "Here's how I can help..."
        
        # Execute
        response = self.conversation.process_user_input("help")
        
        # Verify
        assert "help" in response.message.lower()
        # State should remain the same for help
        assert self.conversation.context.state == ConversationState.GATHERING_REQUIREMENTS
    
    def test_conversation_history_tracking(self):
        """Test conversation history is properly tracked."""
        # Setup
        self.conversation.context.state = ConversationState.GATHERING_REQUIREMENTS
        self.mock_agent.process_message.return_value = AgentResponse(
            message="Test response",
            success=True
        )
        
        # Execute multiple interactions
        self.conversation.process_user_input("first message")
        self.conversation.process_user_input("second message")
        
        # Verify history
        history = self.conversation.export_conversation_history()
        assert len(history) == 4  # 2 user + 2 agent messages
        
        user_messages = [h for h in history if h["speaker"] == "user"]
        assert len(user_messages) == 2
        assert user_messages[0]["message"] == "first message"
        assert user_messages[1]["message"] == "second message"
    
    def test_conversation_summary(self):
        """Test conversation summary generation."""
        # Setup conversation context
        self.conversation.context.conversation_id = "test_conv_123"
        self.conversation.context.state = ConversationState.PRESENTING_RECOMMENDATION
        self.conversation.context.interaction_count = 3
        
        # Execute
        summary = self.conversation.get_conversation_summary()
        
        # Verify
        assert summary["conversation_id"] == "test_conv_123"
        assert summary["state"] == "presenting_recommendation"
        assert summary["interaction_count"] == 3
        assert "has_recommendation" in summary
    
    def test_active_conversation_check(self):
        """Test conversation activity status."""
        # Test active states
        active_states = [
            ConversationState.GATHERING_REQUIREMENTS,
            ConversationState.PRESENTING_RECOMMENDATION,
            ConversationState.CONFIRMING_DEPLOYMENT,
            ConversationState.MODIFYING_CONFIG
        ]
        
        for state in active_states:
            self.conversation.context.state = state
            assert self.conversation.is_conversation_active()
        
        # Test inactive states
        inactive_states = [
            ConversationState.INITIAL,
            ConversationState.COMPLETED,
            ConversationState.ERROR
        ]
        
        for state in inactive_states:
            self.conversation.context.state = state
            assert not self.conversation.is_conversation_active()


class TestAgentIntegrationScenarios:
    """Integration tests for complete agent scenarios."""
    
    @patch('src.agent.core.simple_agent.create_ollama_client')
    @patch('src.agent.core.simple_agent.create_user_profile') 
    @patch('src.agent.core.simple_agent.create_storage_advisor')
    def test_end_to_end_storage_creation(self, mock_advisor_factory, mock_profile_factory, mock_llm_factory):
        """Test complete end-to-end storage creation flow."""
        # Setup mocked components
        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = Mock(success=True, content="Great choice for images!")
        mock_llm_factory.return_value = mock_llm
        
        mock_profile = Mock()
        mock_profile.get_context_for_conversation.return_value = {
            "user_preferences": {"cost_preference": "optimized"}
        }
        mock_profile.suggest_storage_name.return_value = "website-images-001"
        mock_profile_factory.return_value = mock_profile
        
        mock_advisor = Mock()
        recommendation = StorageRecommendation(
            configuration=StorageConfig(
                performance="Standard",
                tier="Hot", 
                replication="LRS",
                reasoning="Optimized for website images"
            ),
            detected_use_case="images",
            confidence=0.92,
            alternative_configs=[],
            context_used={"detected_keywords": ["images", "website"]},
            suggestion_id="test_e2e_001"
        )
        mock_advisor.recommend_configuration.return_value = recommendation
        mock_advisor_factory.return_value = mock_advisor
        
        # Execute complete flow
        conversation = StorageConversation()
        
        # 1. Start conversation
        start_response = conversation.start_new_conversation()
        assert start_response.success
        
        # 2. Make storage request
        request_response = conversation.process_user_input("I need storage for my website images")
        assert request_response.success
        assert request_response.recommendation is not None
        assert request_response.requires_confirmation
        
        # 3. Confirm deployment
        confirm_response = conversation.process_user_input("yes")
        assert confirm_response.success
        
        # 4. Verify final state
        assert not conversation.is_conversation_active() or conversation.context.state == ConversationState.CONFIRMING_DEPLOYMENT
        
        # Verify all components were called appropriately
        mock_advisor.recommend_configuration.assert_called()
        mock_profile.suggest_storage_name.assert_called()
        mock_profile.add_deployment_history.assert_called()