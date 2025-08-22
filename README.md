# Azure Infrastructure Agent

An intelligent conversational agent that simplifies Azure infrastructure deployment through natural language interactions.

## Overview

The Azure Infrastructure Agent guides users through resource specification, generates appropriate infrastructure-as-code templates, and handles deployments with minimal manual intervention.

## Features

- **Conversational Interface**: Natural language interaction for specifying infrastructure requirements
- **Guided Configuration**: Interactive prompts to gather all necessary parameters
- **Template Generation**: Automatic creation of ARM/Bicep templates from user specifications
- **Azure Authentication**: Multi-method authentication with automatic fallback (CLI, Service Principal, Managed Identity)
- **Deployment Management**: Execute and monitor Azure deployments with real-time status reporting
- **Rollback Capability**: Comprehensive rollback functionality for failed deployments
- **Template Validation**: Pre-deployment validation with warnings and error detection

## Prerequisites

- Python 3.9 or higher
- Active Azure subscription
- Azure CLI (for authentication)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd azure-infrastructure-agent
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the agent:
```bash
python -m src.main
```

### Complete Storage Account Workflow

With Sprint 3 complete, you can now deploy Azure storage accounts using natural language:

```text
User: "I need a storage account"
Agent: "I'll help you create a storage account. What would you like to name it?"
User: "mystorageacct001"
Agent: "Which resource group should I use?"
User: "my-rg"
Agent: "Which region would you prefer?"
User: "East US"
[Agent continues collecting configuration...]
Agent: [Shows generated ARM template preview]
Agent: "Would you like me to deploy this storage account?"
User: "yes"
Agent: [Deploys to Azure with real-time status updates]
```

### Current Functionality (Sprint 3 Complete)

The agent provides a complete end-to-end workflow for Azure storage account deployment, including natural language intent parsing, interactive configuration, ARM template generation, Azure authentication, and deployment management:

```python
# Example: Intent parsing
from src.agents.intent_parser import create_basic_intent_parser
from src.agents.entities import create_entity_extractor

parser = create_basic_intent_parser()
response = parser.process({"user_input": "I need a storage account in East US"})
# Returns: storage_account intent with region entity

# Example: Storage account configuration
from src.resources.storage_account import create_storage_account_resource

storage_handler = create_storage_account_resource()
config = storage_handler.collect_parameters_interactively()

# Example: ARM template generation
from src.templates.storage_template_generator import create_storage_template_generator

template_gen = create_storage_template_generator()
generated = template_gen.generate_template(config)
preview = template_gen.preview_template(config)

# Example: Azure authentication
from src.auth.azure_auth import create_azure_authenticator

authenticator = create_azure_authenticator()
auth_result = authenticator.authenticate()
# Returns: authentication result with credentials and subscription info

# Example: ARM template deployment
from src.deployers.arm_deployer import create_arm_deployer, DeploymentConfig

deployer = create_arm_deployer()
deployment_config = DeploymentConfig(
    deployment_name="my-storage-deployment",
    resource_group_name="my-rg",
    location="East US",
    template=generated,
    parameters={"storageAccountName": "mystorageaccount123"}
)

# Validate template before deployment
validation_result = deployer.validate_template(deployment_config)
if validation_result.is_valid:
    # Deploy the template
    deployment_result = deployer.deploy(deployment_config)
    print(f"Deployment status: {deployment_result.status.provisioning_state}")
```

### Supported Intents

- **Storage Account**: "I need a storage account", "Create storage", "Deploy a storage account"
- **Web App**: "Create a web app", "I need an app service", "Deploy web application"
- **Virtual Machine**: "Create a VM", "I need a virtual machine"
- **And 10+ more Azure resource types**

### Supported Parameters

**Storage Accounts**:
- Account name (with Azure naming validation)
- Resource group (new or existing)
- Location/region (validated against Azure regions)
- Performance tier (Standard/Premium)
- Replication type (LRS, GRS, RAGRS, ZRS, GZRS, RAGZRS)
- Access tier (Hot/Cool/Archive)
- Storage account kind (StorageV2, Storage, FileStorage, etc.)
- Tags and advanced security settings

## Project Structure

```
src/
├── __init__.py
├── main.py              # Main entry point
├── cli/                 # Command-line interface components
│   ├── __init__.py
│   ├── chat.py         # Chat interface logic
│   └── interface.py    # Terminal interface handling
├── agents/             # Intent parsing and AI logic
│   ├── __init__.py
│   ├── base.py        # Base agent classes and interfaces
│   ├── entities.py    # Entity extraction system for Azure resources
│   └── intent_parser.py # Intent classification and routing logic
├── resources/          # Azure resource handlers
│   ├── __init__.py
│   ├── base.py        # Base resource classes and validation
│   ├── storage_account.py # Storage account resource handler
│   ├── storage_config.py  # Storage account configuration classes
│   ├── validators.py  # Azure resource validation utilities
│   └── validation_result.py # Validation result containers
├── templates/          # Template generation
│   ├── __init__.py
│   ├── generator.py   # Base ARM template generator with Jinja2
│   ├── storage_template_generator.py # Storage-specific template generator
│   └── storage_account.json.j2 # Jinja2 template for storage accounts
├── auth/               # Azure authentication
│   ├── __init__.py
│   └── azure_auth.py  # Multi-method Azure authentication (CLI, Service Principal, Managed Identity)
├── deployers/          # Azure deployment logic
│   ├── __init__.py
│   ├── azure.py       # Legacy Azure deployment (being phased out)
│   ├── arm_deployer.py # ARM template deployment engine with validation and rollback
│   └── deployment_monitor.py # Real-time deployment monitoring and progress tracking
└── config/             # Configuration management
    ├── __init__.py
    ├── settings.py     # Application and Azure settings
    └── logging.py      # Logging configuration with Rich support

templates/
└── arm/                # Static ARM template examples
    └── storage_account_template.json # Storage account ARM template

tests/                  # Comprehensive test suite
├── src/
│   ├── agents/        # Intent parsing and entity extraction tests
│   ├── resources/     # Resource handler and validation tests
│   ├── templates/     # Template generation and validation tests
│   ├── auth/          # Azure authentication tests
│   ├── deployers/     # Deployment engine and monitoring tests
│   └── ...
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/ tests/
```

### Linting

```bash
flake8 src/ tests/
```

## Dependencies

- **CLI Framework**: Click 8.1.0+
- **Terminal UI**: Rich 13.0.0+
- **Data Validation**: Pydantic 2.0.0+
- **Template Engine**: Jinja2 3.1.0+
- **Azure SDK**: azure-identity, azure-mgmt-resource, azure-mgmt-storage, azure-mgmt-web, azure-cli-core
- **Development**: pytest, flake8, black

## Current Status

**✅ Sprint 1 Foundation Completed**:

**✅ Task 1.1 Completed**: Environment Setup
- ✅ Python virtual environment created
- ✅ Project directory structure established  
- ✅ Dependencies defined in requirements.txt
- ✅ Git repository initialized
- ✅ VS Code configuration added

**✅ Task 1.2 Completed**: Basic CLI Framework
- ✅ Click CLI structure implemented
- ✅ Rich console for enhanced terminal output
- ✅ Conversation loop with graceful exit handling
- ✅ Welcome message and user interaction
- ✅ Comprehensive unit tests created

**✅ Task 1.3 Completed**: Basic Project Structure
- ✅ Complete directory structure with all modules
- ✅ Base agent and resource classes with extensible architecture
- ✅ Configuration management with environment variables and Azure settings
- ✅ Advanced logging system with Rich console formatting and file logging
- ✅ ARM template generator with Jinja2 templating engine
- ✅ Azure deployment engine with authentication and monitoring

**✅ Sprint 2 Intent Recognition & Storage Account Completed**:

**✅ Task 2.1 Completed**: Basic Intent Parser
- ✅ Intent classification system with 15+ Azure resource intents
- ✅ Keyword-based resource detection and routing logic
- ✅ Entity extraction system for Azure resources (names, regions, tiers)
- ✅ Response routing with agent request/response architecture
- ✅ Comprehensive test coverage for intent parsing scenarios

**✅ Task 2.2 Completed**: Storage Account Resource Handler
- ✅ Storage account resource class with parameter collection
- ✅ Interactive questionnaire flow for guided parameter gathering
- ✅ Azure-specific validation with naming rules and constraints
- ✅ Support for all storage account parameters (tier, replication, access tier)
- ✅ Modular architecture with separate config and validation modules

**✅ Task 2.3 Completed**: ARM Template Generator for Storage
- ✅ Jinja2 template for storage account ARM deployments
- ✅ Parameter substitution with dynamic template rendering
- ✅ Template validation with ARM schema and security checks
- ✅ Template preview functionality with human-readable summaries
- ✅ Integration with storage account configuration system

**✅ Sprint 3 Azure Integration & Deployment Completed**:

**✅ Task 3.1 Completed**: Azure Authentication
- ✅ Multi-method authentication (Azure CLI, Service Principal, Managed Identity)
- ✅ Automatic fallback between authentication methods
- ✅ Subscription validation and access checking
- ✅ Authentication result caching with expiration
- ✅ Clear error messages and troubleshooting guidance
- ✅ Comprehensive test coverage for all authentication scenarios

**✅ Task 3.2 Completed**: Azure Deployment Engine
- ✅ ARM template deployment with validation and error handling
- ✅ Real-time deployment monitoring with progress callbacks
- ✅ Deployment rollback functionality (deletion and previous deployment)
- ✅ Resource group management and automatic creation
- ✅ Template validation before deployment with warnings analysis
- ✅ Deployment history tracking and operation monitoring
- ✅ Extensible callback system for UI integration
- ✅ Timeout handling and graceful cancellation

**✅ Task 3.3 Completed**: End-to-End Storage Account Flow
- ✅ Complete integration of all components for storage account deployment
- ✅ Comprehensive error handling and user feedback
- ✅ Deployment summary with status reporting
- ✅ Full conversation flow from intent to deployment
- ✅ Template preview and confirmation workflow

**✅ Task 3.4 Completed**: Fix Template Generation Issues
- ✅ Resolved "TemplateNotFound" errors in template generation
- ✅ ARM template file properly located in templates directory
- ✅ End-to-end template generation with parameter substitution
- ✅ Generated templates pass validation with proper ARM JSON structure
- ✅ Comprehensive test coverage for template generation workflow

**Sprint 3 Complete**: Full storage account deployment workflow from natural language input to Azure deployment is now functional.

**Next**: Sprint 4 - Web App Support & Polish

## Contributing

1. Follow PEP 8 coding standards
2. Use type hints for all functions
3. Write unit tests for new features
4. Update documentation when adding features

## License

[License information to be added]