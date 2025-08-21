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

Run the agent:
```bash
python -m src.main
```

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
│   └── base.py        # Base agent classes and interfaces
├── resources/          # Azure resource handlers
│   ├── __init__.py
│   └── base.py        # Base resource classes and validation
├── templates/          # Template generation
│   ├── __init__.py
│   └── generator.py   # ARM template generator with Jinja2
├── deployers/          # Azure deployment logic
│   ├── __init__.py
│   └── azure.py       # Azure authentication and deployment
└── config/             # Configuration management
    ├── __init__.py
    ├── settings.py     # Application and Azure settings
    └── logging.py      # Logging configuration with Rich support
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

**Next**: Sprint 2 - Intent Recognition & Storage Account Implementation

## Contributing

1. Follow PEP 8 coding standards
2. Use type hints for all functions
3. Write unit tests for new features
4. Update documentation when adding features

## License

[License information to be added]