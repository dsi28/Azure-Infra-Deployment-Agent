"""
Chat interface logic for the Azure Infrastructure Agent.
"""
import signal
import sys
from typing import Optional
from .interface import TerminalInterface
from ..config.logging import get_logger

logger = get_logger(__name__)


class ChatManager:
    """
    Manages the conversational interface and main chat loop.
    
    Handles user input processing, conversation flow, and graceful shutdown
    for the Azure Infrastructure Agent CLI.
    """
    
    def __init__(self) -> None:
        """
        Initialize the chat manager with terminal interface.
        
        Sets up the terminal interface and configures signal handlers
        for graceful exit handling.
        """
        self.interface = TerminalInterface()
        self.running = True
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """
        Set up signal handlers for graceful exit on Ctrl+C.
        
        Configures SIGINT handler to allow clean shutdown when user
        presses Ctrl+C during conversation.
        """
        # Reason: Enable graceful shutdown on Ctrl+C signal
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle interrupt signals for graceful shutdown.
        
        Args:
            signum (int): The signal number received.
            frame: The current stack frame.
        """
        self.interface.display_info("\nShutdown requested...")
        self.stop()
    
    def start(self) -> None:
        """
        Start the main conversation loop.
        
        Displays welcome message and enters the main chat loop
        where users can interact with the agent.
        """
        self.interface.display_welcome()
        self._conversation_loop()
    
    def stop(self) -> None:
        """
        Stop the conversation loop and display goodbye message.
        
        Sets the running flag to False and shows farewell message.
        """
        self.running = False
        self.interface.display_goodbye()
    
    def _conversation_loop(self) -> None:
        """
        Main conversation loop for processing user input.
        
        Continuously processes user input until exit condition is met.
        Handles quit commands and forwards other input to the agent processor.
        """
        while self.running:
            try:
                user_input = self.interface.get_user_input()
                
                # Check for exit commands
                if self._is_exit_command(user_input):
                    self.stop()
                    break
                
                # Process the user input and generate response
                response = self._process_user_input(user_input)
                self.interface.display_agent_response(response)
                
            except EOFError:
                # Reason: Handle EOF gracefully (e.g., when input is redirected)
                self.interface.display_info("\nInput stream ended.")
                self.stop()
                break
            except KeyboardInterrupt:
                # Reason: Additional safety net for Ctrl+C handling
                self.interface.display_info("\nInterrupted by user.")
                self.stop()
                break
            except Exception as e:
                # Reason: Catch unexpected errors to prevent crash
                self.interface.display_error(f"An unexpected error occurred: {str(e)}")
    
    def _is_exit_command(self, user_input: str) -> bool:
        """
        Check if the user input is an exit command.
        
        Args:
            user_input (str): The user's input string.
            
        Returns:
            bool: True if the input is an exit command, False otherwise.
        """
        exit_commands = ['quit', 'exit', 'bye', 'goodbye']
        return user_input.lower().strip() in exit_commands
    
    def _process_user_input(self, user_input: str) -> str:
        """
        Process user input using the complete storage account deployment workflow.
        
        Integrates intent parsing, resource handling, template generation,
        and deployment execution for storage accounts.
        
        Args:
            user_input (str): The user's input string.
            
        Returns:
            str: The agent's response message.
        """
        if not user_input.strip():
            return "I'm here to help! Please tell me what Azure resources you need."
        
        try:
            # Import required components
            from ..agents.intent_parser import create_intent_parser, Intent
            from ..resources.storage_account import create_storage_account_resource
            from ..resources.base import ResourceRequest
            from ..templates.storage_template_generator import create_storage_template_generator
            from ..deployers.arm_deployer import create_arm_deployer, DeploymentConfig
            from ..auth.azure_auth import AzureAuthenticator
            import uuid
            from datetime import datetime
            
            # Parse intent from user input
            intent_parser = create_intent_parser()
            from ..agents.base import AgentRequest
            
            request = AgentRequest(user_input=user_input)
            intent_response = intent_parser.process(request)
            
            # Handle different intents
            if intent_response.intent == Intent.CREATE_STORAGE_ACCOUNT.value:
                return self._handle_storage_account_creation(user_input, intent_response)
            elif intent_response.intent == Intent.GET_HELP.value:
                return self._handle_help_request()
            elif intent_response.intent == Intent.GREETING.value:
                return intent_response.response
            elif intent_response.intent == Intent.GOODBYE.value:
                return intent_response.response
            else:
                return ("I can help you create Azure storage accounts. Try saying something like:\n"
                       "- 'I need a storage account'\n"
                       "- 'Create a storage account called mystorageacct'\n"
                       "- 'Deploy a storage account in East US'")
                       
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}")
            return f"I encountered an error processing your request. Please try again or ask for help."
    
    def _handle_storage_account_creation(self, user_input: str, intent_response) -> str:
        """
        Handle the complete storage account creation workflow.
        
        Args:
            user_input (str): Original user input.
            intent_response: Response from intent parser.
            
        Returns:
            str: Response message for the user.
        """
        try:
            from ..resources.storage_account import create_storage_account_resource
            from ..resources.base import ResourceRequest
            from ..templates.storage_template_generator import create_storage_template_generator
            from ..deployers.arm_deployer import create_arm_deployer, DeploymentConfig
            from ..auth.azure_auth import AzureAuthenticator
            import uuid
            
            self.interface.display_info("\n=== Storage Account Deployment Workflow ===")
            
            # Step 1: Check Azure authentication
            self.interface.display_info("Step 1: Checking Azure authentication...")
            auth = AzureAuthenticator()
            auth_result = auth.authenticate()
            
            if not auth_result.success:
                return f"Authentication failed: {auth_result.error_message}\nPlease run 'az login' and try again."
            
            self.interface.display_success(f"✓ Authenticated to subscription: {auth_result.subscription_id}")
            
            # Step 2: Collect resource parameters
            self.interface.display_info("\nStep 2: Collecting storage account parameters...")
            
            storage_resource = create_storage_account_resource()
            
            # Extract entities from intent response and create resource request
            request = ResourceRequest(
                resource_type="storage_account",
                parameters=intent_response.entities
            )
            
            resource_response = storage_resource.process(request)
            
            if not resource_response.success:
                return f"Configuration failed: {resource_response.message}"
            
            config = resource_response.configuration
            self.interface.display_success(f"✓ Configuration completed for storage account: {config.name}")
            
            # Step 3: Generate ARM template
            self.interface.display_info("\nStep 3: Generating ARM template...")
            
            template_generator = create_storage_template_generator()
            generated_template = template_generator.generate_template(config)
            
            self.interface.display_success("✓ ARM template generated successfully")
            
            # Step 4: Show template preview and get confirmation
            self.interface.display_info("\nStep 4: Template preview...")
            preview = template_generator.preview_template(config)
            print(preview)
            
            confirm = input("\nDo you want to proceed with deployment? (y/N): ").strip().lower()
            if confirm != 'y' and confirm != 'yes':
                return "Deployment cancelled by user."
            
            # Step 5: Deploy to Azure
            self.interface.display_info("\nStep 5: Deploying to Azure...")
            
            deployer = create_arm_deployer(auth_result.subscription_id)
            
            deployment_config = DeploymentConfig(
                deployment_name=f"storage-{config.name}-{uuid.uuid4().hex[:8]}",
                resource_group_name=config.resource_group,
                location=config.location,
                template=generated_template.content,
                parameters={
                    "storageAccountName": config.name,
                    "location": config.location,
                    "performanceTier": config.performance_tier,
                    "replicationType": config.replication_type,
                    "accessTier": config.access_tier,
                    "storageAccountKind": config.kind,
                    "enableHttpsOnly": config.enable_https_only,
                    "enableHierarchicalNamespace": config.enable_hierarchical_namespace
                },
                tags={"created_by": "azure-infrastructure-agent"}
            )
            
            deployment_result = deployer.deploy(deployment_config)
            
            # Step 6: Report results
            if deployment_result.status.provisioning_state == "Succeeded":
                summary = self._create_deployment_summary(deployment_result, config)
                self.interface.display_success("\n✓ Deployment completed successfully!")
                return summary
            else:
                error_msg = deployment_result.status.error_message or "Unknown deployment error"
                self.interface.display_error(f"\n✗ Deployment failed: {error_msg}")
                return f"Deployment failed: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error in storage account creation workflow: {str(e)}")
            return f"Storage account creation failed: {str(e)}"
    
    def _handle_help_request(self) -> str:
        """Handle user help requests."""
        return ("I'm your Azure Infrastructure Agent! I can help you deploy:\n\n"
               "• Storage Accounts - Just say 'I need a storage account'\n"
               "• More resource types coming soon!\n\n"
               "I'll guide you through the process step by step, including:\n"
               "- Parameter collection\n"
               "- Template generation\n"
               "- Azure deployment\n\n"
               "Try: 'Create a storage account called mystore in East US'")
    
    def _create_deployment_summary(self, deployment_result, config) -> str:
        """Create a deployment summary for the user."""
        duration_str = str(deployment_result.duration) if deployment_result.duration else "N/A"
        
        summary_lines = [
            "\n" + "=" * 50,
            "DEPLOYMENT SUMMARY",
            "=" * 50,
            f"Storage Account: {config.name}",
            f"Resource Group: {config.resource_group}",
            f"Location: {config.location}",
            f"Performance Tier: {config.performance_tier}",
            f"Replication: {config.replication_type}",
            f"Access Tier: {config.access_tier}",
            f"Deployment Status: {deployment_result.status.provisioning_state}",
            f"Duration: {duration_str}",
            "\nNext steps:",
            "- Your storage account is now ready to use",
            "- You can access it through the Azure Portal",
            "- Use Azure Storage Explorer or Azure CLI for management",
            "=" * 50
        ]
        
        return "\n".join(summary_lines)