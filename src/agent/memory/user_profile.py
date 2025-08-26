"""
Storage-specific user profile management for the Azure Storage Agent.

Manages user preferences, learned patterns, and storage account history
to provide personalized storage recommendations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .json_memory import JSONMemory


class UserProfile:
    """
    Storage-focused user profile that learns from interactions.
    
    Tracks storage preferences, deployment patterns, and user feedback
    to provide increasingly personalized storage recommendations.
    """
    
    def __init__(self, memory: JSONMemory):
        """
        Initialize user profile with memory backend.
        
        Args:
            memory (JSONMemory): Memory system for data persistence.
        """
        self.memory = memory
    
    def get_preferred_regions(self) -> List[str]:
        """
        Get user's preferred Azure regions.
        
        Returns:
            List[str]: List of preferred region names.
        """
        return self.memory.get_preference("preferred_regions", ["eastus", "westus2"])
    
    def set_preferred_regions(self, regions: List[str]) -> None:
        """
        Set user's preferred Azure regions.
        
        Args:
            regions (List[str]): List of preferred region names.
        """
        self.memory.set_preference("preferred_regions", regions)
    
    def get_naming_pattern(self) -> str:
        """
        Get user's preferred naming pattern for storage accounts.
        
        Returns:
            str: Naming pattern preference ("descriptive", "short", "company").
        """
        return self.memory.get_preference("naming_pattern", "descriptive")
    
    def set_naming_pattern(self, pattern: str) -> None:
        """
        Set user's preferred naming pattern.
        
        Args:
            pattern (str): Naming pattern ("descriptive", "short", "company").
        """
        valid_patterns = ["descriptive", "short", "company"]
        if pattern not in valid_patterns:
            raise ValueError(f"Invalid naming pattern. Must be one of: {valid_patterns}")
        
        self.memory.set_preference("naming_pattern", pattern)
    
    def get_cost_preference(self) -> str:
        """
        Get user's cost optimization preference.
        
        Returns:
            str: Cost preference ("optimized", "balanced", "performance").
        """
        return self.memory.get_preference("cost_preference", "optimized")
    
    def set_cost_preference(self, preference: str) -> None:
        """
        Set user's cost optimization preference.
        
        Args:
            preference (str): Cost preference ("optimized", "balanced", "performance").
        """
        valid_preferences = ["optimized", "balanced", "performance"]
        if preference not in valid_preferences:
            raise ValueError(f"Invalid cost preference. Must be one of: {valid_preferences}")
        
        self.memory.set_preference("cost_preference", preference)
    
    def get_default_performance_tier(self) -> str:
        """
        Get user's default performance tier preference.
        
        Returns:
            str: Performance tier ("Standard" or "Premium").
        """
        return self.memory.get_preference("default_performance_tier", "Standard")
    
    def set_default_performance_tier(self, tier: str) -> None:
        """
        Set user's default performance tier preference.
        
        Args:
            tier (str): Performance tier ("Standard" or "Premium").
        """
        valid_tiers = ["Standard", "Premium"]
        if tier not in valid_tiers:
            raise ValueError(f"Invalid performance tier. Must be one of: {valid_tiers}")
        
        self.memory.set_preference("default_performance_tier", tier)
    
    def get_default_replication(self) -> str:
        """
        Get user's default replication preference.
        
        Returns:
            str: Replication type ("LRS", "GRS", "ZRS").
        """
        return self.memory.get_preference("default_replication", "LRS")
    
    def set_default_replication(self, replication: str) -> None:
        """
        Set user's default replication preference.
        
        Args:
            replication (str): Replication type ("LRS", "GRS", "ZRS").
        """
        valid_replications = ["LRS", "GRS", "ZRS"]
        if replication not in valid_replications:
            raise ValueError(f"Invalid replication type. Must be one of: {valid_replications}")
        
        self.memory.set_preference("default_replication", replication)
    
    def get_use_case_config(self, use_case: str) -> Optional[Dict[str, str]]:
        """
        Get learned configuration for specific use case.
        
        Args:
            use_case (str): Use case name (e.g., "images", "backups").
            
        Returns:
            Optional[Dict[str, str]]: Configuration or None if not learned.
        """
        return self.memory.get_use_case_pattern(use_case)
    
    def learn_use_case_config(self, use_case: str, config: Dict[str, str]) -> None:
        """
        Learn configuration preference for use case from user feedback.
        
        Args:
            use_case (str): Use case name.
            config (Dict[str, str]): Storage configuration that worked well.
        """
        self.memory.add_use_case_pattern(use_case, config)
    
    def suggest_storage_name(self, use_case: str, base_name: Optional[str] = None) -> str:
        """
        Suggest storage account name based on use case and naming pattern.
        
        Args:
            use_case (str): Storage use case.
            base_name (Optional[str]): Base name provided by user.
            
        Returns:
            str: Suggested storage account name.
        """
        pattern = self.get_naming_pattern()
        
        if base_name:
            return base_name
        
        if pattern == "descriptive":
            # Descriptive names based on use case
            use_case_names = {
                "images": "webapp-images-storage",
                "backups": "database-backup-storage", 
                "logs": "application-logs-storage",
                "website": "website-assets-storage",
                "data_lake": "analytics-data-lake",
                "archive": "compliance-archive-storage"
            }
            return use_case_names.get(use_case, f"{use_case}-storage")
        
        elif pattern == "short":
            # Short names with abbreviations
            use_case_short = {
                "images": "imgstore",
                "backups": "bkpstore", 
                "logs": "logstore",
                "website": "webstore",
                "data_lake": "dlstore",
                "archive": "arcstore"
            }
            timestamp = datetime.now().strftime("%m%d")
            return f"{use_case_short.get(use_case, 'store')}{timestamp}"
        
        elif pattern == "company":
            # Company/project prefix pattern
            company_prefix = self.memory.get_preference("company_prefix", "company")
            return f"{company_prefix}{use_case}storage"
        
        return f"{use_case}storage"
    
    def add_deployment_history(self, deployment: Dict[str, Any]) -> None:
        """
        Record successful storage account deployment for learning.
        
        Args:
            deployment (Dict[str, Any]): Deployment details including config and outcome.
        """
        entry = {
            "type": "deployment",
            "timestamp": datetime.now().isoformat(),
            "deployment": deployment
        }
        self.memory.add_conversation_entry(entry)
        
        # Learn from successful deployment
        if deployment.get("success") and deployment.get("use_case"):
            config = {
                "tier": deployment.get("access_tier"),
                "replication": deployment.get("replication_type"),
                "performance": deployment.get("performance_tier")
            }
            # Remove None values
            config = {k: v for k, v in config.items() if v is not None}
            if config:
                self.learn_use_case_config(deployment["use_case"], config)
    
    def add_feedback(self, feedback: Dict[str, Any]) -> None:
        """
        Record user feedback for future learning.
        
        Args:
            feedback (Dict[str, Any]): User feedback about suggestions or deployments.
        """
        entry = {
            "type": "feedback",
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback
        }
        self.memory.add_conversation_entry(entry)
        
        # Process feedback for learning
        if feedback.get("type") == "suggestion_rejected":
            suggestion = feedback.get("suggestion", {})
            reason = feedback.get("reason", "")
            
            # Learn from rejection patterns
            if "too expensive" in reason.lower():
                if self.get_cost_preference() != "optimized":
                    self.set_cost_preference("optimized")
            elif "too slow" in reason.lower() or "performance" in reason.lower():
                if self.get_cost_preference() != "performance":
                    self.set_cost_preference("performance")
    
    def get_context_for_conversation(self) -> Dict[str, Any]:
        """
        Get relevant context for current conversation.
        
        Returns:
            Dict[str, Any]: Context including preferences and recent history.
        """
        recent_deployments = []
        recent_conversations = self.memory.get_recent_conversations(5)
        
        for conv in recent_conversations:
            if conv.get("type") == "deployment" and conv.get("deployment", {}).get("success"):
                recent_deployments.append(conv["deployment"])
        
        return {
            "user_preferences": {
                "preferred_regions": self.get_preferred_regions(),
                "naming_pattern": self.get_naming_pattern(),
                "cost_preference": self.get_cost_preference(),
                "default_performance_tier": self.get_default_performance_tier(),
                "default_replication": self.get_default_replication()
            },
            "recent_deployments": recent_deployments[:3],  # Last 3 successful deployments
            "learned_patterns": self.memory.get_preference("use_case_patterns", {})
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get user profile summary for display or debugging.
        
        Returns:
            Dict[str, Any]: Complete user profile summary.
        """
        context = self.get_context_for_conversation()
        total_conversations = len(self.memory.get_conversation_history())
        deployments = [c for c in self.memory.get_conversation_history() 
                      if c.get("type") == "deployment"]
        successful_deployments = [d for d in deployments 
                                 if d.get("deployment", {}).get("success")]
        
        return {
            "preferences": context["user_preferences"],
            "learned_patterns": context["learned_patterns"],
            "stats": {
                "total_conversations": total_conversations,
                "total_deployments": len(deployments),
                "successful_deployments": len(successful_deployments)
            },
            "recent_activity": context["recent_deployments"]
        }


def create_user_profile(data_dir: str = "data") -> UserProfile:
    """
    Factory function to create UserProfile instance.
    
    Args:
        data_dir (str): Directory for storing profile data.
        
    Returns:
        UserProfile: Configured user profile instance.
    """
    from .json_memory import create_memory
    memory = create_memory(data_dir)
    return UserProfile(memory)