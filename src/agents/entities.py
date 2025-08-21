"""
Entity extraction and management for Azure Infrastructure Agent.

This module defines data structures for entities extracted from user input,
including resource names, regions, and other configuration parameters.
"""

import re
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class EntityType(Enum):
    """Enumeration of supported entity types."""
    RESOURCE_NAME = "resource_name"
    REGION = "region"
    RESOURCE_GROUP = "resource_group"
    SKU = "sku"
    PRICING_TIER = "pricing_tier"
    PERFORMANCE_TIER = "performance_tier"
    REPLICATION_TYPE = "replication_type"
    ACCESS_TIER = "access_tier"
    RUNTIME_STACK = "runtime_stack"
    APP_SERVICE_PLAN = "app_service_plan"
    SUBSCRIPTION_ID = "subscription_id"
    TAG_KEY = "tag_key"
    TAG_VALUE = "tag_value"


class Entity(BaseModel):
    """
    Represents an extracted entity from user input.
    
    An entity is a meaningful piece of information extracted from natural language
    that corresponds to an Azure resource parameter or configuration value.
    """
    
    type: EntityType
    value: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    original_text: str
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ExtractedEntities(BaseModel):
    """
    Container for all entities extracted from a single user input.
    
    This class organizes extracted entities by type for easy access
    and provides methods for validation and conversion.
    """
    
    entities: List[Entity] = Field(default_factory=list)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    
    def add_entity(self, entity: Entity) -> None:
        """
        Add an entity to the collection.
        
        Args:
            entity (Entity): The entity to add.
        """
        if entity.confidence >= self.confidence_threshold:
            self.entities.append(entity)
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """
        Get all entities of a specific type.
        
        Args:
            entity_type (EntityType): The type of entities to retrieve.
            
        Returns:
            List[Entity]: List of entities of the specified type.
        """
        return [e for e in self.entities if e.type == entity_type]
    
    def get_best_entity(self, entity_type: EntityType) -> Optional[Entity]:
        """
        Get the highest confidence entity of a specific type.
        
        Args:
            entity_type (EntityType): The type of entity to retrieve.
            
        Returns:
            Optional[Entity]: The best entity of the type, or None if not found.
        """
        candidates = self.get_entities_by_type(entity_type)
        if not candidates:
            return None
        
        return max(candidates, key=lambda e: e.confidence)
    
    def get_entity_value(self, entity_type: EntityType) -> Optional[str]:
        """
        Get the value of the best entity of a specific type.
        
        Args:
            entity_type (EntityType): The type of entity to retrieve.
            
        Returns:
            Optional[str]: The entity value, or None if not found.
        """
        entity = self.get_best_entity(entity_type)
        return entity.value if entity else None
    
    def has_entity(self, entity_type: EntityType) -> bool:
        """
        Check if any entity of the specified type exists.
        
        Args:
            entity_type (EntityType): The type of entity to check for.
            
        Returns:
            bool: True if entity exists, False otherwise.
        """
        return bool(self.get_entities_by_type(entity_type))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert extracted entities to a dictionary format.
        
        Returns:
            Dict[str, Any]: Dictionary with entity types as keys and values as values.
        """
        result = {}
        for entity_type in EntityType:
            entity_value = self.get_entity_value(entity_type)
            if entity_value:
                result[entity_type.value] = entity_value
        
        return result


class EntityExtractor:
    """
    Base class for entity extraction from natural language text.
    
    This class provides keyword-based entity extraction using predefined
    patterns and mappings for common Azure resource parameters.
    """
    
    def __init__(self):
        """Initialize the entity extractor with predefined patterns."""
        self._initialize_patterns()
    
    def _initialize_patterns(self) -> None:
        """Initialize regex patterns and keyword mappings for entity extraction."""
        
        # Azure regions mapping
        self.region_patterns = {
            # US regions
            r'\beast\s*us\b': 'East US',
            r'\bwest\s*us\b': 'West US',
            r'\bcentral\s*us\b': 'Central US',
            r'\bsouth\s*central\s*us\b': 'South Central US',
            r'\bnorth\s*central\s*us\b': 'North Central US',
            r'\beast\s*us\s*2\b': 'East US 2',
            r'\bwest\s*us\s*2\b': 'West US 2',
            r'\bwest\s*central\s*us\b': 'West Central US',
            
            # Europe regions
            r'\bnorth\s*europe\b': 'North Europe',
            r'\bwest\s*europe\b': 'West Europe',
            r'\buk\s*south\b': 'UK South',
            r'\buk\s*west\b': 'UK West',
            r'\bfrance\s*central\b': 'France Central',
            r'\bgermany\s*west\s*central\b': 'Germany West Central',
            
            # Asia Pacific regions
            r'\bsoutheast\s*asia\b': 'Southeast Asia',
            r'\beast\s*asia\b': 'East Asia',
            r'\bjapan\s*east\b': 'Japan East',
            r'\bjapan\s*west\b': 'Japan West',
            r'\baustralia\s*east\b': 'Australia East',
            r'\baustralia\s*southeast\b': 'Australia Southeast',
        }
        
        # Performance tiers
        self.performance_tier_patterns = {
            r'\bstandard\b': 'Standard',
            r'\bpremium\b': 'Premium',
            r'\bbasic\b': 'Basic',
        }
        
        # Replication types
        self.replication_patterns = {
            r'\blrs\b': 'LRS',
            r'\bgrs\b': 'GRS',
            r'\bragrs\b': 'RA-GRS',
            r'\bzrs\b': 'ZRS',
            r'\bgzrs\b': 'GZRS',
            r'\bragrz\b': 'RA-GZRS',
            r'\blocally\s*redundant\b': 'LRS',
            r'\bgeo\s*redundant\b': 'GRS',
            r'\bzone\s*redundant\b': 'ZRS',
        }
        
        # Access tiers
        self.access_tier_patterns = {
            r'\bhot\b': 'Hot',
            r'\bcool\b': 'Cool',
            r'\barchive\b': 'Archive',
        }
        
        # Runtime stacks for web apps
        self.runtime_stack_patterns = {
            r'\bnode\.?js\b': 'NODE',
            r'\bpython\b': 'PYTHON',
            r'\bdotnet\b': 'DOTNET',
            r'\b\.net\b': 'DOTNET',
            r'\bc#\b': 'DOTNET',
            r'\bjava\b': 'JAVA',
            r'\bphp\b': 'PHP',
            r'\bruby\b': 'RUBY',
        }
        
        # Resource name patterns (alphanumeric with hyphens)
        self.resource_name_patterns = [
            r'\bcalled\s+([a-zA-Z0-9\-_]+)\b',
            r'\bnamed\s+([a-zA-Z0-9\-_]+)\b',
            r'\bname\s+([a-zA-Z0-9\-_]+)\b',
            r'\b([a-zA-Z0-9\-_]+)\s+storage\s+account\b',
            r'\b([a-zA-Z0-9\-_]+)\s+web\s+app\b',
        ]
    
    def extract_entities(self, text: str) -> ExtractedEntities:
        """
        Extract entities from the given text.
        
        Args:
            text (str): The input text to extract entities from.
            
        Returns:
            ExtractedEntities: Container with all extracted entities.
        """
        extracted = ExtractedEntities()
        text_lower = text.lower()
        
        # Extract regions
        self._extract_regions(text_lower, text, extracted)
        
        # Extract performance tiers
        self._extract_performance_tiers(text_lower, text, extracted)
        
        # Extract replication types
        self._extract_replication_types(text_lower, text, extracted)
        
        # Extract access tiers
        self._extract_access_tiers(text_lower, text, extracted)
        
        # Extract runtime stacks
        self._extract_runtime_stacks(text_lower, text, extracted)
        
        # Extract resource names
        self._extract_resource_names(text_lower, text, extracted)
        
        return extracted
    
    def _extract_regions(self, text_lower: str, original_text: str, extracted: ExtractedEntities) -> None:
        """Extract Azure region entities from text."""
        for pattern, region_name in self.region_patterns.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.REGION,
                    value=region_name,
                    original_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9
                )
                extracted.add_entity(entity)
    
    def _extract_performance_tiers(self, text_lower: str, original_text: str, extracted: ExtractedEntities) -> None:
        """Extract performance tier entities from text."""
        for pattern, tier in self.performance_tier_patterns.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.PERFORMANCE_TIER,
                    value=tier,
                    original_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.8
                )
                extracted.add_entity(entity)
    
    def _extract_replication_types(self, text_lower: str, original_text: str, extracted: ExtractedEntities) -> None:
        """Extract replication type entities from text."""
        for pattern, replication in self.replication_patterns.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.REPLICATION_TYPE,
                    value=replication,
                    original_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.8
                )
                extracted.add_entity(entity)
    
    def _extract_access_tiers(self, text_lower: str, original_text: str, extracted: ExtractedEntities) -> None:
        """Extract access tier entities from text."""
        for pattern, tier in self.access_tier_patterns.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.ACCESS_TIER,
                    value=tier,
                    original_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.8
                )
                extracted.add_entity(entity)
    
    def _extract_runtime_stacks(self, text_lower: str, original_text: str, extracted: ExtractedEntities) -> None:
        """Extract runtime stack entities from text."""
        for pattern, stack in self.runtime_stack_patterns.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.RUNTIME_STACK,
                    value=stack,
                    original_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.8
                )
                extracted.add_entity(entity)
    
    def _extract_resource_names(self, text_lower: str, original_text: str, extracted: ExtractedEntities) -> None:
        """Extract resource name entities from text."""
        for pattern in self.resource_name_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                # Get the captured group (the actual name)
                if match.groups():
                    name = match.group(1)
                    entity = Entity(
                        type=EntityType.RESOURCE_NAME,
                        value=name,
                        original_text=match.group(),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.9
                    )
                    extracted.add_entity(entity)