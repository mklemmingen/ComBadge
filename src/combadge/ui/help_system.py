"""
In-app help system for ComBadge.

This module provides context-sensitive help, tutorials, and documentation
access directly within the ComBadge interface.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class HelpTopic:
    """Represents a help topic."""
    id: str
    title: str
    content: str
    category: str
    keywords: List[str]
    difficulty: str  # beginner, intermediate, advanced
    last_updated: datetime
    related_topics: List[str] = None
    examples: List[str] = None
    
    def __post_init__(self):
        if self.related_topics is None:
            self.related_topics = []
        if self.examples is None:
            self.examples = []


@dataclass
class HelpSearchResult:
    """Search result for help topics."""
    topic: HelpTopic
    relevance_score: float
    matching_keywords: List[str]


@dataclass
class TutorialStep:
    """Single step in a tutorial."""
    id: str
    title: str
    description: str
    action_type: str  # click, type, wait, info
    target_element: Optional[str] = None
    expected_value: Optional[str] = None
    validation_func: Optional[str] = None
    tips: List[str] = None
    
    def __post_init__(self):
        if self.tips is None:
            self.tips = []


@dataclass
class Tutorial:
    """Interactive tutorial."""
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    estimated_duration: int  # minutes
    prerequisites: List[str]
    steps: List[TutorialStep]
    completion_criteria: Dict[str, Any]
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []


@dataclass
class UserProgress:
    """Tracks user's help system progress."""
    user_id: str
    completed_tutorials: List[str]
    bookmarked_topics: List[str]
    search_history: List[str]
    last_accessed_topic: Optional[str] = None
    help_preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.help_preferences is None:
            self.help_preferences = {}


class ContextualHelp:
    """Provides context-aware help suggestions."""
    
    def __init__(self):
        self.context_rules: Dict[str, List[str]] = {}
        self.load_context_rules()
        
    def load_context_rules(self):
        """Load context-to-help mapping rules."""
        self.context_rules = {
            "vehicle_reservation": [
                "vehicle-reservation-basics",
                "time-date-formats",
                "confidence-scores"
            ],
            "maintenance_scheduling": [
                "maintenance-scheduling",
                "service-types",
                "maintenance-calendar"
            ],
            "low_confidence": [
                "improving-requests",
                "request-examples",
                "troubleshooting-confidence"
            ],
            "first_time_user": [
                "getting-started",
                "interface-overview",
                "first-request"
            ],
            "approval_workflow": [
                "approval-process",
                "edit-requests",
                "understanding-analysis"
            ],
            "email_processing": [
                "email-integration",
                "email-formats",
                "email-troubleshooting"
            ]
        }
        
    def get_contextual_suggestions(
        self,
        context: str,
        user_level: str = "beginner"
    ) -> List[str]:
        """Get help suggestions for current context."""
        suggestions = []
        
        # Get direct context matches
        if context in self.context_rules:
            suggestions.extend(self.context_rules[context])
            
        # Add level-appropriate general topics
        if user_level == "beginner":
            suggestions.extend([
                "interface-overview",
                "basic-requests",
                "understanding-confidence"
            ])
        elif user_level == "advanced":
            suggestions.extend([
                "advanced-features",
                "batch-operations",
                "template-creation"
            ])
            
        return list(dict.fromkeys(suggestions))  # Remove duplicates


class HelpContentLoader:
    """Loads and manages help content from various sources."""
    
    def __init__(self, content_directory: Path):
        self.content_directory = Path(content_directory)
        self.topics: Dict[str, HelpTopic] = {}
        self.tutorials: Dict[str, Tutorial] = {}
        
    async def load_all_content(self):
        """Load all help content from files."""
        await asyncio.gather(
            self.load_help_topics(),
            self.load_tutorials()
        )
        
    async def load_help_topics(self):
        """Load help topics from markdown files."""
        topics_dir = self.content_directory / "topics"
        if not topics_dir.exists():
            logger.warning(f"Topics directory not found: {topics_dir}")
            return
            
        for topic_file in topics_dir.glob("*.md"):
            try:
                topic = await self._load_topic_from_file(topic_file)
                self.topics[topic.id] = topic
            except Exception as e:
                logger.error(f"Failed to load topic {topic_file}: {e}")
                
    async def load_tutorials(self):
        """Load tutorials from JSON files."""
        tutorials_dir = self.content_directory / "tutorials"
        if not tutorials_dir.exists():
            logger.warning(f"Tutorials directory not found: {tutorials_dir}")
            return
            
        for tutorial_file in tutorials_dir.glob("*.json"):
            try:
                tutorial = await self._load_tutorial_from_file(tutorial_file)
                self.tutorials[tutorial.id] = tutorial
            except Exception as e:
                logger.error(f"Failed to load tutorial {tutorial_file}: {e}")
                
    async def _load_topic_from_file(self, file_path: Path) -> HelpTopic:
        """Load help topic from markdown file."""
        content = file_path.read_text(encoding='utf-8')
        
        # Parse frontmatter (YAML header)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                content_body = parts[2].strip()
                
                # Parse YAML frontmatter (simplified)
                metadata = self._parse_simple_yaml(frontmatter)
            else:
                metadata = {}
                content_body = content
        else:
            metadata = {}
            content_body = content
            
        # Create topic with metadata
        topic_id = metadata.get('id', file_path.stem)
        return HelpTopic(
            id=topic_id,
            title=metadata.get('title', topic_id.replace('-', ' ').title()),
            content=content_body,
            category=metadata.get('category', 'general'),
            keywords=metadata.get('keywords', []),
            difficulty=metadata.get('difficulty', 'beginner'),
            last_updated=datetime.now(),
            related_topics=metadata.get('related_topics', []),
            examples=metadata.get('examples', [])
        )
        
    async def _load_tutorial_from_file(self, file_path: Path) -> Tutorial:
        """Load tutorial from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Convert step data to TutorialStep objects
        steps = [
            TutorialStep(**step_data)
            for step_data in data.get('steps', [])
        ]
        
        return Tutorial(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            category=data.get('category', 'general'),
            difficulty=data.get('difficulty', 'beginner'),
            estimated_duration=data.get('estimated_duration', 10),
            prerequisites=data.get('prerequisites', []),
            steps=steps,
            completion_criteria=data.get('completion_criteria', {})
        )
        
    def _parse_simple_yaml(self, yaml_str: str) -> Dict[str, Any]:
        """Simple YAML parser for frontmatter."""
        result = {}
        for line in yaml_str.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Handle lists
                if value.startswith('[') and value.endswith(']'):
                    value = [item.strip().strip('"\'') 
                           for item in value[1:-1].split(',')
                           if item.strip()]
                # Handle quotes
                elif value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                    
                result[key] = value
                
        return result


class HelpSearchEngine:
    """Search engine for help content."""
    
    def __init__(self):
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'will', 'with', 'how', 'what',
            'when', 'where', 'why'
        }
        
    def search(
        self,
        query: str,
        topics: Dict[str, HelpTopic],
        max_results: int = 10
    ) -> List[HelpSearchResult]:
        """Search help topics by query."""
        if not query.strip():
            return []
            
        query_terms = self._tokenize_query(query.lower())
        results = []
        
        for topic in topics.values():
            score, matching_keywords = self._score_topic(topic, query_terms)
            if score > 0:
                results.append(HelpSearchResult(
                    topic=topic,
                    relevance_score=score,
                    matching_keywords=matching_keywords
                ))
                
        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:max_results]
        
    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenize search query."""
        # Simple tokenization
        import re
        tokens = re.findall(r'\w+', query.lower())
        return [token for token in tokens if token not in self.stop_words]
        
    def _score_topic(
        self,
        topic: HelpTopic,
        query_terms: List[str]
    ) -> tuple[float, List[str]]:
        """Score topic relevance to query."""
        score = 0.0
        matching_keywords = []
        
        # Search in title (highest weight)
        title_words = self._tokenize_query(topic.title.lower())
        for term in query_terms:
            for word in title_words:
                if term in word or word in term:
                    score += 3.0
                    matching_keywords.append(word)
                    
        # Search in keywords (high weight)
        for keyword in topic.keywords:
            keyword_lower = keyword.lower()
            for term in query_terms:
                if term in keyword_lower or keyword_lower in term:
                    score += 2.0
                    matching_keywords.append(keyword)
                    
        # Search in content (medium weight)
        content_words = self._tokenize_query(topic.content.lower())
        for term in query_terms:
            count = content_words.count(term)
            if count > 0:
                score += count * 0.5
                matching_keywords.append(term)
                
        # Boost score for exact matches
        title_lower = topic.title.lower()
        content_lower = topic.content.lower()
        for term in query_terms:
            if term in title_lower:
                score += 1.0
            if term in content_lower:
                score += 0.3
                
        return score, list(set(matching_keywords))


class TutorialRunner:
    """Manages tutorial execution and progress."""
    
    def __init__(self, ui_interface):
        self.ui_interface = ui_interface
        self.current_tutorial: Optional[Tutorial] = None
        self.current_step_index: int = 0
        self.is_running: bool = False
        self.step_completion_callbacks: Dict[str, Callable] = {}
        
    def start_tutorial(self, tutorial: Tutorial) -> bool:
        """Start a tutorial."""
        if self.is_running:
            logger.warning("Tutorial already running")
            return False
            
        self.current_tutorial = tutorial
        self.current_step_index = 0
        self.is_running = True
        
        logger.info(f"Starting tutorial: {tutorial.title}")
        return True
        
    def stop_tutorial(self):
        """Stop current tutorial."""
        self.is_running = False
        self.current_tutorial = None
        self.current_step_index = 0
        
    def get_current_step(self) -> Optional[TutorialStep]:
        """Get current tutorial step."""
        if not self.is_running or not self.current_tutorial:
            return None
            
        if self.current_step_index < len(self.current_tutorial.steps):
            return self.current_tutorial.steps[self.current_step_index]
        return None
        
    def next_step(self) -> bool:
        """Move to next tutorial step."""
        if not self.is_running or not self.current_tutorial:
            return False
            
        self.current_step_index += 1
        
        # Check if tutorial is complete
        if self.current_step_index >= len(self.current_tutorial.steps):
            self.complete_tutorial()
            return False
            
        return True
        
    def previous_step(self) -> bool:
        """Move to previous tutorial step."""
        if not self.is_running or self.current_step_index <= 0:
            return False
            
        self.current_step_index -= 1
        return True
        
    def complete_tutorial(self):
        """Mark tutorial as completed."""
        if self.current_tutorial:
            logger.info(f"Tutorial completed: {self.current_tutorial.title}")
            # Here you could save completion to user progress
            
        self.stop_tutorial()
        
    def validate_step_completion(self, step: TutorialStep) -> bool:
        """Validate if tutorial step is completed correctly."""
        if step.validation_func and step.validation_func in self.step_completion_callbacks:
            return self.step_completion_callbacks[step.validation_func](step)
        return True
        
    def register_validation_callback(self, name: str, callback: Callable):
        """Register step validation callback."""
        self.step_completion_callbacks[name] = callback


class HelpSystem:
    """Main help system orchestrator."""
    
    def __init__(self, content_directory: Path, ui_interface=None):
        self.content_loader = HelpContentLoader(content_directory)
        self.search_engine = HelpSearchEngine()
        self.contextual_help = ContextualHelp()
        self.tutorial_runner = TutorialRunner(ui_interface)
        
        self.user_progress: Dict[str, UserProgress] = {}
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize help system."""
        if self.is_initialized:
            return
            
        logger.info("Initializing help system...")
        await self.content_loader.load_all_content()
        
        self.is_initialized = True
        logger.info(f"Help system initialized with {len(self.content_loader.topics)} topics "
                   f"and {len(self.content_loader.tutorials)} tutorials")
                   
    def get_topic(self, topic_id: str) -> Optional[HelpTopic]:
        """Get help topic by ID."""
        return self.content_loader.topics.get(topic_id)
        
    def get_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        """Get tutorial by ID."""
        return self.content_loader.tutorials.get(tutorial_id)
        
    def search_topics(
        self,
        query: str,
        max_results: int = 10
    ) -> List[HelpSearchResult]:
        """Search help topics."""
        return self.search_engine.search(
            query,
            self.content_loader.topics,
            max_results
        )
        
    def get_contextual_help(
        self,
        context: str,
        user_id: str = "default"
    ) -> List[HelpTopic]:
        """Get contextual help suggestions."""
        user_progress = self.get_user_progress(user_id)
        user_level = self._determine_user_level(user_progress)
        
        suggestions = self.contextual_help.get_contextual_suggestions(
            context, user_level
        )
        
        topics = []
        for topic_id in suggestions:
            topic = self.get_topic(topic_id)
            if topic:
                topics.append(topic)
                
        return topics
        
    def get_user_progress(self, user_id: str) -> UserProgress:
        """Get or create user progress."""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = UserProgress(
                user_id=user_id,
                completed_tutorials=[],
                bookmarked_topics=[],
                search_history=[]
            )
        return self.user_progress[user_id]
        
    def update_user_progress(
        self,
        user_id: str,
        **updates
    ):
        """Update user progress."""
        progress = self.get_user_progress(user_id)
        for key, value in updates.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
                
    def _determine_user_level(self, progress: UserProgress) -> str:
        """Determine user skill level from progress."""
        completed_count = len(progress.completed_tutorials)
        
        if completed_count == 0:
            return "beginner"
        elif completed_count < 5:
            return "intermediate"
        else:
            return "advanced"
            
    def bookmark_topic(self, user_id: str, topic_id: str):
        """Bookmark a help topic for user."""
        progress = self.get_user_progress(user_id)
        if topic_id not in progress.bookmarked_topics:
            progress.bookmarked_topics.append(topic_id)
            
    def unbookmark_topic(self, user_id: str, topic_id: str):
        """Remove bookmark from help topic."""
        progress = self.get_user_progress(user_id)
        if topic_id in progress.bookmarked_topics:
            progress.bookmarked_topics.remove(topic_id)
            
    def get_bookmarked_topics(self, user_id: str) -> List[HelpTopic]:
        """Get user's bookmarked topics."""
        progress = self.get_user_progress(user_id)
        topics = []
        
        for topic_id in progress.bookmarked_topics:
            topic = self.get_topic(topic_id)
            if topic:
                topics.append(topic)
                
        return topics
        
    def record_search(self, user_id: str, query: str):
        """Record user search for analytics."""
        progress = self.get_user_progress(user_id)
        progress.search_history.append(query)
        
        # Keep only recent searches
        if len(progress.search_history) > 50:
            progress.search_history = progress.search_history[-50:]
            
    def get_popular_topics(self, limit: int = 10) -> List[HelpTopic]:
        """Get most popular help topics."""
        # Simplified - in real implementation, track topic access
        popular_topic_ids = [
            "getting-started",
            "vehicle-reservation-basics",
            "confidence-scores",
            "approval-process",
            "request-examples"
        ]
        
        topics = []
        for topic_id in popular_topic_ids[:limit]:
            topic = self.get_topic(topic_id)
            if topic:
                topics.append(topic)
                
        return topics
        
    def get_recommended_tutorials(self, user_id: str) -> List[Tutorial]:
        """Get recommended tutorials for user."""
        progress = self.get_user_progress(user_id)
        user_level = self._determine_user_level(progress)
        
        recommended = []
        for tutorial in self.content_loader.tutorials.values():
            # Skip completed tutorials
            if tutorial.id in progress.completed_tutorials:
                continue
                
            # Match difficulty level
            if tutorial.difficulty == user_level:
                recommended.append(tutorial)
                
        # Sort by estimated duration (shorter first for beginners)
        recommended.sort(key=lambda t: t.estimated_duration)
        return recommended[:5]  # Return top 5 recommendations
        
    def export_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Export user progress as JSON."""
        progress = self.get_user_progress(user_id)
        return asdict(progress)
        
    def import_user_progress(self, user_id: str, progress_data: Dict[str, Any]):
        """Import user progress from JSON."""
        progress = UserProgress(**progress_data)
        self.user_progress[user_id] = progress