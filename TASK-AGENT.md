# Azure Storage Agent - Simple MVP Tasks

## Week 1: Storage Agent MVP (5 Days)

### Day 1: Local LLM Setup ✅ COMPLETED
**Priority**: High | **Effort**: 4 hours

- [x] Install Ollama locally
- [x] Download and test Llama 3.1 or Mistral 7B model
- [x] Create basic Python wrapper for Ollama API
- [x] Test local LLM with simple storage-related prompts

**Files to Create**:
- `src/agent/llm/ollama_client.py` - Ollama API wrapper
- `src/agent/llm/storage_prompts.py` - Storage-specific prompts
- `requirements-agent-simple.txt` - Minimal agent dependencies

**Dependencies**:
```bash
# Install Ollama first
pip install requests  # For Ollama API calls
pip install langchain-community  # Free version only
```

**Acceptance Criteria**: ✅ ALL MET
- ✅ Ollama runs locally and responds to API calls
- ✅ Basic storage conversation works locally
- ✅ No external API calls required

### Day 2: Simple JSON Memory System ✅ COMPLETED
**Priority**: High | **Effort**: 4 hours

- [x] Create JSON-based user preference storage
- [x] Implement simple conversation history
- [x] Add basic context management for storage conversations
- [x] Create storage-specific user profile

**Files to Create**:
- `src/agent/memory/json_memory.py` - Simple file-based storage
- `src/agent/memory/user_profile.py` - Storage preferences
- `data/user_preferences.json` - User data file
- `data/conversation_history.json` - Chat history

**Storage Preferences to Track**:
```json
{
  "preferred_regions": ["eastus", "westus2"],
  "naming_pattern": "descriptive",
  "cost_preference": "optimized",
  "default_performance_tier": "Standard",
  "default_replication": "LRS",
  "use_case_patterns": {
    "images": {"tier": "Hot", "replication": "LRS"},
    "backups": {"tier": "Cool", "replication": "GRS"},
    "logs": {"tier": "Cool", "replication": "LRS"}
  }
}
```

**Acceptance Criteria**: ✅ ALL MET
- ✅ Preferences persist across sessions in JSON files
- ✅ Agent remembers previous storage account configurations
- ✅ Simple conversation context maintained
- ✅ No external database required

### Day 3: Storage Decision Engine ✅ COMPLETED
**Priority**: High | **Effort**: 6 hours

- [x] Create simple rule-based decision engine for storage
- [x] Implement use case detection (images, backups, logs, etc.)
- [x] Add configuration suggestion based on use case
- [x] Build simple confidence scoring

**Files to Create**:
- `src/agent/decision/storage_advisor.py` - Storage-specific decisions
- `src/agent/decision/use_case_detector.py` - Detect storage purpose
- `src/agent/decision/rules.py` - Simple decision rules

**Decision Rules**:
```python
USE_CASE_RULES = {
    "images": {"tier": "Hot", "performance": "Standard", "replication": "LRS"},
    "website": {"tier": "Hot", "performance": "Standard", "replication": "LRS"},
    "backups": {"tier": "Cool", "performance": "Standard", "replication": "GRS"},
    "logs": {"tier": "Cool", "performance": "Standard", "replication": "LRS"},
    "archive": {"tier": "Archive", "performance": "Standard", "replication": "GRS"},
    "data_lake": {"tier": "Cool", "performance": "Premium", "replication": "ZRS"}
}
```

**Acceptance Criteria**: ✅ ALL MET
- ✅ Agent detects storage use case from user input
- ✅ Suggests appropriate tier, performance, and replication
- ✅ Uses user preferences as defaults
- ✅ Simple confidence based on keyword matching

### Day 4: Agent Chat Interface ✅ COMPLETED
**Priority**: High | **Effort**: 6 hours

- [x] Create new agent-based chat interface alongside existing workflow
- [x] Integrate Ollama LLM with storage decision engine
- [x] Implement conversation flow for storage requests
- [x] Add fallback to workflow mode if agent fails

**Files Created**:
- `src/cli/agent_chat.py` - New agent-powered chat interface
- `src/agent/conversation/storage_conversation.py` - Storage conversation flow
- `src/agent/core/simple_agent.py` - Main agent orchestrator
- `tests/agent/test_storage_scenarios.py` - End-to-end scenario tests

**Conversation Flow**:
1. User: "I need storage for my blog images"
2. Agent uses LLM to understand request
3. Agent suggests configuration using decision engine
4. Agent confirms with user
5. Agent uses existing ARM deployer

**Acceptance Criteria**: ✅ ALL MET
- ✅ Agent mode available alongside workflow mode
- ✅ Natural conversation about storage needs
- ✅ Smart suggestions based on use case and preferences
- ✅ Graceful fallback if LLM unavailable
- ✅ State machine-based conversation flow management
- ✅ Special command handling (help, status, restart, exit)
- ✅ Comprehensive unit tests (462 additional scenario tests)

### Day 5: Integration & Testing ✅ COMPLETED
**Priority**: High | **Effort**: 6 hours

- [x] Integrate all agent components with existing CLI
- [x] Add agent/workflow mode toggle
- [x] Test end-to-end storage agent scenarios
- [x] Create basic learning from user feedback

**Files Created**:
- `src/main.py` - Updated with agent mode option (`--agent` flag)
- `src/agent/learning/simple_feedback.py` - Basic learning system
- `tests/agent/test_simple_feedback.py` - Learning system tests
- ✅ `tests/agent/test_storage_scenarios.py` - Agent test scenarios (completed in Day 4)

**Integration Tasks**: ✅ ALL COMPLETED
- ✅ Add `--agent` flag to enable agent mode
- ✅ Maintain full compatibility with existing workflow
- ✅ Test multiple storage scenarios
- ✅ Implement simple feedback learning

**Test Scenarios**: ✅ ALL TESTED
1. ✅ **Basic Request**: "I need a storage account"
2. ✅ **Use Case Specific**: "I need storage for my website images"  
3. ✅ **Context Aware**: "Create another storage account like the last one"
4. ✅ **Cost Conscious**: "I need cheap storage for backups"
5. ✅ **Performance Focused**: "I need fast storage for a database"

**Learning Implementation**: ✅ COMPLETED
- ✅ Track if user accepts/modifies suggestions
- ✅ Adjust future suggestions based on feedback
- ✅ Simple JSON-based learning (no ML required)
- ✅ Persistent storage of learning patterns
- ✅ Confidence adjustment based on success rate

**Acceptance Criteria**: ✅ ALL MET
- ✅ Agent mode works end-to-end for storage accounts
- ✅ Fallback to workflow mode if agent fails
- ✅ User preferences learned and applied
- ✅ All existing functionality preserved
- ✅ Comprehensive test coverage (649+ tests total)

## Sprint 2: Dual Recommendation System (Next Sprint)

### Enhancement 1: LLM + Rules Dual Decision Engine
**Priority**: High | **Effort**: 8 hours | **Date Added**: 2025-09-09

- [ ] Create LLM-based recommendation engine alongside existing rules
- [ ] Implement side-by-side recommendation comparison UI
- [ ] Add user choice tracking and preference learning
- [ ] Build confidence scoring for both recommendation types

**Files to Create**:
- `src/agent/decision/llm_advisor.py` - LLM-based storage recommendations
- `src/agent/decision/dual_recommender.py` - Orchestrate both recommendation systems
- `src/agent/conversation/dual_recommendation_ui.py` - Present both options to user
- `src/agent/learning/recommendation_feedback.py` - Track which recommendations users prefer

**Implementation Tasks**:
- [ ] Design LLM prompts with Azure storage expertise
- [ ] Create structured output parsing for LLM recommendations
- [ ] Build comparison UI showing both recommendations side-by-side
- [ ] Implement user choice collection and feedback learning
- [ ] Add fallback logic when LLM unavailable
- [ ] Create comprehensive tests for dual recommendation scenarios

**Example User Experience**:
```
User: "I need storage for high-traffic e-commerce product images"

🤖 AI Recommendation:          📋 Rule-Based:
- Hot tier                     - Hot tier  
- Premium performance          - Standard performance
- ZRS replication             - LRS replication
- "High-traffic needs Premium" - "Cost-effective for images"

Which would you prefer? (1) AI, (2) Rules, (3) Custom
```

**Acceptance Criteria**:
- [ ] Both LLM and rule-based recommendations generated for same input
- [ ] Clear side-by-side presentation of recommendations with reasoning
- [ ] User can choose between recommendations or create custom config
- [ ] System learns which recommendation type user prefers over time
- [ ] Graceful handling when LLM is unavailable (fallback to rules only)
- [ ] Performance remains under 15 seconds for dual recommendations

**Learning Opportunities**:
- [ ] Track recommendation acceptance rates (LLM vs Rules vs Custom)
- [ ] Identify patterns where LLM outperforms rules and vice versa
- [ ] Build user preference profiles for recommendation type selection
- [ ] Create confidence adjustments based on historical performance

## Future Enhancements (Post-Sprint 2)

### Enhancement 2: Better Conversation Flow
**Priority**: Medium | **Future Sprint**

- [ ] Handle conversation interruptions and topic changes
- [ ] Add support for multiple storage accounts in one conversation
- [ ] Implement conversation state persistence
- [ ] Better context management for longer conversations

### Enhancement 3: Advanced Learning
**Priority**: Medium | **Future Sprint**

- [ ] Pattern recognition in user preferences
- [ ] Cost optimization suggestions based on usage
- [ ] Performance recommendations based on access patterns
- [ ] Integration with Azure cost management APIs

### Enhancement 4: Enhanced Decision Making
**Priority**: Low | **Future Sprint**

- [ ] Integration with Azure pricing APIs for cost estimates
- [ ] Security best practices suggestions
- [ ] Lifecycle policy recommendations
- [ ] Multi-region deployment advice

## MVP Success Criteria

### Technical Success ✅ ALL ACHIEVED
- ✅ Ollama LLM runs locally and responds to storage queries
- ✅ JSON-based memory persists user preferences across sessions
- ✅ Agent suggests appropriate storage configurations based on use case
- ✅ Integration with existing ARM deployment system works
- ✅ Agent mode can be toggled on/off without breaking existing workflow

### User Experience Success ✅ ALL ACHIEVED
- ✅ Natural conversation about storage needs
- ✅ Smart suggestions reduce configuration time
- ✅ Agent remembers user preferences and patterns
- ✅ Fallback to workflow mode if agent fails
- ✅ User prefers agent mode for storage account creation

### Example Success Interaction
```
User: "I need storage for my e-commerce product images"
Agent: "I'll set up image storage for your e-commerce site. For product images, I recommend:
        - Hot access tier (fast customer loading)
        - Standard performance (cost-effective)
        - LRS replication (sufficient for product data)
        - East US (your preferred region)
        Should I call it 'ecommerce-product-images'?"
User: "Yes, deploy it"
Agent: "Deploying ecommerce-product-images storage account... ✓ Complete!"
```

## Installation & Setup

### Prerequisites
1. Install Ollama: https://ollama.ai
2. Download model: `ollama pull llama3.2:3b`
3. Install Python dependencies: `pip install -r requirements-agent-simple.txt`

### Running Agent Mode
```bash
# Agent mode (new)
python -m src.main --agent

# Workflow mode (existing)
python -m src.main
```

## Notes

- **Scope**: Storage accounts only - no other Azure resources
- **Cost**: Completely free - no external API calls
- **Fallback**: If agent fails, automatically falls back to existing workflow
- **Data**: All preferences stored locally in JSON files
- **Performance**: Depends on local hardware for LLM inference
- **Evolution**: Foundation for future enterprise agent capabilities