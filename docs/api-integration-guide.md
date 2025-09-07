# API Integration Guide for ComBadge

This guide explains how to update ComBadge when you receive actual API documentation from a fleet management system. The system is designed to be easily customizable with real API specifications.

## Overview

ComBadge currently contains template/example API configurations. When you get real API documentation, you'll need to update several components to match the actual system's endpoints, schemas, and authentication methods.

## What to Update

### 1. API Documentation and Knowledge Base

**Location**: `/knowledge/api_documentation/`

#### Update Endpoint Documentation
- **Files**: `endpoints/*.yaml` (vehicles.yaml, maintenance.yaml, reservations.yaml, parking.yaml)
- **What to change**: 
  - Replace example URLs with actual API endpoints
  - Update HTTP methods (GET, POST, PUT, DELETE)
  - Modify parameter names and data types
  - Update response formats and field names
  - Replace example business rules with actual policies

```yaml
# BEFORE (example)
vehicles:
  create_vehicle:
    endpoint: "/api/vehicles"
    method: "POST"
    
# AFTER (with real API docs)
vehicles:
  create_vehicle:
    endpoint: "/fleet-management/v2/assets"
    method: "POST"
```

#### Update API Schemas
- **Files**: `schemas/*.json` (request_schemas.json, response_schemas.json, error_schemas.json)
- **What to change**:
  - Field names and data types
  - Required vs optional fields
  - Validation patterns (regex, enums)
  - Error code mappings
  - Response structure formats

```json
// BEFORE (example)
{
  "vehicle_id": {"type": "string", "pattern": "^[A-Z]{3}[0-9]{3,4}$"}
}

// AFTER (with real API)
{
  "asset_number": {"type": "string", "pattern": "^AST[0-9]{6}$"}
}
```

### 2. Authentication Configuration

**Location**: `/src/combadge/api/authentication.py`

#### Update Authentication Methods
Based on the real API documentation, you may need to:

```python
# If the API uses different authentication
def configure_real_auth(self):
    # Example: API uses OAuth 2.0 with client credentials
    config = {
        'type': 'jwt',
        'token_url': 'https://api.fleetmanager.com/oauth/token',
        'client_id': 'your_client_id',
        'client_secret': 'your_client_secret',
        'scope': 'fleet.read fleet.write'
    }
    
    # Or if it uses API keys
    config = {
        'type': 'api_key',
        'api_key': 'your_api_key',
        'header_name': 'X-Fleet-API-Key'
    }
```

### 3. HTTP Client Configuration

**Location**: `/src/combadge/api/client.py`

#### Update Base URLs and Headers
```python
# Update in your client initialization
client = HTTPClient(
    base_url="https://api.fleetmanager.com",  # Real API base URL
    user_agent="ComBadge-Integration/1.0.0"   # Update user agent
)

# Add any required headers
client.session.headers.update({
    'X-API-Version': '2.1',  # If API requires version header
    'Accept': 'application/vnd.fleet.v2+json'  # If API uses custom content types
})
```

### 4. API Endpoints

**Location**: `/src/combadge/api/endpoints/`

#### Update Endpoint Classes
For each endpoint file, update:

```python
class VehicleEndpoints(BaseEndpoint):
    def _get_base_path(self) -> str:
        # BEFORE
        return '/api/vehicles'
        
        # AFTER (with real API)
        return '/fleet-management/v2/assets'
    
    def create_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        # Update required fields based on real API
        required_fields = ['asset_name', 'asset_type', 'serial_number']  # Real API fields
        
        # Update field mappings
        mapped_data = {
            'asset_name': vehicle_data.get('make') + ' ' + vehicle_data.get('model'),
            'asset_type': 'vehicle',
            'serial_number': vehicle_data.get('vin')
        }
```

### 5. Request Templates

**Location**: `/src/combadge/api/request_builder.py`

#### Update Template Definitions
```python
def create_fleet_templates(self):
    # Update templates with real API structure
    self.register_template(RequestTemplate(
        template_id='create_vehicle',
        method='POST',
        endpoint='/fleet-management/v2/assets',  # Real endpoint
        required_fields=['asset_name', 'asset_type', 'serial_number'],  # Real fields
        optional_fields=['location', 'department', 'purchase_date'],
        field_validators={
            'serial_number': lambda x: len(x) == 17,  # Real validation
            'asset_type': lambda x: x in ['vehicle', 'equipment', 'trailer']
        }
    ))
```

### 6. Response Handling

**Location**: `/src/combadge/api/response_handler.py`

#### Update Response Parsers
```python
def _register_default_processors(self):
    # Update for real API response format
    def validate_vehicle_response(data: Any) -> List[str]:
        errors = []
        if isinstance(data, dict):
            # Update required fields based on real API response
            required_fields = ['asset_id', 'asset_name', 'status']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        return errors
```

### 7. Business Rules and Policies

**Location**: `/knowledge/business_rules/`

#### Update Policy Files
Replace example policies with actual organizational rules:

```yaml
# fleet_policies.yaml - Update with real company policies
vehicle_usage:
  business_use:
    rules:
      - policy_id: "VU001"
        rule: "Company vehicles for business use only"  # Your actual policy
        enforcement: "automatic"
        
# operational_constraints.yaml - Update with real system limits
system_constraints:
  database_limits:
    max_vehicles: 5000  # Your actual fleet size
    max_users: 500     # Your actual user count
```

### 8. Natural Language Processing

**Location**: `/knowledge/prompts/`

#### Update Intent Classification
```text
# intent_classification/base_prompt.txt
# Update with your specific vehicle terminology
Classify fleet requests into these categories:
1. vehicle_operations - requests about company assets, fleet vehicles, or mobile equipment
2. maintenance_scheduling - requests about service appointments, repairs, or inspections
```

#### Update Entity Extraction
```text
# entity_extraction/vehicle_extraction.txt
# Update patterns for your ID formats
Vehicle ID Patterns:
- Asset numbers: AST followed by 6 digits (AST123456)
- Fleet codes: FL- followed by 4 digits (FL-0001)
- License plates: Your regional format
```

## Step-by-Step Integration Process

### Phase 1: Documentation Analysis
1. **Review API Documentation**
   - Collect all endpoint URLs, methods, and parameters
   - Document authentication requirements
   - Map response formats and error codes
   - Identify rate limits and constraints

2. **Create Field Mapping**
   - Map ComBadge fields to API fields
   - Document data type conversions needed
   - Identify missing or extra fields

### Phase 2: Configuration Updates
1. **Update Authentication**
   ```bash
   # Test authentication with real credentials
   python -c "
   from combadge.api import HTTPClient
   client = HTTPClient('https://api.fleetmanager.com')
   client.set_authentication({'type': 'jwt', 'token_url': '...'})
   print(client.health_check())
   "
   ```

2. **Update Base Configuration**
   - Modify `client.py` with real base URL
   - Update headers and timeouts
   - Configure proxy settings if needed

3. **Update Endpoints**
   - Modify each endpoint class
   - Update method signatures
   - Test basic CRUD operations

### Phase 3: Schema Updates
1. **Request Schemas**
   - Update `request_schemas.json`
   - Add validation rules
   - Test with real data

2. **Response Schemas**
   - Update `response_schemas.json`
   - Update error mappings
   - Test response parsing

### Phase 4: Business Logic Integration
1. **Update Business Rules**
   - Replace example policies
   - Configure approval workflows
   - Set up notification preferences

2. **Update Validation Rules**
   - Implement real field validators
   - Add business logic constraints
   - Configure error messages

### Phase 5: Testing and Validation
1. **Unit Testing**
   ```bash
   # Test individual components
   python -m pytest tests/api/test_authentication.py
   python -m pytest tests/api/test_endpoints.py
   ```

2. **Integration Testing**
   ```bash
   # Test end-to-end workflows
   python -m pytest tests/integration/test_vehicle_operations.py
   ```

3. **User Acceptance Testing**
   - Test natural language processing
   - Validate approval workflows
   - Test error handling

## Configuration File Templates

### Environment Configuration
Create `.env` file:
```bash
# Real API Configuration
FLEET_API_BASE_URL=https://api.fleetmanager.com
FLEET_API_VERSION=v2
FLEET_API_KEY=your_api_key_here
FLEET_CLIENT_ID=your_client_id
FLEET_CLIENT_SECRET=your_client_secret

# Optional: Proxy settings
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=https://proxy.company.com:8080
```

### API Configuration
Create `config/api_config.json`:
```json
{
  "base_url": "https://api.fleetmanager.com",
  "version": "v2",
  "authentication": {
    "type": "jwt",
    "token_url": "/oauth/token",
    "expires_in": 3600
  },
  "endpoints": {
    "vehicles": "/fleet-management/v2/assets",
    "maintenance": "/fleet-management/v2/work-orders", 
    "reservations": "/fleet-management/v2/bookings"
  },
  "rate_limits": {
    "requests_per_minute": 100,
    "requests_per_hour": 1000
  }
}
```

## Common Integration Challenges

### 1. Field Name Mismatches
**Problem**: API uses different field names than expected
**Solution**: Create field mapping dictionaries

```python
FIELD_MAPPINGS = {
    'vehicle_id': 'asset_id',
    'license_plate': 'registration_number',
    'assigned_driver': 'primary_user'
}

def map_request_fields(data):
    return {FIELD_MAPPINGS.get(k, k): v for k, v in data.items()}
```

### 2. Date Format Differences
**Problem**: API expects different date formats
**Solution**: Add date transformation utilities

```python
def format_date_for_api(date_str: str) -> str:
    # Convert from ISO format to API format
    from datetime import datetime
    dt = datetime.fromisoformat(date_str)
    return dt.strftime('%Y/%m/%d')  # API expected format
```

### 3. Authentication Token Handling
**Problem**: Token expiration and refresh
**Solution**: Implement automatic token refresh

```python
class TokenManager:
    def refresh_token_if_needed(self):
        if self.token_expires_soon():
            self.refresh_token()
```

### 4. Error Code Mapping
**Problem**: API returns different error codes
**Solution**: Create error code translation

```python
ERROR_CODE_MAPPING = {
    'INVALID_ASSET': 'Invalid vehicle ID',
    'BOOKING_CONFLICT': 'Vehicle already reserved',
    'AUTH_EXPIRED': 'Authentication expired'
}
```

## Testing Your Integration

### 1. Authentication Test
```python
def test_authentication():
    client = HTTPClient(base_url=API_BASE_URL)
    client.set_authentication(auth_config)
    assert client.get('/health').get('status') == 'ok'
```

### 2. Basic CRUD Test
```python
def test_vehicle_crud():
    vehicles = VehicleEndpoints(client)
    
    # Test create
    vehicle = vehicles.create_vehicle(test_vehicle_data)
    assert 'vehicle_id' in vehicle
    
    # Test read
    retrieved = vehicles.get_vehicle(vehicle['vehicle_id'])
    assert retrieved['make'] == test_vehicle_data['make']
```

### 3. Natural Language Processing Test
```python
def test_nlp_integration():
    from combadge.nlp import FleetRequestProcessor
    
    processor = FleetRequestProcessor()
    request = "Schedule maintenance for vehicle F-123 tomorrow at 2 PM"
    
    result = processor.process_request(request)
    assert result['intent'] == 'maintenance_scheduling'
    assert result['entities']['vehicle_id'] == 'F-123'
```

## Maintenance and Updates

### Regular Updates Needed
1. **API Schema Changes**: Monitor API version updates
2. **Authentication Updates**: Rotate keys and credentials
3. **Business Rule Changes**: Update policies as company rules change
4. **Performance Tuning**: Adjust timeouts and retry logic

### Monitoring Integration Health
```python
def check_integration_health():
    health_checks = {
        'authentication': client.auth_manager.is_authenticated(),
        'api_connectivity': client.health_check()['status'] == 'healthy',
        'rate_limits': client.get_metrics()['success_rate'] > 0.95
    }
    return all(health_checks.values())
```

This guide ensures smooth integration when you receive actual API documentation. Each section provides specific examples and code snippets to help you update ComBadge for real fleet management systems.