"""AI-Driven Template Selector

Intelligent template selection using LLM to analyze user input and choose
the most appropriate template based on examples and template metadata.
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

from ..core.logging_manager import LoggingManager
from ..intelligence.llm_manager import OllamaServerManager
from ..processors.templates.template_manager import TemplateManager, TemplateMetadata


class SelectionConfidence(Enum):
    """Template selection confidence levels."""
    VERY_HIGH = "very_high"  # > 0.9
    HIGH = "high"           # 0.8 - 0.9
    MEDIUM = "medium"       # 0.6 - 0.8
    LOW = "low"            # 0.4 - 0.6
    VERY_LOW = "very_low"   # < 0.4


@dataclass 
class TemplateChoice:
    """AI's template selection with reasoning."""
    template_name: str
    confidence: float
    reasoning: str
    confidence_level: SelectionConfidence
    alternative_templates: List[str] = field(default_factory=list)
    matched_examples: List[str] = field(default_factory=list)
    key_factors: List[str] = field(default_factory=list)


class AITemplateSelector:
    """AI-powered template selection using LLM analysis."""
    
    def __init__(self, template_manager: TemplateManager, ollama_manager: OllamaServerManager):
        """Initialize AI template selector.
        
        Args:
            template_manager: Template manager for accessing templates
            ollama_manager: Ollama manager for LLM communication
        """
        self.template_manager = template_manager
        self.ollama_manager = ollama_manager
        self.logger = LoggingManager.get_logger(__name__)
        
        # Load example data
        self.examples_data = self._load_example_data()
        
        # Selection history for learning
        self.selection_history: List[Dict[str, Any]] = []
        
    def _load_example_data(self) -> Dict[str, List[str]]:
        """Load example data for each template category.
        
        Returns:
            Dictionary mapping template categories to example commands
        """
        examples_file = Path(__file__).parent.parent.parent.parent / "knowledge" / "prompts" / "intent_classification" / "few_shot_examples.txt"
        
        if not examples_file.exists():
            self.logger.warning(f"Examples file not found: {examples_file}")
            return {}
        
        try:
            with open(examples_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse examples by category
            examples = {}
            current_category = None
            current_examples = []
            
            for line in content.split('\\n'):
                line = line.strip()
                
                # Category headers (e.g., "## RESERVATION_BOOKING Examples")
                if line.startswith('##') and 'Examples' in line:
                    if current_category and current_examples:
                        examples[current_category] = current_examples
                    current_category = line.replace('##', '').replace('Examples', '').strip().lower()
                    current_examples = []
                
                # Example inputs
                elif line.startswith('Input:'):
                    example = line.replace('Input:', '').strip().strip('"')
                    if example and current_category:
                        current_examples.append(example)
            
            # Add last category
            if current_category and current_examples:
                examples[current_category] = current_examples
            
            self.logger.info(f"Loaded examples for {len(examples)} categories")
            return examples
            
        except Exception as e:
            self.logger.error(f"Failed to load example data: {e}")
            return {}
    
    def select_template(self, user_input: str) -> TemplateChoice:
        """Select the best template for user input using AI analysis.
        
        Args:
            user_input: User's natural language input
            
        Returns:
            Template choice with reasoning
        """
        self.logger.info(f"AI selecting template for input: {user_input[:50]}...")
        
        # Get available templates
        templates_metadata = self.template_manager.get_all_templates_metadata()
        
        if not templates_metadata:
            return self._create_fallback_choice("No templates available")
        
        # Build AI prompt
        prompt = self._build_selection_prompt(user_input, templates_metadata)
        
        try:
            # Get AI response
            response = self._query_llm(prompt)
            
            # Parse AI response
            choice = self._parse_ai_response(response, templates_metadata)
            
            # Record selection for learning
            self._record_selection(user_input, choice, response)
            
            return choice
            
        except Exception as e:
            self.logger.error(f"AI template selection failed: {e}")
            return self._create_fallback_choice(f"AI selection error: {str(e)}")
    
    def _build_selection_prompt(self, user_input: str, templates: List[TemplateMetadata]) -> str:
        """Build the AI prompt for template selection.
        
        Args:
            user_input: User's input text
            templates: Available templates
            
        Returns:
            Complete AI prompt
        """
        # Build template descriptions
        template_descriptions = []
        for template in templates:
            # Get examples for this template's category
            category_examples = self.examples_data.get(template.category, [])
            examples_text = "\\n".join([f"  - {ex}" for ex in category_examples[:3]])  # Limit to 3 examples
            
            template_desc = f"""
Template: {template.name}
Category: {template.category}
Description: {template.description}
Required Entities: {', '.join(template.required_entities)}
Optional Entities: {', '.join(template.optional_entities)}
API Endpoint: {template.api_endpoint}
Usage Count: {template.usage_count}
Success Rate: {template.success_rate:.1%}
Example Commands:
{examples_text}
---"""
            template_descriptions.append(template_desc)
        
        prompt = f"""You are an AI template selector for an API request system. Your job is to analyze user input and select the most appropriate template.

USER INPUT: "{user_input}"

AVAILABLE TEMPLATES:
{''.join(template_descriptions)}

INSTRUCTIONS:
1. Analyze the user input to understand their intent
2. Match the intent to the most appropriate template based on:
   - Description similarity
   - Required entities availability in the input
   - Example command similarity
   - Usage success rates
3. Provide a confidence score (0.0 to 1.0)
4. Explain your reasoning clearly
5. Suggest up to 2 alternative templates if confidence < 0.8

RESPONSE FORMAT (JSON):
{{
  "selected_template": "template_name",
  "confidence": 0.85,
  "reasoning": "Detailed explanation of why this template was chosen",
  "key_factors": ["factor1", "factor2", "factor3"],
  "alternatives": ["alt_template1", "alt_template2"],
  "matched_examples": ["example1", "example2"]
}}

Respond with valid JSON only. No additional text."""
        
        return prompt
    
    def _query_llm(self, prompt: str) -> str:
        """Query the LLM with the selection prompt.
        
        Args:
            prompt: Complete AI prompt
            
        Returns:
            AI response text
        """
        try:
            response = self.ollama_manager.query(
                prompt=prompt,
                model=self.ollama_manager.model_name,
                temperature=0.3,  # Lower temperature for more deterministic selection
                max_tokens=1000
            )
            
            if response and response.get('success'):
                return response.get('response', '')
            else:
                raise Exception(f"LLM query failed: {response}")
                
        except Exception as e:
            self.logger.error(f"LLM query error: {e}")
            raise
    
    def _parse_ai_response(self, response: str, templates: List[TemplateMetadata]) -> TemplateChoice:
        """Parse AI response into TemplateChoice object.
        
        Args:
            response: Raw AI response
            templates: Available templates for validation
            
        Returns:
            Parsed template choice
        """
        try:
            # Clean response - sometimes LLM includes extra text
            response = response.strip()
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            elif response.startswith('```'):
                response = response.replace('```', '').strip()
            
            # Find JSON in response
            json_match = re.search(r'\\{.*\\}', response, re.DOTALL)
            if json_match:
                response = json_match.group()
            
            # Parse JSON
            ai_choice = json.loads(response)
            
            # Validate template exists
            selected_template = ai_choice.get('selected_template', '')
            template_names = [t.name for t in templates]
            
            if selected_template not in template_names:
                # Try to find closest match
                selected_template = self._find_closest_template(selected_template, template_names)
                self.logger.warning(f"AI selected non-existent template, using closest match: {selected_template}")
            
            # Parse confidence level
            confidence = float(ai_choice.get('confidence', 0.0))
            confidence_level = self._get_confidence_level(confidence)
            
            # Validate alternatives
            alternatives = ai_choice.get('alternatives', [])
            valid_alternatives = [alt for alt in alternatives if alt in template_names]
            
            return TemplateChoice(
                template_name=selected_template,
                confidence=confidence,
                reasoning=ai_choice.get('reasoning', 'No reasoning provided'),
                confidence_level=confidence_level,
                alternative_templates=valid_alternatives,
                matched_examples=ai_choice.get('matched_examples', []),
                key_factors=ai_choice.get('key_factors', [])
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.error(f"Failed to parse AI response: {e}\\nResponse: {response}")
            return self._create_fallback_choice(f"Response parsing error: {str(e)}")
    
    def _find_closest_template(self, target: str, template_names: List[str]) -> str:
        """Find the closest matching template name.
        
        Args:
            target: Target template name
            template_names: Available template names
            
        Returns:
            Closest matching template name
        """
        if not template_names:
            return "unknown"
        
        # Simple string similarity based on shared words
        target_words = set(target.lower().replace('_', ' ').split())
        
        best_match = template_names[0]
        best_score = 0
        
        for name in template_names:
            name_words = set(name.lower().replace('_', ' ').split())
            score = len(target_words & name_words) / len(target_words | name_words)
            
            if score > best_score:
                best_score = score
                best_match = name
        
        return best_match
    
    def _get_confidence_level(self, confidence: float) -> SelectionConfidence:
        """Convert numeric confidence to confidence level enum.
        
        Args:
            confidence: Numeric confidence (0.0-1.0)
            
        Returns:
            SelectionConfidence enum value
        """
        if confidence >= 0.9:
            return SelectionConfidence.VERY_HIGH
        elif confidence >= 0.8:
            return SelectionConfidence.HIGH
        elif confidence >= 0.6:
            return SelectionConfidence.MEDIUM
        elif confidence >= 0.4:
            return SelectionConfidence.LOW
        else:
            return SelectionConfidence.VERY_LOW
    
    def _create_fallback_choice(self, reason: str) -> TemplateChoice:
        """Create a fallback template choice when AI selection fails.
        
        Args:
            reason: Reason for fallback
            
        Returns:
            Fallback template choice
        """
        # Try to get the most used template as fallback
        templates = self.template_manager.get_all_templates_metadata()
        if templates:
            # Sort by usage count, then by success rate
            fallback_template = max(
                templates,
                key=lambda t: (t.usage_count, t.success_rate)
            )
            template_name = fallback_template.name
        else:
            template_name = "create_reservation"  # Default fallback
        
        return TemplateChoice(
            template_name=template_name,
            confidence=0.1,
            reasoning=f"Fallback selection due to: {reason}",
            confidence_level=SelectionConfidence.VERY_LOW,
            alternative_templates=[],
            matched_examples=[],
            key_factors=["fallback_selection"]
        )
    
    def _record_selection(self, user_input: str, choice: TemplateChoice, raw_response: str):
        """Record template selection for learning and analytics.
        
        Args:
            user_input: Original user input
            choice: AI template choice
            raw_response: Raw AI response
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "selected_template": choice.template_name,
            "confidence": choice.confidence,
            "reasoning": choice.reasoning,
            "alternatives": choice.alternative_templates,
            "raw_response": raw_response
        }
        
        self.selection_history.append(record)
        
        # Keep history size manageable
        if len(self.selection_history) > 1000:
            self.selection_history = self.selection_history[-500:]
    
    def get_selection_analytics(self) -> Dict[str, Any]:
        """Get analytics on template selection performance.
        
        Returns:
            Selection analytics dictionary
        """
        if not self.selection_history:
            return {"total_selections": 0}
        
        total_selections = len(self.selection_history)
        
        # Confidence distribution
        confidence_levels = [record["confidence"] for record in self.selection_history]
        avg_confidence = sum(confidence_levels) / len(confidence_levels)
        
        # Most selected templates
        template_counts = {}
        for record in self.selection_history:
            template = record["selected_template"]
            template_counts[template] = template_counts.get(template, 0) + 1
        
        most_selected = sorted(
            template_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "total_selections": total_selections,
            "average_confidence": avg_confidence,
            "most_selected_templates": most_selected,
            "confidence_distribution": {
                "very_high": len([c for c in confidence_levels if c >= 0.9]),
                "high": len([c for c in confidence_levels if 0.8 <= c < 0.9]),
                "medium": len([c for c in confidence_levels if 0.6 <= c < 0.8]),
                "low": len([c for c in confidence_levels if 0.4 <= c < 0.6]),
                "very_low": len([c for c in confidence_levels if c < 0.4])
            }
        }