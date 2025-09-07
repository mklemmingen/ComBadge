# Complete API Configuration Guide for ComBadge

This comprehensive guide explains how to configure ComBadge to control any external system through natural language when you have complete API documentation. This guide is for system administrators and developers who want to integrate ComBadge with their existing enterprise software.

## Overview

ComBadge is designed to be a universal natural language interface for any API-based system. With proper configuration, users can control complex enterprise software using simple natural language commands like:

- "Show me all vehicles scheduled for maintenance this week"
- "Create a new user account for John Smith in the Sales department"
- "Generate a report of all failed backup jobs from yesterday"
- "Schedule a meeting with the engineering team for next Tuesday"

This guide shows you how to configure ComBadge for **any** API-based system, not just fleet management.

## Prerequisites

Before starting, ensure you have:
- Complete API documentation for your target system
- API credentials and access permissions
- Basic understanding of REST APIs and JSON
- Access to ComBadge configuration files

## Step 1: Analyze Your Target System

### 1.1 Inventory Your API Endpoints

Create a comprehensive list of all API endpoints you want to control:

```yaml
# Example endpoint inventory for a CRM system
endpoints:
  users:
    - GET /api/users - List users
    - POST /api/users - Create user
    - PUT /api/users/{id} - Update user
    - DELETE /api/users/{id} - Delete user
  
  accounts:
    - GET /api/accounts - List accounts
    - POST /api/accounts - Create account
    - PUT /api/accounts/{id} - Update account
  
  reports:
    - GET /api/reports - List reports
    - POST /api/reports/generate - Generate report
```

### 1.2 Map Business Operations to API Calls

Identify the common business operations users will want to perform:

```yaml
business_operations:
  user_management:
    create_user: "POST /api/users"
    find_user: "GET /api/users?search={query}"
    update_user: "PUT /api/users/{id}"
    disable_user: "PUT /api/users/{id} (set active: false)"
  
  reporting:
    generate_sales_report: "POST /api/reports/generate"
    list_recent_reports: "GET /api/reports?created_after={date}"
```

### 1.3 Understand Authentication

Document your system's authentication method:

```yaml
authentication:
  method: oauth2  # or api_key, basic_auth, jwt, etc.
  endpoints:
    token: "https://api.yoursystem.com/oauth/token"
    refresh: "https://api.yoursystem.com/oauth/refresh"
  scopes:
    - "read:users"
    - "write:users" 
    - "read:reports"
```

## Step 2: Configure API Connection

### 2.1 Update Base Configuration

Edit `config/default_config.yaml` or create environment-specific files:

```yaml
# config/default_config.yaml or production.yaml
api:
  base_url: "https://api.yoursystem.com"
  timeout: 60
  retry_attempts: 5
  retry_delay: 2.0
  verify_ssl: true
  authentication:
    method: oauth2
    token_url: "https://api.yoursystem.com/oauth/token"
    client_id: "your_client_id"
    # client_secret stored securely (see Step 2.2)
```

### 2.2 Configure Secure Authentication

Use environment variables for sensitive data:

```bash
# .env file or environment variables
COMBADGE_API_AUTHENTICATION_CLIENT_SECRET=your_secret_here
COMBADGE_API_AUTHENTICATION_USERNAME=service_account_user
COMBADGE_API_AUTHENTICATION_PASSWORD=secure_password
```

For production, use your organization's secrets management:
- Azure Key Vault
- AWS Secrets Manager  
- HashiCorp Vault
- Kubernetes Secrets

## Step 3: Create Knowledge Base

### 3.1 API Endpoint Documentation

Create detailed endpoint documentation in `knowledge/api_documentation/endpoints/`:

```yaml
# knowledge/api_documentation/endpoints/users.yaml
users:
  list_users:
    endpoint: "/api/users"
    method: "GET"
    description: "Retrieve list of users with optional filtering"
    parameters:
      query:
        search: "Text search across user fields"
        department: "Filter by department"
        active: "Filter by active status (true/false)"
        limit: "Number of results (max 100)"
        offset: "Pagination offset"
    response_fields:
      id: "Unique user identifier"
      email: "User email address"
      first_name: "User's first name"
      last_name: "User's last name"
      department: "User's department"
      role: "User's role/permissions level"
      created_date: "Account creation date"
      last_login: "Last login timestamp"
    natural_language_patterns:
      - "show me all users"
      - "list users in {department}"
      - "find users named {name}"
      - "show inactive users"

  create_user:
    endpoint: "/api/users"
    method: "POST"
    description: "Create a new user account"
    required_fields:
      - email
      - first_name
      - last_name
      - department
    optional_fields:
      - role
      - phone
      - manager_id
    business_rules:
      - "Email must be unique"
      - "Department must exist"
      - "Role defaults to 'user' if not specified"
    natural_language_patterns:
      - "create user {name} in {department}"
      - "add new employee {name} with email {email}"
      - "set up account for {name}"
```

### 3.2 Entity Extraction Patterns

Update `knowledge/prompts/entity_extraction/` for your domain:

```text
# knowledge/prompts/entity_extraction/user_extraction.txt
User Entity Extraction Patterns:

User Names:
- Full names: "John Smith", "Mary Johnson"
- First name only: "John", "Mary" 
- Email addresses: "john.smith@company.com"
- Employee IDs: "EMP001", "E12345"

Department Names:
- Standard departments: "Sales", "Engineering", "Marketing", "HR"
- Variations: "IT Department", "Customer Service", "Accounting"

Roles and Permissions:
- Basic roles: "admin", "manager", "user", "guest"
- Department-specific: "sales manager", "senior developer"

Status Indicators:
- Active/Inactive: "active users", "disabled accounts"
- Employment status: "current employees", "former staff"

Examples:
- "Find John Smith in Sales" → user_name: "John Smith", department: "Sales"
- "Create account for mary.johnson@company.com in Marketing" 
  → email: "mary.johnson@company.com", department: "Marketing"
```

### 3.3 Intent Classification

Update `knowledge/prompts/intent_classification/base_prompt.txt`:

```text
Classify user requests into these business intents for [YOUR SYSTEM NAME]:

1. user_management - Creating, updating, finding, or managing user accounts
   Examples: "create user", "find John", "disable account", "reset password"

2. reporting - Generating, viewing, or managing reports and analytics  
   Examples: "generate sales report", "show last month's metrics"

3. data_query - Searching, filtering, or retrieving information
   Examples: "show all active projects", "find customers in California"

4. system_administration - System settings, configurations, maintenance
   Examples: "backup database", "update system settings"

5. workflow_management - Managing processes, approvals, tasks
   Examples: "approve request", "start workflow", "assign task"

6. integration_operations - Third-party integrations and data sync
   Examples: "sync with Salesforce", "import from Excel"

[Add more intents specific to your system]

Classification Guidelines:
- Focus on the primary action the user wants to perform
- Consider the data or entities involved
- Account for system-specific terminology
- Handle ambiguous requests by asking for clarification
```

## Step 4: Create Request Templates

### 4.1 JSON Templates

Create request templates in `knowledge/templates/`:

```json
// knowledge/templates/user_operations/create_user.json
{
  "template_id": "create_user",
  "intent": "user_management", 
  "action": "create",
  "description": "Create a new user account",
  
  "api_request": {
    "method": "POST",
    "endpoint": "/api/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "{{user_email}}",
      "first_name": "{{first_name}}",
      "last_name": "{{last_name}}",
      "department": "{{department}}",
      "role": "{{role|default:user}}",
      "phone": "{{phone|optional}}",
      "manager_id": "{{manager_id|optional}}"
    }
  },
  
  "field_mappings": {
    "user_email": {
      "type": "email",
      "required": true,
      "validation": "email_format",
      "extraction_patterns": ["email addresses", "@company.com domains"]
    },
    "first_name": {
      "type": "string", 
      "required": true,
      "extraction_patterns": ["person names", "first names"]
    },
    "last_name": {
      "type": "string",
      "required": true, 
      "extraction_patterns": ["person names", "surnames"]
    },
    "department": {
      "type": "string",
      "required": true,
      "validation": "department_exists",
      "extraction_patterns": ["department names", "organizational units"]
    }
  },
  
  "success_response": {
    "status_codes": [201],
    "success_message": "User {{first_name}} {{last_name}} created successfully with ID {{response.id}}"
  },
  
  "natural_language_examples": [
    "Create user John Smith in Engineering with email john.smith@company.com",
    "Add new employee Mary Johnson to the Sales department", 
    "Set up account for mike.davis@company.com in IT as an admin"
  ]
}
```

### 4.2 Business Rules and Validation

Create validation rules in `knowledge/business_rules/`:

```yaml
# knowledge/business_rules/user_policies.yaml
user_management_policies:
  creation_rules:
    - rule_id: "UM001"
      rule: "Email addresses must be unique across all users"
      validation_endpoint: "GET /api/users?email={{email}}"
      error_message: "User with email {{email}} already exists"
      
    - rule_id: "UM002" 
      rule: "Department must exist in the system"
      validation_endpoint: "GET /api/departments?name={{department}}"
      error_message: "Department '{{department}}' not found"
      
    - rule_id: "UM003"
      rule: "Manager ID must reference an existing user"
      validation_endpoint: "GET /api/users/{{manager_id}}"
      error_message: "Manager with ID {{manager_id}} not found"

  update_rules:
    - rule_id: "UM101"
      rule: "Cannot change email of active users with pending transactions"
      validation_logic: "complex"
      
  deletion_rules:
    - rule_id: "UM201" 
      rule: "Cannot delete users who are managers of other users"
      validation_endpoint: "GET /api/users?manager_id={{user_id}}"
      error_message: "Cannot delete user who manages other employees"
```

## Step 5: Configure Domain-Specific Processing

### 5.1 Custom Entity Extractors

Create entity extractors for your domain:

```python
# src/combadge/fleet/processors/custom_entity_extractor.py
class CustomEntityExtractor:
    """Extract entities specific to your business domain"""
    
    def __init__(self):
        self.department_names = ["Sales", "Engineering", "Marketing", "HR", "IT"]
        self.role_names = ["admin", "manager", "user", "guest"]
    
    def extract_user_info(self, text: str) -> Dict[str, Any]:
        """Extract user-related entities"""
        entities = {}
        
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            entities['email'] = emails[0]
        
        # Department extraction
        for dept in self.department_names:
            if dept.lower() in text.lower():
                entities['department'] = dept
                break
        
        # Role extraction  
        for role in self.role_names:
            if role.lower() in text.lower():
                entities['role'] = role
                break
        
        return entities
```

### 5.2 Custom Validators

Create validators for your business rules:

```python
# src/combadge/fleet/templates/custom_validators.py
class CustomBusinessRuleValidator:
    """Validate business rules specific to your system"""
    
    def __init__(self, api_client):
        self.api_client = api_client
    
    async def validate_user_creation(self, user_data: Dict[str, Any]) -> List[str]:
        """Validate user creation request"""
        errors = []
        
        # Check email uniqueness
        if 'email' in user_data:
            existing_user = await self.api_client.get(
                f"/api/users?email={user_data['email']}"
            )
            if existing_user.get('total', 0) > 0:
                errors.append(f"User with email {user_data['email']} already exists")
        
        # Validate department exists
        if 'department' in user_data:
            dept_response = await self.api_client.get(
                f"/api/departments?name={user_data['department']}"  
            )
            if dept_response.get('total', 0) == 0:
                errors.append(f"Department '{user_data['department']}' not found")
        
        return errors
```

## Step 6: Test and Validate Configuration

### 6.1 Configuration Testing

Test your configuration systematically:

```python
# test_config.py
import asyncio
from combadge.core.config_manager import ConfigManager
from combadge.api.client import HTTPClient

async def test_api_connection():
    """Test API connectivity and authentication"""
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    client = HTTPClient(
        base_url=config.api.base_url,
        timeout=config.api.timeout
    )
    
    # Test authentication
    client.set_authentication({
        'type': config.api.authentication.method,
        'client_id': config.api.authentication.client_id,
        # Add other auth parameters
    })
    
    # Test basic endpoint
    try:
        response = await client.get('/api/health')
        print(f"API Health Check: {response}")
        return True
    except Exception as e:
        print(f"API connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_api_connection())
```

### 6.2 Template Validation

Validate your request templates:

```python
# validate_templates.py
import json
from pathlib import Path
from combadge.fleet.templates.validators import TemplateValidator

def validate_all_templates():
    """Validate all request templates"""
    template_dir = Path("knowledge/templates")
    validator = TemplateValidator()
    
    errors = []
    for template_file in template_dir.rglob("*.json"):
        try:
            with open(template_file) as f:
                template = json.load(f)
            
            template_errors = validator.validate_template(template)
            if template_errors:
                errors.extend([
                    f"{template_file}: {error}" for error in template_errors
                ])
                
        except Exception as e:
            errors.append(f"{template_file}: Failed to load - {e}")
    
    if errors:
        print("Template validation errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("All templates validated successfully")
        return True

if __name__ == "__main__":
    validate_all_templates()
```

## Step 7: Advanced Configuration

### 7.1 Custom Chain of Thought

Customize reasoning for your domain:

```text
# knowledge/prompts/chain_of_thought/domain_reasoning.txt
Reasoning Framework for [YOUR SYSTEM] Operations:

Phase 1: Intent Understanding
- What is the user trying to accomplish?
- What business process does this relate to?
- Are there any compliance or security considerations?

Phase 2: Entity Analysis  
- What specific entities are mentioned (users, accounts, etc.)?
- Are all required parameters provided?
- What additional information might be needed?

Phase 3: Business Rule Validation
- Does this operation comply with business policies?
- Are there any approval requirements?
- What are the potential impacts or side effects?

Phase 4: API Mapping
- Which API endpoint(s) should be called?
- How should the data be formatted?
- What authentication/authorization is required?

Phase 5: Risk Assessment
- Is this a safe operation to perform?
- Should this require manual approval?
- What is the confidence level of the interpretation?

Domain-Specific Considerations:
[Add reasoning specific to your business domain]
```

### 7.2 Multi-System Integration

Configure multiple API integrations:

```yaml
# config/multi_system.yaml
systems:
  primary_crm:
    api:
      base_url: "https://crm.company.com/api"
      authentication:
        method: oauth2
        token_url: "https://crm.company.com/oauth/token"
    priority: 1
    
  backup_system:
    api: 
      base_url: "https://backup.crm.company.com/api"
      authentication:
        method: api_key
    priority: 2
    
  analytics_platform:
    api:
      base_url: "https://analytics.company.com/api"
      authentication:
        method: jwt
    priority: 3

routing_rules:
  - pattern: "user management"
    systems: ["primary_crm", "backup_system"]
  - pattern: "reporting"  
    systems: ["analytics_platform", "primary_crm"]
```

## Step 8: Deployment and Monitoring

### 8.1 Production Deployment

Configure for production deployment:

```yaml
# config/production.yaml
environment: production
debug_mode: false

# Production-specific settings
api:
  timeout: 30
  retry_attempts: 5
  verify_ssl: true
  
processing:
  confidence_threshold: 0.9  # Higher threshold for production
  enable_caching: true
  cache_ttl: 7200
  
logging:
  level: INFO
  audit_enabled: true
  file_path: "/var/log/combadge/app.log"
  
ui:
  auto_approve_high_confidence: true  # Enable for efficiency
  confidence_threshold: 0.95
```

### 8.2 Monitoring Configuration

Set up monitoring and alerting:

```yaml
# monitoring/alerts.yaml
monitoring:
  api_health_checks:
    - endpoint: "/api/health"
      interval: 60
      timeout: 10
      alert_on_failure: true
      
  performance_metrics:
    - metric: "response_time"
      threshold: 5000  # 5 seconds
      alert_on_breach: true
      
    - metric: "error_rate" 
      threshold: 0.05  # 5%
      alert_on_breach: true
      
  business_metrics:
    - metric: "approval_rate"
      threshold: 0.8
      alert_on_low: true
      
  security_monitoring:
    - event: "authentication_failure"
      threshold: 5
      time_window: 300  # 5 minutes
      alert_on_breach: true
```

## Step 9: User Training and Documentation

### 9.1 Create User Guides

Document natural language patterns for users:

```markdown
# User Guide: Natural Language Commands

## User Management Commands

### Creating Users
- "Create user John Smith in Sales with email john.smith@company.com"
- "Add new employee Mary Johnson to Engineering department"
- "Set up admin account for mike.davis@company.com"

### Finding Users  
- "Find all users in Marketing department"
- "Show me John Smith's user details"
- "List inactive users"

### Updating Users
- "Move John Smith to IT department" 
- "Make Mary Johnson a manager"
- "Update phone number for user@company.com"

## Reporting Commands

### Standard Reports
- "Generate monthly sales report"
- "Show user activity report for last week"
- "Create department utilization summary"

### Custom Queries
- "How many users joined this month?"
- "Show me all users who haven't logged in for 30 days"
- "List managers in each department"
```

### 9.2 Training Materials

Create training materials for administrators:

```markdown
# Administrator Training Guide

## Configuration Management
- How to update API endpoints
- Managing authentication credentials
- Customizing business rules
- Adding new templates

## Monitoring and Maintenance
- Checking system health
- Reviewing approval logs
- Performance optimization
- Troubleshooting common issues

## Security Best Practices  
- Credential rotation
- Access control management
- Audit log analysis
- Incident response procedures
```

## Best Practices and Tips

### Security Best Practices
1. **Never store credentials in configuration files**
   - Use environment variables or secure vaults
   - Rotate credentials regularly
   - Monitor for credential exposure

2. **Implement proper access controls**
   - Use least-privilege principles  
   - Regular access reviews
   - Multi-factor authentication

3. **Enable comprehensive auditing**
   - Log all configuration changes
   - Track all API calls
   - Monitor unusual patterns

### Performance Optimization
1. **Use caching strategically**
   - Cache frequently accessed data
   - Set appropriate TTL values
   - Monitor cache hit rates

2. **Optimize API calls**
   - Batch requests where possible
   - Use appropriate timeouts
   - Implement circuit breakers

3. **Monitor resource usage**
   - Track response times
   - Monitor memory usage
   - Alert on performance degradation

### Reliability Measures
1. **Implement graceful degradation**
   - Fallback to manual processes
   - Queue requests during outages
   - Provide clear error messages

2. **Test thoroughly**
   - Regular integration testing
   - Load testing for peak usage
   - Disaster recovery testing

3. **Monitor continuously**
   - Health checks for all dependencies
   - Alert on anomalies
   - Regular performance reviews

## Troubleshooting Common Issues

### Authentication Failures
```bash
# Check credentials
COMBADGE_DEBUG_MODE=true python -m combadge.api.test_auth

# Validate token expiration
curl -H "Authorization: Bearer $TOKEN" $API_URL/health

# Check OAuth flow
COMBADGE_LOGGING_LEVEL=DEBUG python -m combadge.api.oauth_test
```

### Template Processing Errors
```bash  
# Validate template syntax
python -m combadge.templates.validate knowledge/templates/

# Test entity extraction
python -m combadge.nlp.test_extraction "create user john@company.com"

# Debug request generation
COMBADGE_DEBUG_MODE=true python -m combadge.templates.debug
```

### API Connectivity Issues
```bash
# Test basic connectivity
curl -v $API_BASE_URL/health

# Check DNS resolution
nslookup api.company.com

# Test SSL/TLS
openssl s_client -connect api.company.com:443
```

## Summary

This guide provides a comprehensive framework for configuring ComBadge to work with any API-based system. The key steps are:

1. **Analyze** your target system's APIs and business processes
2. **Configure** authentication and connection settings
3. **Create** comprehensive knowledge base with endpoints and templates
4. **Customize** entity extraction and validation for your domain
5. **Test** thoroughly in development and staging environments
6. **Deploy** with appropriate monitoring and security measures
7. **Train** users and administrators on proper usage
8. **Monitor** and maintain the system continuously

With proper configuration, ComBadge can provide a natural language interface to virtually any enterprise system, making complex software accessible to all users regardless of technical expertise.