# Azure Infrastructure Agent

An intelligent conversational agent that simplifies Azure infrastructure deployment through natural language interactions.

## Overview

The Azure Infrastructure Agent guides users through resource specification, generates appropriate infrastructure-as-code templates, and handles deployments with minimal manual intervention.

## Features

- **Conversational Interface**: Natural language interaction for specifying infrastructure requirements
- **Guided Configuration**: Interactive prompts to gather all necessary parameters
- **Template Generation**: Automatic creation of ARM/Bicep templates from user specifications
- **Deployment Management**: Execute and monitor Azure deployments with status reporting

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

### Current Functionality (Sprint 2 Complete)

The agent currently supports natural language intent parsing, storage account configuration, and ARM template generation:

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
├── deployers/          # Azure deployment logic
│   ├── __init__.py
│   └── azure.py       # Azure authentication and deployment
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

**Next**: Sprint 3 - Azure Integration & Deployment Engine

## Contributing

1. Follow PEP 8 coding standards
2. Use type hints for all functions
3. Write unit tests for new features
4. Update documentation when adding features

## License

[License information to be added]