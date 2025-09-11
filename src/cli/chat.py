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
            from ..config.settings import mask_subscription_id
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
            from ..config.settings import mask_subscription_id
            import uuid
            
            self.interface.display_info("\n=== Storage Account Deployment Workflow ===")
            
            # Step 1: Check Azure authentication
            self.interface.display_info("Step 1: Checking Azure authentication...")
            auth = AzureAuthenticator()
            auth_result = auth.authenticate()
            
            if not auth_result.success:
                return f"Authentication failed: {auth_result.error_message}\nPlease run 'az login' and try again."
            
            self.interface.display_success(f"✓ Authenticated to subscription: {mask_subscription_id(auth_result.subscription_id)}")
            
            # Step 1.5: Subscription selection
            current_sub_id = mask_subscription_id(auth_result.subscription_id)
            self.interface.display_info(f"\nCurrent subscription: {current_sub_id}")
            if auth_result.user_info and auth_result.user_info.get('subscription_name'):
                self.interface.display_info(f"Subscription name: {auth_result.user_info['subscription_name']}")
                
            # Show available subscriptions and allow selection
            self.interface.display_info("Getting available subscriptions...")
            available_subs = auth.get_available_subscriptions(auth_result)
            
            if not available_subs:
                self.interface.display_info("Could not retrieve subscription list. Continuing with current subscription...")
            elif len(available_subs) > 1:
                self.interface.display_info("\nAvailable subscriptions:")
                for i, sub in enumerate(available_subs, 1):
                    marker = " (current)" if sub['id'] == auth_result.subscription_id else ""
                    self.interface.display_info(f"  {i}. ({mask_subscription_id(sub['id'])}){marker}")
                
                selection = input(f"\nEnter subscription number (1-{len(available_subs)}) or press Enter to use current: ").strip()
                
                if selection and selection.isdigit():
                    selected_index = int(selection) - 1
                    if 0 <= selected_index < len(available_subs):
                        selected_sub = available_subs[selected_index]
                        # Update auth_result with selected subscription
                        auth_result.subscription_id = selected_sub['id']
                        if auth_result.user_info:
                            auth_result.user_info['subscription_name'] = selected_sub['name']
                        self.interface.display_success(f"Using subscription: ({mask_subscription_id(selected_sub['id'])})")
                    else:
                        return "Invalid subscription number selected."
            
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
            
            # Step 4: Show deployment confirmation with all details
            self.interface.display_info("\nStep 4: Deployment confirmation...")
            
            confirmation_details = [
                "\n" + "=" * 60,
                "DEPLOYMENT CONFIRMATION",
                "=" * 60,
                f"Subscription ID: {mask_subscription_id(auth_result.subscription_id)}",
                f"Storage Account Name: {config.name}",
                f"Resource Group: {config.resource_group}",
                f"Location: {config.location}",
                f"Performance Tier: {config.performance_tier}",
                f"Replication Type: {config.replication_type}",
                f"Access Tier: {config.access_tier}",
                f"Account Kind: {config.kind}",
                f"HTTPS Only: {config.enable_https_only}",
                f"Hierarchical Namespace: {config.enable_hierarchical_namespace}",
                "=" * 60
            ]
            
            for line in confirmation_details:
                print(line)
            
            while True:
                action = input("\nChoose an action:\n1. Proceed with deployment (y)\n2. Modify parameters (m)\n3. Cancel (n)\nEnter choice (y/m/n): ").strip().lower()
                
                if action in ['y', 'yes', '1']:
                    break  # Proceed with deployment
                elif action in ['n', 'no', '3']:
                    return "Deployment cancelled by user."
                elif action in ['m', 'modify', '2']:
                    # Allow parameter modification
                    config = self._modify_storage_config(config)
                    if config is None:
                        return "Deployment cancelled by user."
                    
                    # Regenerate template with new config
                    generated_template = template_generator.generate_template(config)
                    self.interface.display_success("✓ Template regenerated with new parameters")
                    
                    # Show updated confirmation
                    confirmation_details = [
                        "\n" + "=" * 60,
                        "UPDATED DEPLOYMENT CONFIRMATION",
                        "=" * 60,
                        f"Subscription ID: {mask_subscription_id(auth_result.subscription_id)}",
                        f"Storage Account Name: {config.name}",
                        f"Resource Group: {config.resource_group}",
                        f"Location: {config.location}",
                        f"Performance Tier: {config.performance_tier}",
                        f"Replication Type: {config.replication_type}",
                        f"Access Tier: {config.access_tier}",
                        f"Account Kind: {config.kind}",
                        f"HTTPS Only: {config.enable_https_only}",
                        f"Hierarchical Namespace: {config.enable_hierarchical_namespace}",
                        "=" * 60
                    ]
                    
                    for line in confirmation_details:
                        print(line)
                else:
                    print("Invalid choice. Please enter 'y', 'm', or 'n'.")
            
            # Step 5: Deploy to Azure
            self.interface.display_info(f"\nStep 5: Deploying to Azure (Subscription: {mask_subscription_id(auth_result.subscription_id)})...")
            
            deployer = create_arm_deployer(auth_result.subscription_id, auth_result)
            
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
    
    def _modify_storage_config(self, config):
        """
        Allow user to modify storage configuration parameters.
        
        Args:
            config: Current storage configuration
            
        Returns:
            Modified configuration or None if cancelled
        """
        print("\nWhich parameter would you like to modify?")
        print("1. Storage Account Name")
        print("2. Resource Group")  
        print("3. Location")
        print("4. Performance Tier")
        print("5. Replication Type")
        print("6. Access Tier")
        print("7. Cancel modifications")
        
        choice = input("\nEnter choice (1-7): ").strip()
        
        if choice == '1':
            new_name = input(f"Enter new storage account name (current: {config.name}): ").strip()
            if new_name:
                config.name = new_name
        elif choice == '2':
            new_rg = input(f"Enter new resource group (current: {config.resource_group}): ").strip()
            if new_rg:
                config.resource_group = new_rg
        elif choice == '3':
            print("Available locations: eastus, westus, centralus, westeurope, eastasia")
            new_location = input(f"Enter new location (current: {config.location}): ").strip()
            if new_location:
                config.location = new_location
        elif choice == '4':
            print("Performance tiers: Standard, Premium")
            new_perf = input(f"Enter new performance tier (current: {config.performance_tier}): ").strip()
            if new_perf and new_perf.lower() in ['standard', 'premium']:
                config.performance_tier = new_perf.title()
        elif choice == '5':
            print("Replication types: LRS, GRS, ZRS, RA-GRS, RA-ZRS")
            new_repl = input(f"Enter new replication type (current: {config.replication_type}): ").strip()
            if new_repl and new_repl.upper() in ['LRS', 'GRS', 'ZRS', 'RA-GRS', 'RA-ZRS']:
                config.replication_type = new_repl.upper()
        elif choice == '6':
            print("Access tiers: Hot, Cool, Archive")
            new_access = input(f"Enter new access tier (current: {config.access_tier}): ").strip()
            if new_access and new_access.lower() in ['hot', 'cool', 'archive']:
                config.access_tier = new_access.title()
        elif choice == '7':
            return config
        else:
            print("Invalid choice.")
            return config
            
        return config