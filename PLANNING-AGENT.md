# Azure Storage Agent - Simple MVP Planning

## Vision

Transform the existing Azure Infrastructure workflow tool into a simple, intelligent storage agent that focuses exclusively on Azure Storage Account deployments. The agent will remember user preferences, make smart configuration decisions, and provide natural conversation for storage account management - all using free/local services.

## Core Objectives

- **Storage-Focused Intelligence**: Smart decision-making for storage account configurations only
- **Simple Memory**: Remember storage preferences and previous deployments locally
- **Natural Conversation**: Conversational interface for storage account requests
- **Local Learning**: Learn user patterns and preferences from interactions
- **Cost-Free Operation**: Use only free, local services (no external API costs)
- **Quick Implementation**: MVP deliverable in 1 week

## Architecture Overview

```
                    ┌─────────────────┐
                    │      User       │
                    │  Conversation   │
                    └─────────┬───────┘
                              │
                              ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ JSON Memory     │◀──▶│ Ollama LLM       │───▶│ Use Case        │
│ - User Prefs    │    │ (llama3.2:3b)    │    │ Detector        │
│ - Chat History  │    │                  │    │                 │
│ - Learning Data │    └──────────────────┘    └─────────┬───────┘
└─────────────────┘             │                       │
        ▲                       │                       ▼
        │                       ▼                ┌─────────────────┐
        │                ┌──────────────────┐    │ Storage Decision│
        │                │ Storage          │◀───│ Rules Engine    │
        │                │ Conversation     │    │                 │
        │                │ Manager          │    └─────────┬───────┘
        │                └──────────────────┘              │
        │                       │                         ▼
        │                       │                ┌─────────────────┐
        │                       │                │ Configuration   │
        │                       │                │ Suggestions     │
        │                       │                └─────────┬───────┘
        │                       │                          │
        │                       │                          ▼
        │                       │                ┌─────────────────┐
        │                       │                │ Config Ready    │
        │                       │                │ for Deployment  │
        │                       │                │ (Agent Output)  │
        │                       │                └─────────┬───────┘
        │                       │                          │
        │                       │                          ▼
        │                       │                ┌─────────────────┐
        └───────────────────────┼───────────────▶│ Simple Feedback │
                                │                │ Learning System │
                                │                └─────────────────┘
                                ▼
                        ┌─────────────────┐
                        │ Conversation    │
                        │ State Machine   │
                        │ (help, status,  │
                        │  restart, exit) │
                        └─────────────────┘
```

### Simple Agent Components

1. **Storage Agent (Local LLM)**: Ollama-based conversation and intent understanding
2. **Decision Engine (Rule-Based)**: Simple rules for storage account configuration selection
3. **Local Memory (JSON Files)**: File-based storage for user preferences and conversation history
4. **Storage Config Builder**: Enhanced parameter selection with agent intelligence
5. **Existing ARM Deployer**: Reuse current deployment infrastructure

## Technology Stack (Free/Local Only)

### Core Technologies
- **Language**: Python 3.9+ (existing)
- **Local LLM**: Ollama with Llama 3.1 or Mistral 7B (completely free)
- **Memory**: JSON files + Python dictionaries (no external database)
- **Infrastructure**: Existing ARM Templates and deployment system
- **Cloud Platform**: Microsoft Azure (existing authentication)

### Free Agent Libraries
- **Ollama**: Local LLM inference (no API costs)
- **LangChain Community**: Free version for basic agent patterns
- **JSON**: Built-in Python for simple data persistence
- **Existing Codebase**: Reuse current storage account and ARM deployment logic

### No External Dependencies
- **❌ No OpenAI API** → Use Ollama local models
- **❌ No Redis/PostgreSQL** → Use JSON files for persistence  
- **❌ No ChromaDB Cloud** → Simple in-memory context management
- **❌ No paid vector databases** → Basic string matching for context
- **❌ No external AI services** → Everything runs locally

### Development Tools (Existing)
- **IDE**: VS Code / Cursor (current setup)
- **Version Control**: Git (current)
- **Package Management**: pip + requirements.txt (current)
- **Testing**: pytest (current)

## Simple Agent Capabilities

### Storage-Focused Intelligence
- **Storage Context**: Remember previous storage account deployments and preferences
- **Use Case Understanding**: Parse storage requests like "for images", "for backups", "for data lake"
- **Smart Suggestions**: Auto-suggest configurations based on stated purpose
- **Simple Conversation**: Natural back-and-forth about storage needs

### Storage Decision Making
- **Tier Selection**: Choose Standard vs Premium based on performance needs
- **Replication Logic**: Select LRS, GRS, ZRS based on durability requirements
- **Access Tier**: Choose Hot, Cool, Archive based on access patterns
- **Region Preference**: Remember and suggest user's preferred regions

### Simple Learning
- **Preference Memory**: Remember naming patterns, preferred regions, cost preferences
- **Usage Patterns**: Learn from user feedback ("too expensive", "too slow")
- **Configuration History**: Track what configurations worked well for specific use cases
- **Simple Feedback**: Basic positive/negative feedback on suggestions

### No Complex Features
- **❌ No Multi-Resource**: Only storage accounts (no web apps, databases, etc.)
- **❌ No Architecture Planning**: Single resource deployment only
- **❌ No Proactive Analysis**: No scanning of existing infrastructure
- **❌ No Complex Learning**: Simple rule-based improvement only

## Supported Storage Scenarios

### Basic Storage Requests
- **Purpose-Driven**: "I need storage for my website images"
- **Simple Context**: "Create another storage account like the last one"
- **Use Case Specific**: "I need backup storage", "I need a data lake", "I need blob storage"

### Agent-Enhanced Experience
- **Smart Suggestions**: Agent suggests configuration based on use case
- **Memory-Based**: "Like last time, I'll use East US and Standard tier"
- **Cost-Aware**: "For backups, I'll suggest Cool tier to save costs"
- **Performance-Aware**: "For website assets, I'll suggest Hot tier for fast access"

### Example Conversations
```
User: "I need storage for my blog images"
Agent: "I'll create image storage for you. Based on website use, I suggest:
        - Hot access tier (fast loading)
        - Standard performance (cost-effective)  
        - LRS replication (sufficient for blog)
        - East US (your usual region)
        Name it 'blog-images-storage'?"

User: "Make it cheaper"
Agent: "I'll switch to Cool tier - 30% cheaper for images accessed less than monthly. 
        Good for blog archives. Proceed?"
```

## Constraints & Considerations

### Technical Constraints
- **Local Model Limits**: Ollama models have smaller context windows than GPT-4
- **Storage Scope**: Only Azure Storage Accounts (no other resource types)
- **Simple State**: JSON file-based persistence (no complex database operations)
- **Local Performance**: Model inference speed depends on local hardware

### Free Service Constraints
- **No API Costs**: Must work entirely with local/free services
- **Limited AI Capability**: Local models are less capable than cloud APIs
- **Simple Memory**: Basic JSON storage vs sophisticated vector databases
- **Manual Setup**: User must install Ollama locally

### User Experience Constraints
- **Simple Conversations**: Less sophisticated than cloud-based LLMs
- **Clear Scope**: Users must understand it's storage-only
- **Local Dependencies**: Requires local Ollama installation
- **Fallback Options**: Graceful degradation if local LLM unavailable

### Implementation Constraints
- **Quick MVP**: Must be implementable in 1 week
- **Minimal Changes**: Reuse existing codebase as much as possible
- **No Breaking Changes**: Don't disrupt current workflow functionality
- **Easy Rollback**: Ability to disable agent and return to workflow mode

## Implementation Phases

### Phase 1: Simple Storage Agent (1 Week)
- Set up Ollama with local LLM
- Create basic conversation interface with storage focus
- Implement JSON-based memory for user preferences
- Add smart storage configuration suggestions
- Integrate with existing ARM deployment system

### Future Phases (Optional)
- **Phase 2**: Enhanced conversation capabilities and better learning
- **Phase 3**: Web interface for easier interaction
- **Phase 4**: Migration to cloud-based LLMs if needed
- **Phase 5**: Expansion to other Azure resources (keeping storage expertise)

## Success Metrics (MVP)

### Simple Intelligence Metrics
- **Storage Decision Accuracy**: >80% of storage suggestions accepted by users
- **Preference Memory**: Successfully remember user preferences >70% of the time
- **Use Case Understanding**: Correctly identify storage use case >75% of the time

### User Experience Metrics
- **Conversation Quality**: Natural back-and-forth about storage needs
- **Setup Time**: Storage account creation 2x faster than workflow mode
- **User Preference**: User chooses agent mode over workflow mode
- **Error Reduction**: Fewer configuration mistakes due to smart suggestions

### Technical Metrics
- **Response Time**: <10 seconds for local LLM responses
- **Local Performance**: Works on standard development hardware
- **Reliability**: No crashes or data loss in JSON persistence
- **Compatibility**: Doesn't break existing deployment functionality

## Risk Mitigation (Simple)

### Local LLM Risks
- **Poor Responses**: Fallback to workflow mode if LLM unavailable or poor quality
- **Context Loss**: Keep context simple and validate important information
- **Hardware Limitations**: Graceful degradation on slower hardware

### Implementation Risks
- **Complexity Creep**: Keep scope strictly limited to storage accounts only
- **Breaking Changes**: Maintain backward compatibility with existing workflow
- **User Confusion**: Clear documentation about agent vs workflow modes

### Data Risks
- **Preference Loss**: Regular JSON file backups and validation
- **Privacy**: All data stays local (no cloud API calls with user data)

## Future Evolution Path

### Natural Next Steps
1. **Enhanced Local Models**: Try different Ollama models for better performance
2. **Better Memory**: More sophisticated preference learning and context management
3. **Multi-Resource**: Expand to web apps while keeping storage expertise
4. **Cloud Migration**: Move to Azure OpenAI when ready for paid services

### Microsoft Integration (Future)
- **Azure OpenAI**: Migrate from local Ollama to cloud-based models
- **Copilot Integration**: API wrapper for Microsoft ecosystem integration
- **Teams Bot**: Natural conversation within Microsoft Teams
- **Enterprise Features**: Multi-tenant, governance, compliance

### Key Advantages of Starting Simple
- **Prove Value**: Demonstrate agent concept with minimal investment
- **Learn Patterns**: Understand user needs and conversation flows
- **Build Foundation**: Create architecture that can evolve to enterprise
- **No Vendor Lock-in**: Local-first approach provides flexibility