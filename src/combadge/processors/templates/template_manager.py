"""Template Manager for Fleet Operations

Advanced template management system that loads, caches, and manages JSON templates
with versioning, metadata tracking, and dynamic template discovery.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import threading
from collections import defaultdict

from ...core.logging_manager import LoggingManager


@dataclass
class TemplateMetadata:
    """Metadata for a JSON template."""
    name: str
    version: str
    category: str
    description: str
    file_path: str
    required_entities: List[str] = field(default_factory=list)
    optional_entities: List[str] = field(default_factory=list)
    api_endpoint: Optional[str] = None
    http_method: str = "POST"
    template_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    usage_count: int = 0
    success_rate: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    
@dataclass 
class TemplateUsageStats:
    """Usage statistics for templates."""
    total_uses: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    last_used: Optional[datetime] = None
    average_generation_time: float = 0.0
    error_patterns: Dict[str, int] = field(default_factory=dict)


@dataclass
class TemplateRegistry:
    """Registry of all loaded templates."""
    templates: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, TemplateMetadata] = field(default_factory=dict)
    usage_stats: Dict[str, TemplateUsageStats] = field(default_factory=dict)
    categories: Dict[str, List[str]] = field(default_factory=dict)
    version_map: Dict[str, List[str]] = field(default_factory=dict)
    

class TemplateManager:
    """Advanced template manager with loading, caching, and versioning."""
    
    def __init__(self, templates_directory: Optional[str] = None):
        """Initialize template manager.
        
        Args:
            templates_directory: Directory containing template files
        """
        self.logger = LoggingManager.get_logger(__name__)
        
        # Set templates directory
        if templates_directory:
            self.templates_dir = Path(templates_directory)
        else:
            # Default to knowledge/templates relative to project root
            project_root = Path(__file__).parents[4]
            self.templates_dir = project_root / "knowledge" / "templates"
        
        # Initialize registry
        self.registry = TemplateRegistry()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Template cache settings
        self.enable_caching = True
        self.auto_reload = True
        self.reload_interval = 300  # 5 minutes
        
        # Template discovery patterns
        self.template_extensions = {".json", ".yaml", ".yml"}
        self.ignore_patterns = {"*.bak", "*~", ".*", "__*"}
        
        # Initialize templates
        self._last_reload = None
        self.load_templates()
        
    def load_templates(self, force_reload: bool = False) -> bool:
        """Load all templates from the templates directory.
        
        Args:
            force_reload: Force reload even if recently loaded
            
        Returns:
            True if templates loaded successfully
        """
        with self._lock:
            current_time = datetime.now()
            
            # Check if reload is needed
            if (not force_reload and self._last_reload and 
                (current_time - self._last_reload).seconds < self.reload_interval):
                return True
            
            self.logger.info(f"Loading templates from: {self.templates_dir}")
            
            if not self.templates_dir.exists():
                self.logger.error(f"Templates directory not found: {self.templates_dir}")
                return False
            
            loaded_count = 0
            error_count = 0
            
            # Walk through directory structure
            for template_file in self._discover_template_files():
                try:
                    if self._load_single_template(template_file):
                        loaded_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    self.logger.error(f"Error loading template {template_file}: {e}")
                    error_count += 1
            
            # Update categories and version maps
            self._update_registry_indexes()
            
            self._last_reload = current_time
            
            self.logger.info(
                f"Template loading complete: {loaded_count} loaded, {error_count} errors"
            )
            
            return error_count == 0
    
    def _discover_template_files(self) -> List[Path]:
        """Discover all template files in the directory structure.
        
        Returns:
            List of template file paths
        """
        template_files = []
        
        for root, dirs, files in os.walk(self.templates_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                
                # Check extension
                if file_path.suffix not in self.template_extensions:
                    continue
                
                # Check ignore patterns
                if any(file_path.match(pattern) for pattern in self.ignore_patterns):
                    continue
                
                template_files.append(file_path)
        
        return sorted(template_files)
    
    def _load_single_template(self, template_file: Path) -> bool:
        """Load a single template file.
        
        Args:
            template_file: Path to template file
            
        Returns:
            True if loaded successfully
        """
        try:
            # Read template file
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            # Extract metadata
            metadata_dict = template_data.get('template_metadata', {})
            template_content = template_data.get('template', {})
            validation_rules = template_data.get('validation_rules', {})
            
            # Create metadata object
            metadata = TemplateMetadata(
                name=metadata_dict.get('name', template_file.stem),
                version=metadata_dict.get('version', '1.0'),
                category=metadata_dict.get('category', 'general'),
                description=metadata_dict.get('description', ''),
                file_path=str(template_file),
                required_entities=metadata_dict.get('required_entities', []),
                optional_entities=metadata_dict.get('optional_entities', []),
                api_endpoint=metadata_dict.get('api_endpoint'),
                http_method=metadata_dict.get('http_method', 'POST'),
                created_at=datetime.fromtimestamp(template_file.stat().st_ctime),
                last_modified=datetime.fromtimestamp(template_file.stat().st_mtime),
                dependencies=metadata_dict.get('dependencies', []),
                tags=metadata_dict.get('tags', [])
            )
            
            # Calculate template hash
            template_json = json.dumps(template_content, sort_keys=True)
            metadata.template_hash = hashlib.md5(template_json.encode()).hexdigest()
            
            # Create template ID
            template_id = f"{metadata.category}.{metadata.name}.{metadata.version}"
            
            # Store template and metadata
            self.registry.templates[template_id] = {
                'content': template_content,
                'validation_rules': validation_rules,
                'raw_data': template_data
            }
            self.registry.metadata[template_id] = metadata
            
            # Initialize usage stats if not exists
            if template_id not in self.registry.usage_stats:
                self.registry.usage_stats[template_id] = TemplateUsageStats()
            
            self.logger.debug(f"Loaded template: {template_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load template {template_file}: {e}")
            return False
    
    def _update_registry_indexes(self):
        """Update category and version indexes in registry."""
        self.registry.categories.clear()
        self.registry.version_map.clear()
        
        for template_id, metadata in self.registry.metadata.items():
            # Update categories
            if metadata.category not in self.registry.categories:
                self.registry.categories[metadata.category] = []
            self.registry.categories[metadata.category].append(template_id)
            
            # Update version map
            base_name = f"{metadata.category}.{metadata.name}"
            if base_name not in self.registry.version_map:
                self.registry.version_map[base_name] = []
            self.registry.version_map[base_name].append(template_id)
        
        # Sort versions for each template
        for base_name in self.registry.version_map:
            self.registry.version_map[base_name].sort(
                key=lambda tid: self.registry.metadata[tid].version,
                reverse=True  # Latest version first
            )
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template data or None if not found
        """
        with self._lock:
            return self.registry.templates.get(template_id)
    
    def get_template_metadata(self, template_id: str) -> Optional[TemplateMetadata]:
        """Get template metadata.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template metadata or None if not found
        """
        with self._lock:
            return self.registry.metadata.get(template_id)
    
    def find_templates_by_category(self, category: str) -> List[str]:
        """Find templates by category.
        
        Args:
            category: Template category
            
        Returns:
            List of template IDs in the category
        """
        with self._lock:
            return self.registry.categories.get(category, []).copy()
    
    def find_templates_by_name(self, name: str, category: Optional[str] = None) -> List[str]:
        """Find templates by name (all versions).
        
        Args:
            name: Template name
            category: Optional category filter
            
        Returns:
            List of template IDs matching the name
        """
        with self._lock:
            if category:
                base_name = f"{category}.{name}"
            else:
                # Search all categories
                matching_templates = []
                for base_name, template_ids in self.registry.version_map.items():
                    if base_name.endswith(f".{name}"):
                        matching_templates.extend(template_ids)
                return matching_templates
            
            return self.registry.version_map.get(base_name, []).copy()
    
    def get_latest_template(self, name: str, category: str) -> Optional[str]:
        """Get latest version of a template.
        
        Args:
            name: Template name
            category: Template category
            
        Returns:
            Latest template ID or None if not found
        """
        base_name = f"{category}.{name}"
        versions = self.registry.version_map.get(base_name, [])
        return versions[0] if versions else None
    
    def search_templates(self, 
                        query: Optional[str] = None,
                        category: Optional[str] = None,
                        required_entities: Optional[List[str]] = None,
                        tags: Optional[List[str]] = None) -> List[str]:
        """Search templates based on criteria.
        
        Args:
            query: Text query to search in name/description
            category: Category filter
            required_entities: Required entities filter
            tags: Tags filter
            
        Returns:
            List of matching template IDs
        """
        with self._lock:
            matching_templates = []
            
            for template_id, metadata in self.registry.metadata.items():
                # Category filter
                if category and metadata.category != category:
                    continue
                
                # Text query filter
                if query:
                    query_lower = query.lower()
                    searchable_text = (
                        f"{metadata.name} {metadata.description} "
                        f"{' '.join(metadata.tags)}"
                    ).lower()
                    if query_lower not in searchable_text:
                        continue
                
                # Required entities filter
                if required_entities:
                    available_entities = set(metadata.required_entities + metadata.optional_entities)
                    if not set(required_entities).issubset(available_entities):
                        continue
                
                # Tags filter
                if tags:
                    if not set(tags).intersection(set(metadata.tags)):
                        continue
                
                matching_templates.append(template_id)
            
            # Sort by usage stats and relevance
            matching_templates.sort(key=lambda tid: (
                self.registry.usage_stats[tid].successful_uses,
                -self.registry.usage_stats[tid].failed_uses,
                self.registry.metadata[tid].name
            ), reverse=True)
            
            return matching_templates
    
    def record_template_usage(self, template_id: str, success: bool = True, 
                             generation_time: float = 0.0, error_type: Optional[str] = None):
        """Record template usage statistics.
        
        Args:
            template_id: Template identifier
            success: Whether the usage was successful
            generation_time: Time taken to generate
            error_type: Type of error if failed
        """
        with self._lock:
            if template_id not in self.registry.usage_stats:
                self.registry.usage_stats[template_id] = TemplateUsageStats()
            
            stats = self.registry.usage_stats[template_id]
            stats.total_uses += 1
            stats.last_used = datetime.now()
            
            if success:
                stats.successful_uses += 1
            else:
                stats.failed_uses += 1
                if error_type:
                    stats.error_patterns[error_type] = stats.error_patterns.get(error_type, 0) + 1
            
            # Update average generation time
            if generation_time > 0:
                total_time = stats.average_generation_time * (stats.total_uses - 1) + generation_time
                stats.average_generation_time = total_time / stats.total_uses
            
            # Update metadata usage count and success rate
            if template_id in self.registry.metadata:
                metadata = self.registry.metadata[template_id]
                metadata.usage_count = stats.total_uses
                metadata.success_rate = stats.successful_uses / stats.total_uses if stats.total_uses > 0 else 1.0
    
    def get_template_stats(self, template_id: str) -> Optional[TemplateUsageStats]:
        """Get usage statistics for a template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Usage statistics or None if not found
        """
        with self._lock:
            return self.registry.usage_stats.get(template_id)
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of template registry.
        
        Returns:
            Registry summary statistics
        """
        with self._lock:
            total_templates = len(self.registry.templates)
            total_categories = len(self.registry.categories)
            
            # Usage statistics
            total_uses = sum(stats.total_uses for stats in self.registry.usage_stats.values())
            total_successes = sum(stats.successful_uses for stats in self.registry.usage_stats.values())
            
            # Most used templates
            most_used = sorted(
                self.registry.usage_stats.keys(),
                key=lambda tid: self.registry.usage_stats[tid].total_uses,
                reverse=True
            )[:5]
            
            # Best performing templates
            best_performing = sorted(
                [tid for tid, stats in self.registry.usage_stats.items() if stats.total_uses >= 5],
                key=lambda tid: self.registry.usage_stats[tid].successful_uses / max(1, self.registry.usage_stats[tid].total_uses),
                reverse=True
            )[:5]
            
            return {
                "total_templates": total_templates,
                "total_categories": total_categories,
                "categories": list(self.registry.categories.keys()),
                "total_usage": total_uses,
                "success_rate": total_successes / max(1, total_uses),
                "most_used_templates": most_used,
                "best_performing_templates": best_performing,
                "last_reload": self._last_reload.isoformat() if self._last_reload else None,
                "templates_directory": str(self.templates_dir)
            }
    
    def validate_template_structure(self, template_id: str) -> Dict[str, Any]:
        """Validate template structure and completeness.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Validation result with issues and recommendations
        """
        template_data = self.get_template(template_id)
        metadata = self.get_template_metadata(template_id)
        
        if not template_data or not metadata:
            return {
                "valid": False,
                "errors": ["Template not found"],
                "warnings": [],
                "recommendations": []
            }
        
        errors = []
        warnings = []
        recommendations = []
        
        # Check required fields in template content
        template_content = template_data['content']
        validation_rules = template_data.get('validation_rules', {})
        
        # Check for required entities in template
        for entity in metadata.required_entities:
            if f"{{{entity}}}" not in json.dumps(template_content):
                errors.append(f"Required entity '{entity}' not found in template")
        
        # Check validation rules consistency
        for entity in metadata.required_entities + metadata.optional_entities:
            if entity not in validation_rules:
                warnings.append(f"No validation rule found for entity '{entity}'")
        
        # Check for unused validation rules
        template_json = json.dumps(template_content)
        for rule_entity in validation_rules:
            if f"{{{rule_entity}}}" not in template_json:
                warnings.append(f"Validation rule for '{rule_entity}' but entity not used in template")
        
        # Check metadata completeness
        if not metadata.description:
            recommendations.append("Add description to template metadata")
        
        if not metadata.api_endpoint:
            recommendations.append("Add API endpoint to template metadata")
        
        if not metadata.tags:
            recommendations.append("Add tags to improve template discoverability")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "recommendations": recommendations,
            "template_id": template_id,
            "validation_timestamp": datetime.now().isoformat()
        }
    
    def export_templates_catalog(self) -> Dict[str, Any]:
        """Export complete templates catalog with metadata.
        
        Returns:
            Complete templates catalog
        """
        with self._lock:
            catalog = {
                "export_timestamp": datetime.now().isoformat(),
                "templates_directory": str(self.templates_dir),
                "summary": self.get_registry_summary(),
                "templates": {}
            }
            
            for template_id in self.registry.templates:
                metadata = self.registry.metadata[template_id]
                stats = self.registry.usage_stats.get(template_id, TemplateUsageStats())
                
                catalog["templates"][template_id] = {
                    "metadata": {
                        "name": metadata.name,
                        "version": metadata.version,
                        "category": metadata.category,
                        "description": metadata.description,
                        "required_entities": metadata.required_entities,
                        "optional_entities": metadata.optional_entities,
                        "api_endpoint": metadata.api_endpoint,
                        "http_method": metadata.http_method,
                        "tags": metadata.tags,
                        "dependencies": metadata.dependencies
                    },
                    "usage_stats": {
                        "total_uses": stats.total_uses,
                        "successful_uses": stats.successful_uses,
                        "failed_uses": stats.failed_uses,
                        "success_rate": stats.successful_uses / max(1, stats.total_uses),
                        "average_generation_time": stats.average_generation_time,
                        "last_used": stats.last_used.isoformat() if stats.last_used else None
                    },
                    "file_info": {
                        "file_path": metadata.file_path,
                        "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
                        "last_modified": metadata.last_modified.isoformat() if metadata.last_modified else None,
                        "template_hash": metadata.template_hash
                    }
                }
            
            return catalog
    
    def reload_if_needed(self):
        """Reload templates if auto-reload is enabled and interval has passed."""
        if self.auto_reload:
            current_time = datetime.now()
            if (not self._last_reload or 
                (current_time - self._last_reload).seconds >= self.reload_interval):
                self.load_templates()
    
    def get_all_templates_metadata(self) -> List[TemplateMetadata]:
        """Get metadata for all loaded templates.
        
        Returns:
            List of TemplateMetadata objects for all templates
        """
        with self._lock:
            return list(self.registry.metadata.values())
    
    def get_templates_by_category(self) -> Dict[str, List[TemplateMetadata]]:
        """Get templates organized by category.
        
        Returns:
            Dictionary mapping categories to lists of template metadata
        """
        with self._lock:
            result = defaultdict(list)
            for metadata in self.registry.metadata.values():
                result[metadata.category].append(metadata)
            return dict(result)
    
    def cleanup(self):
        """Cleanup template manager resources."""
        self.logger.info("Cleaning up template manager")
        with self._lock:
            self.registry.templates.clear()
            self.registry.metadata.clear()
            self.registry.usage_stats.clear()
            self.registry.categories.clear()
            self.registry.version_map.clear()