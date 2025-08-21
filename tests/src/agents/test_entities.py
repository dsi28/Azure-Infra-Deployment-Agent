"""
Unit tests for agents.entities module.

Tests for entity extraction including EntityExtractor, Entity models,
and various extraction scenarios with expected use cases, edge cases, and failures.
"""

import pytest
from src.agents.entities import (
    EntityType,
    Entity,
    ExtractedEntities,
    EntityExtractor
)


class TestEntityType:
    """Test cases for EntityType enum."""
    
    def test_entity_type_values(self):
        """Test EntityType enum values."""
        assert EntityType.RESOURCE_NAME.value == "resource_name"
        assert EntityType.REGION.value == "region"
        assert EntityType.RESOURCE_GROUP.value == "resource_group"
        assert EntityType.PERFORMANCE_TIER.value == "performance_tier"
        assert EntityType.REPLICATION_TYPE.value == "replication_type"
        assert EntityType.ACCESS_TIER.value == "access_tier"
        assert EntityType.RUNTIME_STACK.value == "runtime_stack"


class TestEntity:
    """Test cases for Entity model."""
    
    def test_entity_creation_success(self):
        """Test successful Entity creation."""
        entity = Entity(
            type=EntityType.RESOURCE_NAME,
            value="mystorage123",
            confidence=0.9,
            original_text="called mystorage123",
            start_pos=7,
            end_pos=19
        )
        
        assert entity.type == EntityType.RESOURCE_NAME
        assert entity.value == "mystorage123"
        assert entity.confidence == 0.9
        assert entity.original_text == "called mystorage123"
        assert entity.start_pos == 7
        assert entity.end_pos == 19
    
    def test_entity_minimal_creation(self):
        """Test Entity creation with minimal fields."""
        entity = Entity(
            type=EntityType.REGION,
            value="East US",
            original_text="east us"
        )
        
        assert entity.type == EntityType.REGION
        assert entity.value == "East US"
        assert entity.confidence == 0.8  # Default
        assert entity.original_text == "east us"
        assert entity.start_pos is None
        assert entity.end_pos is None
    
    def test_entity_invalid_confidence_failure(self):
        """Test Entity creation with invalid confidence fails."""
        with pytest.raises(ValueError):
            Entity(
                type=EntityType.REGION,
                value="East US",
                confidence=1.5,  # > 1.0
                original_text="east us"
            )
        
        with pytest.raises(ValueError):
            Entity(
                type=EntityType.REGION,
                value="East US", 
                confidence=-0.1,  # < 0.0
                original_text="east us"
            )


class TestExtractedEntities:
    """Test cases for ExtractedEntities container."""
    
    def test_extracted_entities_initialization(self):
        """Test ExtractedEntities initialization."""
        extracted = ExtractedEntities()
        
        assert extracted.entities == []
        assert extracted.confidence_threshold == 0.5
    
    def test_add_entity_success(self):
        """Test successful entity addition."""
        extracted = ExtractedEntities()
        entity = Entity(
            type=EntityType.RESOURCE_NAME,
            value="test",
            confidence=0.8,
            original_text="test"
        )
        
        extracted.add_entity(entity)
        
        assert len(extracted.entities) == 1
        assert extracted.entities[0] == entity
    
    def test_add_entity_below_threshold(self):
        """Test entity addition below confidence threshold."""
        extracted = ExtractedEntities(confidence_threshold=0.7)
        entity = Entity(
            type=EntityType.RESOURCE_NAME,
            value="test",
            confidence=0.5,  # Below threshold
            original_text="test"
        )
        
        extracted.add_entity(entity)
        
        assert len(extracted.entities) == 0
    
    def test_get_entities_by_type_success(self):
        """Test getting entities by type."""
        extracted = ExtractedEntities()
        
        entity1 = Entity(type=EntityType.RESOURCE_NAME, value="storage1", original_text="storage1")
        entity2 = Entity(type=EntityType.REGION, value="East US", original_text="east us")
        entity3 = Entity(type=EntityType.RESOURCE_NAME, value="storage2", original_text="storage2")
        
        extracted.add_entity(entity1)
        extracted.add_entity(entity2)
        extracted.add_entity(entity3)
        
        resource_names = extracted.get_entities_by_type(EntityType.RESOURCE_NAME)
        regions = extracted.get_entities_by_type(EntityType.REGION)
        
        assert len(resource_names) == 2
        assert len(regions) == 1
        assert entity1 in resource_names
        assert entity3 in resource_names
        assert entity2 in regions
    
    def test_get_best_entity_success(self):
        """Test getting the best entity by type."""
        extracted = ExtractedEntities()
        
        entity1 = Entity(type=EntityType.RESOURCE_NAME, value="storage1", confidence=0.7, original_text="storage1")
        entity2 = Entity(type=EntityType.RESOURCE_NAME, value="storage2", confidence=0.9, original_text="storage2")
        
        extracted.add_entity(entity1)
        extracted.add_entity(entity2)
        
        best = extracted.get_best_entity(EntityType.RESOURCE_NAME)
        
        assert best == entity2  # Higher confidence
        assert best.confidence == 0.9
    
    def test_get_best_entity_not_found(self):
        """Test getting best entity when type not found."""
        extracted = ExtractedEntities()
        
        best = extracted.get_best_entity(EntityType.REGION)
        
        assert best is None
    
    def test_get_entity_value_success(self):
        """Test getting entity value."""
        extracted = ExtractedEntities()
        entity = Entity(type=EntityType.REGION, value="West US", original_text="west us")
        extracted.add_entity(entity)
        
        value = extracted.get_entity_value(EntityType.REGION)
        
        assert value == "West US"
    
    def test_get_entity_value_not_found(self):
        """Test getting entity value when not found."""
        extracted = ExtractedEntities()
        
        value = extracted.get_entity_value(EntityType.REGION)
        
        assert value is None
    
    def test_has_entity_success(self):
        """Test checking entity existence."""
        extracted = ExtractedEntities()
        entity = Entity(type=EntityType.ACCESS_TIER, value="Hot", original_text="hot")
        extracted.add_entity(entity)
        
        assert extracted.has_entity(EntityType.ACCESS_TIER) is True
        assert extracted.has_entity(EntityType.REGION) is False
    
    def test_to_dict_success(self):
        """Test converting to dictionary."""
        extracted = ExtractedEntities()
        
        entity1 = Entity(type=EntityType.RESOURCE_NAME, value="mystorage", original_text="mystorage")
        entity2 = Entity(type=EntityType.REGION, value="East US", original_text="east us")
        
        extracted.add_entity(entity1)
        extracted.add_entity(entity2)
        
        result = extracted.to_dict()
        
        expected = {
            "resource_name": "mystorage",
            "region": "East US"
        }
        
        assert result == expected


class TestEntityExtractor:
    """Test cases for EntityExtractor class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.extractor = EntityExtractor()
    
    def test_entity_extractor_initialization(self):
        """Test EntityExtractor initialization."""
        extractor = EntityExtractor()
        
        assert extractor.region_patterns is not None
        assert extractor.performance_tier_patterns is not None
        assert extractor.replication_patterns is not None
        assert extractor.access_tier_patterns is not None
        assert extractor.runtime_stack_patterns is not None
        assert extractor.resource_name_patterns is not None
    
    def test_extract_regions_success(self):
        """Test successful region extraction."""
        text = "Deploy to East US and also create backup in West Europe"
        
        extracted = self.extractor.extract_entities(text)
        
        regions = extracted.get_entities_by_type(EntityType.REGION)
        assert len(regions) == 2
        
        region_values = [r.value for r in regions]
        assert "East US" in region_values
        assert "West Europe" in region_values
    
    def test_extract_regions_case_insensitive(self):
        """Test region extraction is case insensitive."""
        text = "I need storage in EAST US"
        
        extracted = self.extractor.extract_entities(text)
        
        region = extracted.get_entity_value(EntityType.REGION)
        assert region == "East US"
    
    def test_extract_performance_tiers_success(self):
        """Test successful performance tier extraction."""
        text = "Create a premium storage account with standard backup"
        
        extracted = self.extractor.extract_entities(text)
        
        tiers = extracted.get_entities_by_type(EntityType.PERFORMANCE_TIER)
        tier_values = [t.value for t in tiers]
        
        assert "Premium" in tier_values
        assert "Standard" in tier_values
    
    def test_extract_replication_types_success(self):
        """Test successful replication type extraction."""
        text = "Use LRS for primary and GRS for backup storage"
        
        extracted = self.extractor.extract_entities(text)
        
        replications = extracted.get_entities_by_type(EntityType.REPLICATION_TYPE)
        replication_values = [r.value for r in replications]
        
        assert "LRS" in replication_values
        assert "GRS" in replication_values
    
    def test_extract_access_tiers_success(self):
        """Test successful access tier extraction."""
        text = "Set the storage to hot tier for frequently accessed files"
        
        extracted = self.extractor.extract_entities(text)
        
        tier = extracted.get_entity_value(EntityType.ACCESS_TIER)
        assert tier == "Hot"
    
    def test_extract_runtime_stacks_success(self):
        """Test successful runtime stack extraction."""
        text = "Create a web app using Node.js and another with Python"
        
        extracted = self.extractor.extract_entities(text)
        
        stacks = extracted.get_entities_by_type(EntityType.RUNTIME_STACK)
        stack_values = [s.value for s in stacks]
        
        assert "NODE" in stack_values
        assert "PYTHON" in stack_values
    
    def test_extract_resource_names_success(self):
        """Test successful resource name extraction."""
        test_cases = [
            ("Create a storage account called mystorage123", "mystorage123"),
            ("I need a web app named testapp", "testapp"),
            ("Deploy myapp storage account", "myapp"),
            ("Create webapp123 web app", "webapp123")
        ]
        
        for text, expected_name in test_cases:
            extracted = self.extractor.extract_entities(text)
            name = extracted.get_entity_value(EntityType.RESOURCE_NAME)
            assert name == expected_name, f"Failed for text: {text}"
    
    def test_extract_multiple_entities_success(self):
        """Test extraction of multiple entity types from single text."""
        text = "Create a storage account called mystorage in East US with premium LRS and hot tier"
        
        extracted = self.extractor.extract_entities(text)
        
        assert extracted.get_entity_value(EntityType.RESOURCE_NAME) == "mystorage"
        assert extracted.get_entity_value(EntityType.REGION) == "East US"
        assert extracted.get_entity_value(EntityType.PERFORMANCE_TIER) == "Premium"
        assert extracted.get_entity_value(EntityType.REPLICATION_TYPE) == "LRS"
        assert extracted.get_entity_value(EntityType.ACCESS_TIER) == "Hot"
    
    def test_extract_no_entities_edge_case(self):
        """Test extraction when no entities are present."""
        text = "This is just random text with no Azure entities"
        
        extracted = self.extractor.extract_entities(text)
        
        assert len(extracted.entities) == 0
    
    def test_extract_entities_empty_text_edge_case(self):
        """Test extraction with empty text."""
        text = ""
        
        extracted = self.extractor.extract_entities(text)
        
        assert len(extracted.entities) == 0
    
    def test_extract_entities_whitespace_text_edge_case(self):
        """Test extraction with whitespace-only text."""
        text = "   \n\t   "
        
        extracted = self.extractor.extract_entities(text)
        
        assert len(extracted.entities) == 0
    
    def test_confidence_scoring(self):
        """Test that entities have appropriate confidence scores."""
        text = "Create storage in East US"
        
        extracted = self.extractor.extract_entities(text)
        
        region_entity = extracted.get_best_entity(EntityType.REGION)
        assert region_entity is not None
        assert 0.0 <= region_entity.confidence <= 1.0
        assert region_entity.confidence > 0.5  # Should be reasonably confident
    
    def test_entity_positions(self):
        """Test that entity positions are correctly captured."""
        text = "Deploy to East US region"
        
        extracted = self.extractor.extract_entities(text)
        
        region_entity = extracted.get_best_entity(EntityType.REGION)
        assert region_entity is not None
        assert region_entity.start_pos is not None
        assert region_entity.end_pos is not None
        assert region_entity.start_pos < region_entity.end_pos
    
    def test_special_characters_in_resource_names(self):
        """Test resource name extraction with valid special characters."""
        text = "Create storage account called my-storage_123"
        
        extracted = self.extractor.extract_entities(text)
        
        name = extracted.get_entity_value(EntityType.RESOURCE_NAME)
        assert name == "my-storage_123"


class TestEntityExtractionIntegration:
    """Integration tests for entity extraction functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.extractor = EntityExtractor()
    
    def test_task_test_cases_storage_account(self):
        """Test the specific test case from TASK.md: storage account intent."""
        text = "I need a storage account"
        
        extracted = self.extractor.extract_entities(text)
        
        # Should not extract any specific entities from this generic request
        assert len(extracted.entities) == 0
    
    def test_task_test_cases_web_app_with_name(self):
        """Test the specific test case from TASK.md: web app with name entity."""
        text = "Create a web app called myapp"
        
        extracted = self.extractor.extract_entities(text)
        
        name = extracted.get_entity_value(EntityType.RESOURCE_NAME)
        assert name == "myapp"
    
    def test_task_test_cases_region_entity(self):
        """Test the specific test case from TASK.md: region entity."""
        text = "Deploy to East US"
        
        extracted = self.extractor.extract_entities(text)
        
        region = extracted.get_entity_value(EntityType.REGION)
        assert region == "East US"
    
    def test_complex_real_world_scenario(self):
        """Test a complex real-world scenario with multiple entities."""
        text = ("I want to create a premium storage account named companydata123 "
               "in West US 2 with geo-redundant replication and cool access tier")
        
        extracted = self.extractor.extract_entities(text)
        
        assert extracted.get_entity_value(EntityType.RESOURCE_NAME) == "companydata123"
        assert extracted.get_entity_value(EntityType.REGION) == "West US 2"
        assert extracted.get_entity_value(EntityType.PERFORMANCE_TIER) == "Premium"
        assert extracted.get_entity_value(EntityType.REPLICATION_TYPE) == "GRS"
        assert extracted.get_entity_value(EntityType.ACCESS_TIER) == "Cool"
    
    def test_ambiguous_entities_handling(self):
        """Test handling of ambiguous or conflicting entities."""
        text = "Create standard premium storage in East US West Europe"
        
        extracted = self.extractor.extract_entities(text)
        
        # Should extract both performance tiers
        tiers = extracted.get_entities_by_type(EntityType.PERFORMANCE_TIER)
        tier_values = [t.value for t in tiers]
        assert "Standard" in tier_values
        assert "Premium" in tier_values
        
        # Should extract both regions
        regions = extracted.get_entities_by_type(EntityType.REGION)
        region_values = [r.value for r in regions]
        assert "East US" in region_values
        assert "West Europe" in region_values
        
        # Best entity should be the one with highest confidence
        best_tier = extracted.get_best_entity(EntityType.PERFORMANCE_TIER)
        assert best_tier is not None