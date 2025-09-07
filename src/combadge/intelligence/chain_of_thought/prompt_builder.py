"""Prompt Builder for ComBadge NLP System

System prompts that guide the language model to identify intent, extract entities,
and provide step-by-step reasoning for natural language to API conversion.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

from ...core.logging_manager import LoggingManager


@dataclass
class IntentCategory:
    """Represents an intent category for NLP processing."""
    name: str
    description: str
    keywords: List[str]
    api_patterns: List[str]
    confidence_threshold: float = 0.7


class APIPromptBuilder:
    """Builds structured prompts for NLP to API conversion with Chain of Thought reasoning."""
    
    def __init__(self):
        """Initialize prompt builder with intent categories."""
        self.logger = LoggingManager.get_logger(__name__)
        self._setup_intent_categories()
        
    def _setup_intent_categories(self):
        """Setup predefined intent categories for API operations."""
        self.intent_categories = [
            IntentCategory(
                name="resource_reservation",
                description="Reserving or booking resources for specific times and purposes",
                keywords=["reserve", "book", "schedule", "assign", "allocate", "need"],
                api_patterns=["POST /reservations", "PUT /resources/{id}/reserve"],
                confidence_threshold=0.8
            ),
            IntentCategory(
                name="task_scheduling",
                description="Scheduling tasks, appointments, or service requests",
                keywords=["schedule", "appointment", "task", "service", "plan", "arrange"],
                api_patterns=["POST /tasks", "PUT /schedule/{id}"],
                confidence_threshold=0.8
            ),
            IntentCategory(
                name="status_query",
                description="Checking resource availability, location, or current status",
                keywords=["status", "available", "location", "where", "check", "find"],
                api_patterns=["GET /resources/{id}/status", "GET /resources/search"],
                confidence_threshold=0.7
            ),
            IntentCategory(
                name="inventory_management",
                description="Managing inventory, assignments, and availability",
                keywords=["inventory", "stock", "items", "manage", "track", "assign"],
                api_patterns=["POST /inventory/assignments", "GET /inventory/availability"],
                confidence_threshold=0.75
            ),
            IntentCategory(
                name="reporting_analytics",
                description="Generating reports, analytics, or data summaries",
                keywords=["report", "analytics", "summary", "data", "statistics", "usage"],
                api_patterns=["GET /reports/{type}", "POST /analytics/query"],
                confidence_threshold=0.7
            ),
            IntentCategory(
                name="user_management",
                description="Managing user permissions, access, and assignments",
                keywords=["user", "access", "permission", "assign", "authorize", "driver"],
                api_patterns=["POST /users", "PUT /users/{id}/permissions"],
                confidence_threshold=0.75
            )
        ]
        
    def build_system_prompt(self) -> str:
        """Build comprehensive system prompt for NLP to API conversion.
        
        Returns:
            System prompt string
        """
        return """You are ComBadge, an intelligent NLP to API conversion system for general purpose API operations. Your role is to analyze natural language input (emails, commands, requests) and convert them into structured API calls with clear Chain of Thought reasoning.

## Core Responsibilities:
1. **Intent Recognition**: Identify what the user wants to accomplish
2. **Entity Extraction**: Extract specific details like resource IDs, dates, times, locations
3. **API Mapping**: Convert intent and entities into appropriate API endpoint calls
4. **Chain of Thought**: Provide step-by-step reasoning for your decisions

## Available Intent Categories:
- **Resource Reservation**: Booking/reserving resources for specific times and purposes
- **Task Scheduling**: Scheduling tasks, appointments, or service requests
- **Status Query**: Checking availability, location, or current status
- **Inventory Management**: Managing inventory assignments and availability
- **Reporting & Analytics**: Generating reports and data summaries
- **User Management**: Managing permissions, access, and user assignments

## Response Format:
Always respond in JSON format with the following structure:
```json
{
  "chain_of_thought": [
    {
      "step": "Input Analysis",
      "reasoning": "Detailed analysis of the input text",
      "findings": ["specific observations"]
    },
    {
      "step": "Intent Recognition", 
      "reasoning": "How I identified the primary intent",
      "intent": "category_name",
      "confidence": 0.85
    },
    {
      "step": "Entity Extraction",
      "reasoning": "What entities I found and how",
      "entities": {
        "resource_ids": ["RES-1234"],
        "dates": ["2024-01-15"],
        "times": ["14:00-16:00"],
        "locations": ["Building A"],
        "users": ["john.doe@company.com"]
      }
    },
    {
      "step": "API Mapping",
      "reasoning": "How I mapped to API endpoints",
      "api_calls": [
        {
          "method": "POST",
          "endpoint": "/reservations",
          "body": {
            "resource_id": "RES-1234",
            "start_time": "2024-01-15T14:00:00Z",
            "end_time": "2024-01-15T16:00:00Z",
            "user": "john.doe@company.com"
          },
          "purpose": "Create resource reservation"
        }
      ]
    }
  ],
  "summary": {
    "intent": "resource_reservation",
    "confidence": 0.85,
    "api_calls_count": 1,
    "requires_approval": true,
    "risk_level": "low"
  }
}
```

## Processing Guidelines:
- Extract all resource IDs (patterns like: RES-1234, ITEM-001, etc.)
- Parse dates and times in ISO format when possible
- Identify email addresses and user references
- Calculate confidence scores based on keyword matches and context clarity
- Flag high-risk operations (deletions, bulk changes) for approval
- Provide clear reasoning for each step

## Error Handling:
- If input is unclear, ask for clarification
- If multiple intents detected, prioritize and explain
- If missing critical information, specify what's needed

Be thorough, accurate, and always explain your reasoning process."""

    def build_user_prompt(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build user prompt with input and context.
        
        Args:
            user_input: User's natural language input
            context: Additional context information
            
        Returns:
            Formatted user prompt
        """
        prompt_parts = []
        
        # Add timestamp
        timestamp = datetime.now().isoformat()
        prompt_parts.append(f"Timestamp: {timestamp}")
        
        # Add context if provided
        if context:
            prompt_parts.append("\n## Context Information:")
            for key, value in context.items():
                prompt_parts.append(f"- {key}: {value}")
        
        # Add user input
        prompt_parts.append(f"\n## User Input:\n{user_input}")
        
        # Add processing instruction
        prompt_parts.append("\n## Task:")
        prompt_parts.append("Analyze the above input and provide a complete Chain of Thought analysis with API mapping in the specified JSON format.")
        
        return "\n".join(prompt_parts)
        
    def build_clarification_prompt(self, original_input: str, 
                                  missing_entities: List[str]) -> str:
        """Build prompt for requesting clarification on missing information.
        
        Args:
            original_input: Original user input
            missing_entities: List of missing entity types
            
        Returns:
            Clarification prompt
        """
        clarification_parts = [
            "I need clarification to process your request accurately.",
            f"\nOriginal request: {original_input}",
            "\nMissing information:"
        ]
        
        for entity in missing_entities:
            if entity == "resource_id":
                clarification_parts.append("- Which specific resource? (e.g., RES-1234, ITEM-001)")
            elif entity == "date":
                clarification_parts.append("- What date? (e.g., today, tomorrow, 2024-01-15)")
            elif entity == "time":
                clarification_parts.append("- What time or time range? (e.g., 2-4pm, 14:00-16:00)")
            elif entity == "location":
                clarification_parts.append("- Which location or building?")
            elif entity == "user":
                clarification_parts.append("- For which user or driver?")
            else:
                clarification_parts.append(f"- {entity.replace('_', ' ').title()}")
                
        clarification_parts.append("\nPlease provide the missing details so I can create the appropriate API calls.")
        
        return "\n".join(clarification_parts)
        
    def build_confidence_analysis_prompt(self, parsed_result: Dict[str, Any]) -> str:
        """Build prompt for confidence analysis and validation.
        
        Args:
            parsed_result: Parsed result from initial processing
            
        Returns:
            Confidence analysis prompt
        """
        return f"""Analyze the confidence and accuracy of this parsed result:

{json.dumps(parsed_result, indent=2)}

Evaluate:
1. **Intent Confidence**: How certain are we about the identified intent?
2. **Entity Accuracy**: Are all extracted entities correct and complete?
3. **API Mapping**: Do the suggested API calls match the intent?
4. **Risk Assessment**: What's the risk level of these operations?

Provide a confidence score (0.0-1.0) and recommendations for improvement."""

    def get_intent_keywords(self, intent_name: str) -> List[str]:
        """Get keywords for a specific intent category.
        
        Args:
            intent_name: Name of intent category
            
        Returns:
            List of keywords for the intent
        """
        for category in self.intent_categories:
            if category.name == intent_name:
                return category.keywords
        return []
        
    def get_api_patterns(self, intent_name: str) -> List[str]:
        """Get API patterns for a specific intent category.
        
        Args:
            intent_name: Name of intent category
            
        Returns:
            List of API patterns for the intent
        """
        for category in self.intent_categories:
            if category.name == intent_name:
                return category.api_patterns
        return []
        
    def validate_entities(self, entities: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate extracted entities and return validation results.
        
        Args:
            entities: Dictionary of extracted entities
            
        Returns:
            Dictionary with validation results and errors
        """
        validation_results = {
            "valid": [],
            "errors": [],
            "warnings": []
        }
        
        # Validate resource IDs
        if "resource_ids" in entities:
            for resource_id in entities["resource_ids"]:
                if self._validate_resource_id(resource_id):
                    validation_results["valid"].append(f"Resource ID: {resource_id}")
                else:
                    validation_results["errors"].append(f"Invalid resource ID format: {resource_id}")
                    
        # Validate dates
        if "dates" in entities:
            for date in entities["dates"]:
                if self._validate_date(date):
                    validation_results["valid"].append(f"Date: {date}")
                else:
                    validation_results["errors"].append(f"Invalid date format: {date}")
                    
        # Validate times
        if "times" in entities:
            for time in entities["times"]:
                if self._validate_time(time):
                    validation_results["valid"].append(f"Time: {time}")
                else:
                    validation_results["warnings"].append(f"Time format may be ambiguous: {time}")
                    
        return validation_results
        
    def _validate_resource_id(self, resource_id: str) -> bool:
        """Validate resource ID format.
        
        Args:
            resource_id: Resource ID to validate
            
        Returns:
            True if valid format
        """
        import re
        # Common patterns: RES-1234, ITEM-001, PROD123, etc.
        patterns = [
            r'^[A-Z]{2,4}-\d{3,4}$',  # RES-1234, ITEM-001
            r'^[A-Z]{3,4}\d{3}$',     # PROD123, ITEM123
            r'^[A-Z]\d{3,4}$',        # R1234
            r'^\d{3,4}$'              # 1234
        ]
        
        return any(re.match(pattern, resource_id.upper()) for pattern in patterns)
        
    def _validate_date(self, date_str: str) -> bool:
        """Validate date string format.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            True if valid date format
        """
        from datetime import datetime
        
        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y", 
            "%d.%m.%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ"
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
                
        return False
        
    def _validate_time(self, time_str: str) -> bool:
        """Validate time string format.
        
        Args:
            time_str: Time string to validate
            
        Returns:
            True if valid time format
        """
        import re
        
        time_patterns = [
            r'^\d{1,2}:\d{2}$',           # 14:30
            r'^\d{1,2}:\d{2}:\d{2}$',     # 14:30:00
            r'^\d{1,2}(am|pm)$',          # 2pm
            r'^\d{1,2}:\d{2}(am|pm)$',    # 2:30pm
            r'^\d{1,2}-\d{1,2}(am|pm)$',  # 2-4pm
        ]
        
        return any(re.match(pattern, time_str.lower()) for pattern in time_patterns)