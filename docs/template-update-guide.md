# Template Update Guide

This guide explains how to update ComBadge templates with correct API documentation and maintain the template system as your API endpoints evolve.

## Overview

The ComBadge template system uses JSON templates that define the structure and validation rules for API requests. This guide covers:

1. Understanding template structure
2. Updating existing templates
3. Adding new templates
4. API documentation integration
5. Validation and testing
6. Best practices

## Template Structure

### Basic Template Format

Each template is a JSON file with three main sections:

```json
{
  "template_metadata": {
    "name": "template_name",
    "version": "1.0",
    "category": "category_name",
    "description": "Description of what this template does",
    "required_entities": ["entity1", "entity2"],
    "optional_entities": ["entity3", "entity4"],
    "api_endpoint": "/api/v1/endpoint",
    "http_method": "POST",
    "tags": ["tag1", "tag2"],
    "dependencies": []
  },
  "template": {
    // JSON structure with variable placeholders
  },
  "validation_rules": {
    // Field validation rules
  }
}
```

### Template Metadata Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `name` | ✓ | Template identifier | `"create_vehicle"` |
| `version` | ✓ | Template version | `"1.2"` |
| `category` | ✓ | Template category | `"vehicle_operations"` |
| `description` | ✓ | What the template does | `"Creates a new vehicle record"` |
| `required_entities` | ✓ | Must-have entities | `["vehicle_id", "user"]` |
| `optional_entities` | - | Optional entities | `["location", "notes"]` |
| `api_endpoint` | ✓ | API endpoint path | `"/api/v1/vehicles"` |
| `http_method` | - | HTTP method (default: POST) | `"PUT"` |
| `tags` | - | Searchable tags | `["fleet", "create"]` |
| `dependencies` | - | Template dependencies | `["auth_token"]` |

## Updating Templates with API Documentation

### Step 1: Gather API Documentation

Before updating templates, collect the following information:

1. **Endpoint Details**
   - Full API endpoint URL
   - HTTP method (GET, POST, PUT, DELETE, PATCH)
   - Authentication requirements
   - Rate limiting information

2. **Request Schema**
   - Required fields
   - Optional fields
   - Data types for each field
   - Field constraints (min/max length, patterns, allowed values)
   - Nested object structures

3. **Response Schema**
   - Success response format
   - Error response format
   - Status codes

4. **Business Rules**
   - Field dependencies
   - Validation logic
   - Workflow constraints

### Step 2: Update Template Metadata

Update the metadata section with current API information:

```json
{
  "template_metadata": {
    "name": "create_vehicle",
    "version": "2.1",  // Increment version
    "category": "vehicle_operations",
    "description": "Creates a new vehicle record in the fleet management system",
    "required_entities": ["vehicle_id", "make", "model", "year"],
    "optional_entities": ["vin", "license_plate", "assigned_driver", "location"],
    "api_endpoint": "/api/v2/fleet/vehicles",  // Updated endpoint
    "http_method": "POST",
    "tags": ["vehicle", "fleet", "create", "management"],
    "dependencies": ["user_authentication"],
    "api_version": "2.1",  // New field
    "last_updated": "2024-01-15T10:30:00Z"  // New field
  }
}
```

### Step 3: Update Template Structure

Map API fields to template variables using the `{variable_name|default_value}` syntax:

```json
{
  "template": {
    "vehicle_information": {
      "vehicle_id": "{vehicle_id}",
      "make": "{make}",
      "model": "{model}",
      "year": "{year|2024}",
      "vin": "{vin|null}",
      "license_plate": "{license_plate|null}"
    },
    "assignment": {
      "assigned_driver": "{assigned_driver|null}",
      "department": "{department|general}",
      "location": "{location|headquarters}"
    },
    "metadata": {
      "created_at": "{current_timestamp}",
      "created_by": "{user|system}",
      "status": "active"
    }
  }
}
```

### Step 4: Update Validation Rules

Define validation rules based on API documentation:

```json
{
  "validation_rules": {
    "vehicle_id": {
      "required": true,
      "type": "string",
      "pattern": "^[A-Z0-9]{6,12}$",
      "description": "Unique vehicle identifier"
    },
    "make": {
      "required": true,
      "type": "string",
      "min_length": 2,
      "max_length": 50,
      "allowed_values": ["Toyota", "Ford", "Honda", "Chevrolet"]
    },
    "year": {
      "required": true,
      "type": "integer",
      "min": 2000,
      "max": 2030
    },
    "vin": {
      "type": "string",
      "pattern": "^[A-HJ-NPR-Z0-9]{17}$",
      "format": "vin"
    },
    "license_plate": {
      "type": "string",
      "pattern": "^[A-Z0-9-]{2,10}$"
    }
  }
}
```

## Adding New Templates

### Step 1: Create Template File

Create a new JSON file in the appropriate category directory:

```
knowledge/templates/
├── vehicle_operations/
│   └── new_template.json
├── maintenance/
├── reservations/
└── parking/
```

### Step 2: Follow Naming Convention

Use descriptive, consistent names:
- File name: `action_object.json` (e.g., `update_vehicle.json`)
- Template name: Match file name without extension
- Version: Start with `"1.0"`

### Step 3: Complete Template Structure

```json
{
  "template_metadata": {
    "name": "update_vehicle",
    "version": "1.0",
    "category": "vehicle_operations",
    "description": "Updates existing vehicle information",
    "required_entities": ["vehicle_id"],
    "optional_entities": ["make", "model", "year", "location"],
    "api_endpoint": "/api/v1/vehicles/{vehicle_id}",
    "http_method": "PUT",
    "tags": ["vehicle", "update", "modify"]
  },
  "template": {
    "vehicle_id": "{vehicle_id}",
    "updates": {
      "make": "{make|null}",
      "model": "{model|null}",
      "year": "{year|null}",
      "location": "{location|null}",
      "last_modified": "{current_timestamp}",
      "modified_by": "{user|system}"
    }
  },
  "validation_rules": {
    "vehicle_id": {
      "required": true,
      "type": "string",
      "pattern": "^[A-Z0-9]{6,12}$"
    }
  }
}
```

## API Documentation Integration

### OpenAPI/Swagger Integration

If you have OpenAPI/Swagger documentation, you can extract template information:

```python
# Example script to extract template info from OpenAPI spec
import json
import yaml

def extract_template_from_openapi(openapi_file, endpoint_path, method):
    with open(openapi_file, 'r') as f:
        api_spec = yaml.safe_load(f)
    
    endpoint = api_spec['paths'][endpoint_path][method]
    request_body = endpoint.get('requestBody', {})
    schema = request_body.get('content', {}).get('application/json', {}).get('schema', {})
    
    # Extract required fields
    required_fields = schema.get('required', [])
    
    # Extract properties
    properties = schema.get('properties', {})
    
    # Generate template structure
    template = {}
    validation_rules = {}
    
    for field_name, field_schema in properties.items():
        template[field_name] = f"{{{field_name}}}"
        validation_rules[field_name] = {
            "type": field_schema.get('type', 'string'),
            "required": field_name in required_fields
        }
        
        # Add constraints
        if 'minLength' in field_schema:
            validation_rules[field_name]['min_length'] = field_schema['minLength']
        if 'maxLength' in field_schema:
            validation_rules[field_name]['max_length'] = field_schema['maxLength']
        if 'pattern' in field_schema:
            validation_rules[field_name]['pattern'] = field_schema['pattern']
    
    return {
        "template": template,
        "validation_rules": validation_rules,
        "required_entities": required_fields
    }
```

### Postman Collection Integration

Extract template information from Postman collections:

```python
def extract_from_postman_collection(collection_file, request_name):
    with open(collection_file, 'r') as f:
        collection = json.load(f)
    
    # Find the specific request
    for item in collection.get('item', []):
        if item['name'] == request_name:
            request = item['request']
            
            # Extract endpoint and method
            url = request['url']['raw']
            method = request['method']
            
            # Extract request body
            body = request.get('body', {})
            if body.get('mode') == 'raw':
                try:
                    body_json = json.loads(body['raw'])
                    return extract_template_from_json(body_json, url, method)
                except json.JSONDecodeError:
                    pass
    
    return None
```

## Testing Templates

### Step 1: Validate Template Structure

Use the built-in validation system:

```python
from combadge.fleet.templates import TemplateManager, TemplateValidator

# Initialize managers
template_manager = TemplateManager()
validator = TemplateValidator(template_manager)

# Load and validate template
template_id = "vehicle_operations.create_vehicle.2.1"
validation_result = template_manager.validate_template_structure(template_id)

if not validation_result['valid']:
    print("Template validation errors:")
    for error in validation_result['errors']:
        print(f"  - {error}")
```

### Step 2: Test with Sample Data

Create test cases for your templates:

```python
from combadge.intelligence import IntentClassifier, EntityExtractor
from combadge.fleet.templates import TemplateSelector, JSONGenerator

# Create test input
test_input = "Create a new vehicle with ID VEH001, make Toyota, model Camry, year 2023"

# Process through NLP pipeline
intent_classifier = IntentClassifier()
entity_extractor = EntityExtractor()

intent_result = intent_classifier.classify(test_input)
entity_result = entity_extractor.extract(test_input)

# Select and generate JSON
template_selector = TemplateSelector(template_manager)
json_generator = JSONGenerator(template_manager)

selection_result = template_selector.select_templates(intent_result, entity_result)
generation_results = json_generator.generate_json(
    selection_result, intent_result, entity_result
)

# Validate generated JSON
for result in generation_results:
    validation = validator.validate_generation_result(result)
    if not validation.is_valid:
        print(f"Generated JSON validation failed for {result.template_id}")
        for issue in validation.issues:
            print(f"  - {issue.message}")
```

### Step 3: Integration Testing

Test with actual API endpoints:

```python
import requests

def test_template_with_api(generation_result, base_url, headers=None):
    """Test generated JSON with actual API endpoint."""
    template_metadata = template_manager.get_template_metadata(
        generation_result.template_id
    )
    
    if not template_metadata:
        return False, "Template metadata not found"
    
    # Construct full URL
    full_url = f"{base_url}{template_metadata.api_endpoint}"
    
    # Make API request
    try:
        response = requests.request(
            method=template_metadata.http_method,
            url=full_url,
            json=generation_result.generated_json,
            headers=headers or {}
        )
        
        return response.status_code < 400, response.text
    except Exception as e:
        return False, str(e)

# Test with API
success, message = test_template_with_api(
    generation_results[0],
    "https://api.example.com",
    {"Authorization": "Bearer token"}
)

if success:
    print("API integration test passed")
else:
    print(f"API integration test failed: {message}")
```

## Best Practices

### 1. Version Management

- Increment version numbers when making changes:
  - Major version (1.0 → 2.0): Breaking changes to template structure
  - Minor version (1.0 → 1.1): New optional fields or enhanced validation
  - Patch version (1.0.0 → 1.0.1): Bug fixes or documentation updates

- Keep old versions for backward compatibility:
```
knowledge/templates/vehicle_operations/
├── create_vehicle_v1.0.json
├── create_vehicle_v1.1.json
└── create_vehicle_v2.0.json  # Latest
```

### 2. Documentation

Document changes in template comments:

```json
{
  "template_metadata": {
    "name": "create_vehicle",
    "version": "2.0",
    "changelog": [
      "v2.0: Added VIN validation, updated API endpoint to v2",
      "v1.1: Added optional location field",
      "v1.0: Initial version"
    ]
  }
}
```

### 3. Entity Mapping

Use consistent entity names across templates:

```json
{
  "entity_mapping": {
    "vehicle_id": ["vehicle_id", "vehicleId", "unit_id", "asset_id"],
    "user": ["user", "user_id", "assigned_to", "driver"],
    "location": ["location", "site", "address", "building"]
  }
}
```

### 4. Error Handling

Include error handling in templates:

```json
{
  "template": {
    "request": {
      // Main request data
    },
    "error_handling": {
      "retry_count": 3,
      "timeout": 30,
      "fallback_template": "create_vehicle_v1.0"
    }
  }
}
```

### 5. Validation Rules

Use comprehensive validation rules:

```json
{
  "validation_rules": {
    "field_name": {
      "required": true,
      "type": "string",
      "min_length": 1,
      "max_length": 50,
      "pattern": "^[A-Z0-9-]+$",
      "allowed_values": ["value1", "value2"],
      "format": "email|phone|date|datetime|url|uuid",
      "description": "Human-readable description",
      "example": "Example value"
    }
  }
}
```

## Automation Tools

### Template Generator Script

Create a script to generate templates from API documentation:

```python
#!/usr/bin/env python3
"""
Template Generator Tool

Usage: python generate_template.py --api-spec openapi.yaml --endpoint /api/v1/vehicles --method POST
"""

import argparse
import json
import yaml
from pathlib import Path

def generate_template(api_spec_file, endpoint_path, method, output_dir):
    # Load API specification
    with open(api_spec_file, 'r') as f:
        if api_spec_file.endswith('.yaml') or api_spec_file.endswith('.yml'):
            api_spec = yaml.safe_load(f)
        else:
            api_spec = json.load(f)
    
    # Extract endpoint information
    endpoint = api_spec['paths'][endpoint_path][method.lower()]
    
    # Generate template structure
    template = {
        "template_metadata": {
            "name": f"{method.lower()}_{endpoint_path.split('/')[-1]}",
            "version": "1.0",
            "category": "generated",
            "description": endpoint.get('summary', 'Generated template'),
            "api_endpoint": endpoint_path,
            "http_method": method.upper(),
            "generated_from": api_spec_file,
            "generated_at": datetime.now().isoformat()
        }
    }
    
    # Extract request body schema
    request_body = endpoint.get('requestBody', {})
    if request_body:
        schema = request_body.get('content', {}).get('application/json', {}).get('schema', {})
        template_content, validation_rules, required_entities = process_schema(schema)
        
        template["template"] = template_content
        template["validation_rules"] = validation_rules
        template["template_metadata"]["required_entities"] = required_entities
    
    # Write template file
    output_path = Path(output_dir) / f"{template['template_metadata']['name']}.json"
    with open(output_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"Generated template: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate template from API specification")
    parser.add_argument("--api-spec", required=True, help="API specification file (OpenAPI/Swagger)")
    parser.add_argument("--endpoint", required=True, help="API endpoint path")
    parser.add_argument("--method", required=True, help="HTTP method")
    parser.add_argument("--output-dir", default="knowledge/templates/generated", help="Output directory")
    
    args = parser.parse_args()
    generate_template(args.api_spec, args.endpoint, args.method, args.output_dir)
```

### Template Validator Script

Create a validation script:

```bash
#!/bin/bash
# validate_templates.sh

echo "Validating ComBadge templates..."

python3 -c "
from combadge.fleet.templates import TemplateManager
import sys

template_manager = TemplateManager()
success = template_manager.load_templates()

if not success:
    print('Template loading failed')
    sys.exit(1)

registry_summary = template_manager.get_registry_summary()
print(f'Loaded {registry_summary[\"total_templates\"]} templates')
print(f'Categories: {registry_summary[\"categories\"]}')

# Validate each template
errors = 0
for template_id in template_manager.registry.templates.keys():
    validation = template_manager.validate_template_structure(template_id)
    if not validation['valid']:
        print(f'INVALID: {template_id}')
        for error in validation['errors']:
            print(f'  ERROR: {error}')
        errors += 1
    else:
        print(f'VALID: {template_id}')

if errors > 0:
    print(f'{errors} templates have validation errors')
    sys.exit(1)
else:
    print('All templates are valid')
"
```

## Troubleshooting

### Common Issues

1. **Template Not Loading**
   - Check file path and naming convention
   - Verify JSON syntax with `json.lint` or similar tool
   - Ensure all required metadata fields are present

2. **Validation Errors**
   - Check required_entities match template variables
   - Verify validation rule syntax
   - Test with sample data

3. **Entity Mapping Issues**
   - Review entity extractor output
   - Update entity mappings in json_generator.py
   - Test with different input variations

4. **API Integration Failures**
   - Verify API endpoint and method
   - Check authentication requirements
   - Test with API documentation examples

### Debug Commands

```python
# Debug template loading
template_manager = TemplateManager()
template_manager.logger.setLevel('DEBUG')
template_manager.load_templates(force_reload=True)

# Debug template selection
from combadge.fleet.templates import TemplateSelector
selector = TemplateSelector(template_manager)
selector.logger.setLevel('DEBUG')

# Debug JSON generation
from combadge.fleet.templates import JSONGenerator
generator = JSONGenerator(template_manager)
generator.logger.setLevel('DEBUG')
```

## Conclusion

This guide provides a comprehensive approach to updating and maintaining ComBadge templates. Regular updates ensure the system stays synchronized with API changes and continues to provide accurate natural language to API request conversion.

Remember to:
- Test templates thoroughly before deployment
- Maintain backward compatibility when possible
- Document all changes
- Use version control for template files
- Automate validation where possible

For additional support or questions about template management, refer to the ComBadge documentation or contact the development team.