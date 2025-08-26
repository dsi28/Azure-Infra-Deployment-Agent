# Azure Storage Agent (Simple MVP)

A free, local Azure Storage Account assistant that helps users create and configure Azure Storage Accounts through natural conversation using a local LLM (Ollama).

## Overview

This is a simple MVP implementation of an Azure Storage Agent that:
- Uses **Ollama** for free local LLM capabilities (no API keys required)
- Focuses exclusively on **Azure Storage Accounts** configuration
- Provides intelligent storage recommendations based on use cases
- Uses **JSON-based local storage** for user preferences (no external databases)
- Offers graceful fallback when services are unavailable

## Features

- **Local LLM Integration**: Uses Ollama for natural language understanding
- **Storage Expertise**: Specialized prompts for Azure Storage Account configuration
- **Use Case Detection**: Identifies storage needs and suggests appropriate tiers
- **Configuration Intelligence**: Recommends performance, access, and replication settings
- **Free Dependencies**: No paid external services required

## Project Structure

```
src/agent/
├── llm/
│   ├── ollama_client.py      # Ollama API wrapper
│   └── storage_prompts.py    # Storage-specific prompts
├── memory/
│   ├── json_memory.py        # JSON-based local storage
│   └── user_profile.py       # Storage-specific user profile
├── decision/
│   ├── rules.py              # Storage configuration rules
│   ├── use_case_detector.py  # Use case detection from text
│   └── storage_advisor.py    # Main decision engine
├── core/
│   ├── simple_agent.py       # Main agent orchestrator
│   └── __init__.py           # Core module exports
├── conversation/
│   └── storage_conversation.py # Conversation flow management
├── learning/
│   ├── simple_feedback.py    # Feedback learning system
│   └── __init__.py           # Learning module exports
src/cli/
└── agent_chat.py             # Agent chat interface
src/main.py                   # Updated main entry point with --agent flag
tests/agent/
├── test_ollama_client.py     # Ollama client tests
├── test_storage_prompts.py   # Storage prompt tests
├── test_json_memory.py       # JSON memory tests
├── test_user_profile.py      # User profile tests
├── test_rules.py             # Decision rules tests
├── test_use_case_detector.py # Use case detection tests
├── test_storage_advisor.py   # Storage advisor tests
├── test_storage_scenarios.py # End-to-end scenario tests
└── test_simple_feedback.py   # Feedback learning tests
data/                         # Local JSON data files (auto-created)
├── user_preferences.json     # User preferences storage
└── conversation_history.json # Conversation history
test_ollama_setup.py          # Integration test
requirements-agent-simple.txt # Free dependencies only
```

## Prerequisites

### 1. Install Ollama

1. Visit [https://ollama.ai](https://ollama.ai)
2. Download and install Ollama for your platform
3. Pull a model: `ollama pull llama3.1`
4. Ollama will start automatically

### 2. Install Python Dependencies

```bash
pip install -r requirements-agent-simple.txt
```

## Quick Start

### 1. Verify Setup

Run the integration test to check if everything is working:

```bash
python test_ollama_setup.py
```

Expected output when Ollama is running:
```
+ Day 1 Setup Complete!
+ Ollama is running and accessible
+ Basic chat functionality works
+ Storage-specific prompts work
+ Requirements extraction tested
```

### 2. Run Unit Tests

```bash
python -m pytest tests/agent/ -v
```

Should show all 649+ tests passing (154 existing + 462 scenario tests + 33 integration tests).

## Usage Examples

### Basic Ollama Client Usage

```python
from src.agent.llm.ollama_client import create_ollama_client

client = create_ollama_client()

# Check if Ollama is available
if client.is_available():
    # Basic chat
    response = client.chat("I need storage for my website images")
    print(response.content)
    
    # Storage-specific conversation
    from src.agent.llm.storage_prompts import STORAGE_AGENT_SYSTEM_PROMPT
    response = client.chat(
        "I need backup storage for my database", 
        system_prompt=STORAGE_AGENT_SYSTEM_PROMPT
    )
    print(response.content)
```

### Storage Requirements Extraction

```python
from src.agent.llm.storage_prompts import format_extract_requirements_prompt

client = create_ollama_client()
user_request = "I need cheap storage for old log files"

prompt = format_extract_requirements_prompt(user_request)
response = client.generate(prompt)

# Response will be JSON with extracted requirements
print(response.content)
```

### User Profile and Memory Management

```python
from src.agent.memory import create_user_profile

# Create user profile with local JSON storage
profile = create_user_profile()

# Set user preferences
profile.set_preferred_regions(["westus", "eastus2"])
profile.set_cost_preference("optimized")
profile.set_naming_pattern("descriptive")

# Get intelligent storage name suggestions
storage_name = profile.suggest_storage_name("images")
print(f"Suggested name: {storage_name}")  # webapp-images-storage

# Learn from deployment success
deployment_result = {
    "success": True,
    "use_case": "backups",
    "access_tier": "Cool",
    "replication_type": "GRS",
    "storage_name": "backup-storage-001"
}
profile.add_deployment_history(deployment_result)

# Get conversation context for personalized responses
context = profile.get_context_for_conversation()
print(f"User preferences: {context['user_preferences']}")
print(f"Recent deployments: {len(context['recent_deployments'])}")
```

### Memory System Usage

```python
from src.agent.memory import create_memory

# Create JSON-based memory system
memory = create_memory()

# Store and retrieve preferences
memory.set_preference("company_name", "Acme Corp")
company = memory.get_preference("company_name")

# Add conversation entries
memory.add_conversation_entry({
    "user_input": "I need storage for website images",
    "agent_response": "I recommend Hot tier with LRS replication",
    "use_case": "images",
    "suggested_config": {"tier": "Hot", "replication": "LRS"}
})

# Get recent conversation history
recent = memory.get_recent_conversations(5)
print(f"Last 5 conversations: {len(recent)}")

# Backup data for safety
backup_files = memory.backup_data()
print(f"Backed up to: {backup_files['preferences']}")
```

### Storage Decision Engine Usage

```python
from src.agent.decision import create_storage_advisor

# Create storage advisor with intelligent decision making
advisor = create_storage_advisor()

# Get storage recommendation from natural language input
recommendation = advisor.recommend_configuration(
    user_input="I need fast storage for my production database",
    user_preferences={
        "cost_preference": "performance",
        "preferred_regions": ["eastus"],
        "use_case_patterns": {
            "database": {"tier": "Hot", "performance": "Premium", "replication": "ZRS"}
        }
    }
)

print(f"Recommended: {recommendation.configuration.performance} {recommendation.configuration.tier}")
print(f"Replication: {recommendation.configuration.replication}")
print(f"Confidence: {recommendation.confidence:.2f}")
print(f"Reasoning: {recommendation.configuration.reasoning}")

# Get detailed explanation
explanation = advisor.explain_recommendation(recommendation)
print(f"Confidence Level: {explanation['confidence_level']}")
print(f"Trade-offs: {explanation['trade_offs']['cost_vs_performance']}")

# Check alternatives
for alt in recommendation.alternative_configs:
    print(f"Alternative: {alt.performance} {alt.tier} with {alt.replication}")
```

### Use Case Detection Usage

```python
from src.agent.decision import create_use_case_detector

detector = create_use_case_detector()

# Detect use case from user input
result = detector.detect_use_case("I need secure storage for compliance data with geo-redundancy")

print(f"Primary use case: {result.primary_use_case}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Keywords found: {result.keywords_found}")
print(f"Performance indicators: {result.performance_indicators}")
print(f"Context hints: {result.context_hints}")

# Get suggestions for partial input
suggestions = detector.get_use_case_suggestions("back")
print(f"Suggestions: {suggestions}")  # ['backup', 'backups']

# Analyze text complexity
analysis = detector.analyze_text_complexity("I need high-performance storage with low latency")
print(f"Technical terms detected: {analysis['has_technical_terms']}")
print(f"Complexity score: {analysis['complexity_score']}")
```

### Agent Mode Usage

#### Starting the Agent

```bash
# Start with intelligent conversational agent (requires Ollama)
python -m src.main --agent

# Start with traditional step-by-step workflow
python -m src.main
```

#### Example Agent Conversation

```
🤖 Starting Azure Storage Agent (Agent Mode)
💡 Requires Ollama with llama3.1 model installed
🔄 Fallback to workflow mode available if needed
------------------------------------------------------------

🤖 Hello! I'm your Azure Storage Agent. I can help you create and configure
Azure Storage Accounts through natural conversation.

Just tell me what kind of storage you need - for example:
• 'I need storage for my website images'
• 'Create backup storage for my database'
• 'I need cheap storage for log files'

What can I help you with today?

💬 You: I need storage for my e-commerce product images

🤖 Perfect for e-commerce images! I'll set up fast, accessible storage for your product catalog.

📋 Storage Configuration:
• Performance: Standard
• Access Tier: Hot  
• Replication: LRS
• Suggested Name: ecommerce-images-001
• Confidence: 92%

💡 Why this configuration?
Hot tier provides fast access for customer browsing, Standard performance is cost-effective for most e-commerce needs, and LRS replication is sufficient for product images that can be easily re-uploaded.

Would you like me to proceed with this configuration? You can also say 'make it cheaper', 'make it faster', or ask for changes.

💬 You: yes

🤖 Perfect! I'll prepare the deployment with these settings:

📋 Final Configuration:
• Performance: Standard
• Access Tier: Hot
• Replication: LRS

The configuration is ready for deployment. You can now use your existing deployment tools to create the storage account with these specifications.
```

#### Agent Features

- **Natural Conversation**: Describe storage needs in plain English
- **Smart Recommendations**: Intelligent configuration based on use case
- **Learning**: Remembers preferences and improves over time
- **Special Commands**: `help`, `status`, `restart`, `workflow`, `exit`
- **Fallback Support**: Automatically falls back to workflow mode if needed

## Storage Configuration Options

The agent understands these Azure Storage Account configuration options:

### Performance Tiers
- **Standard**: Cost-effective for most use cases
- **Premium**: High-performance for databases and intensive workloads

### Access Tiers
- **Hot**: Frequently accessed data (websites, active applications)
- **Cool**: Infrequently accessed data (backups, older content)
- **Archive**: Rarely accessed data (compliance, long-term storage)

### Replication Types
- **LRS**: Locally Redundant Storage (cost-effective)
- **GRS**: Geo-Redundant Storage (disaster recovery)
- **ZRS**: Zone-Redundant Storage (high availability)

## Common Use Cases & Recommendations

| Use Case | Performance | Access Tier | Replication |
|----------|-------------|-------------|-------------|
| Website assets | Standard | Hot | LRS/ZRS |
| Images/media | Standard | Hot | LRS/ZRS |
| Backups | Standard | Cool | GRS |
| Log files | Standard | Cool | LRS |
| Archive/compliance | Standard | Archive | GRS |
| High-perf databases | Premium | Hot | ZRS |

## Development

### Project Status

✅ **Day 1: Local LLM Setup** - Complete
- Ollama integration with error handling
- Storage-specific prompts
- Comprehensive unit tests (26 tests)

✅ **Day 2: Simple JSON Memory System** - Complete  
- JSON-based user preference storage
- Conversation history management
- Storage-specific user profile with learning
- Context management for personalized responses
- Comprehensive unit tests (34 additional tests)

✅ **Day 3: Storage Decision Engine** - Complete
- Rule-based decision engine for storage configuration
- Use case detection from natural language input
- Intelligent configuration suggestions with confidence scoring
- Context-aware recommendations (production, compliance, security)
- Alternative configuration generation
- Comprehensive unit tests (94 additional tests)

✅ **Day 4: Agent Chat Interface** - Complete
- Agent-powered chat interface with conversational AI
- Integration of Ollama LLM with storage decision engine
- Structured conversation flow management with state tracking
- Natural language processing for storage requests
- Fallback to workflow mode when agent unavailable
- Special command handling (help, status, restart, exit)
- Comprehensive unit tests (462 additional scenario tests)

✅ **Day 5: Integration & Testing** - Complete
- Full integration with existing CLI using --agent flag
- Agent/workflow mode toggle with seamless fallback
- End-to-end testing covering all storage scenarios
- Simple feedback learning system for continuous improvement
- Learning from user interactions to improve future recommendations
- Persistent storage of user preferences and learning patterns
- Comprehensive test suite (33 additional integration tests)

🎯 **MVP Complete** - All 5 days delivered successfully!

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Agent-specific tests
python -m pytest tests/agent/ -v

# Integration test
python test_ollama_setup.py
```

### Code Quality

- **Test Coverage**: 649+ unit tests covering success, failure, and edge cases
- **Type Hints**: Full type annotations throughout
- **Documentation**: Comprehensive docstrings using Google style
- **Error Handling**: Graceful degradation when services unavailable
- **Memory Management**: Local JSON storage with backup capabilities
- **Learning System**: User preference learning from interactions
- **Decision Engine**: Intelligent configuration recommendations with confidence scoring
- **Context Awareness**: Production, compliance, and security-sensitive recommendations
- **Conversation Flow**: State machine-based conversation management
- **Agent Integration**: Natural language processing with LLM integration

## Troubleshooting

### Ollama Not Available

If you see "Ollama service is not available":

1. Check if Ollama is installed: `ollama --version`
2. Check if Ollama is running: `ollama list`
3. Start Ollama if needed (usually starts automatically)
4. Ensure a model is installed: `ollama pull llama3.1`

### Connection Issues

- Verify Ollama is running on default port 11434
- Check firewall settings if using custom configuration
- Try restarting Ollama service

### Test Failures

- Ensure all dependencies are installed: `pip install -r requirements-agent-simple.txt`
- Verify Python version compatibility (3.8+)
- Check that test files have proper permissions

### Memory/Data Issues

If you encounter issues with local data storage:

1. Check data directory permissions: The agent creates a `data/` folder automatically
2. Backup corrupted files: Use the backup functionality before troubleshooting
3. Reset preferences: Delete `data/user_preferences.json` to restore defaults
4. Clear history: Delete `data/conversation_history.json` to start fresh
5. Manual backup: Copy `data/` folder before major changes

## Architecture Notes

This is a **simple MVP** focused on:
- **Free services only** (Ollama, local JSON storage)
- **Storage Accounts only** (not other Azure resources)
- **Local execution** (no cloud dependencies)
- **Minimal complexity** (essential features only)

The agent uses a modular design that can be extended for more advanced features while maintaining the core simplicity and free operation model.

## Contributing

When extending the agent:
1. Follow the existing patterns in `src/agent/`
2. Add comprehensive unit tests for new features
3. Update this README for new capabilities
4. Keep files under 500 lines per project rules
5. Maintain focus on Azure Storage Accounts only